// gpu/cis2_model.h — CIS-2 v0.3b forward pass as index-space kernels,
// single-source CUDA-portable C++17.
//
// Mirrors src/main.rs statement for statement. See gpu/README.md §3 for the
// op -> Rust-function -> reduction-order table and §4 for the twenty-five
// places where the Rust's evaluation order is not obvious.
//
// KERNEL MODEL
//   Every kernel is one lambda over an index space, dispatched through
//   `cis2_for_each(n, f)`:
//     * host build : a plain `for (int i = 0; i < n; ++i) f(i);`
//     * nvcc build : a grid launch of `n` threads, one per index.
//   The kernel bodies are the SAME source text in both builds; only the
//   dispatcher differs. Index spaces are chosen so that each thread owns
//   exactly one output element and performs that element's reduction
//   serially, in the order §5.1/§5.3 pin — which is what makes the two
//   builds bit-identical rather than merely close.
//
//   Reductions that the spec pins as a single strict left-to-right fold
//   over the WHOLE vector (RMSNorm's sum of squares, softmax's max scan and
//   denominator) are therefore one-thread kernels by construction. That is
//   the intended cost of v0.3b's strict order, not an oversight.

#ifndef CIS2_MODEL_H
#define CIS2_MODEL_H

#include "cis2_math.h"
#include "cis2_sha256.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <string>
#include <vector>

// =====================================================================
// 1. Index-space dispatch and device memory
// =====================================================================

#if defined(__CUDACC__)

template <class F>
__global__ void cis2_index_kernel(int n, F f) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) f(i);
}

// NOTE: never compiled on this box (no nvcc, no GPU). Requires
// `--extended-lambda`; see gpu/Makefile's `cuda` target.
template <class F>
inline void cis2_for_each(int n, F f) {
  if (n <= 0) return;
  const int threads = 256;
  const int blocks = (n + threads - 1) / threads;
  cis2_index_kernel<<<blocks, threads>>>(n, f);
  cudaError_t e = cudaDeviceSynchronize();
  if (e != cudaSuccess) {
    fprintf(stderr, "FATAL: kernel launch failed: %s\n", cudaGetErrorString(e));
    exit(2);
  }
}

inline float *cis2_dev_alloc(size_t n) {
  float *p = nullptr;
  if (cudaMalloc(&p, n * sizeof(float)) != cudaSuccess) {
    fprintf(stderr, "FATAL: cudaMalloc(%zu floats) failed\n", n);
    exit(2);
  }
  return p;
}
inline void cis2_dev_free(float *p) { cudaFree(p); }
inline void cis2_upload(float *d, const float *h, size_t n) {
  cudaMemcpy(d, h, n * sizeof(float), cudaMemcpyHostToDevice);
}
inline void cis2_download(float *h, const float *d, size_t n) {
  cudaMemcpy(h, d, n * sizeof(float), cudaMemcpyDeviceToHost);
}
#define CIS2_DEVICE_IS_HOST 0

#else  // ---------------- host build ----------------

template <class F>
inline void cis2_for_each(int n, F f) {
  for (int i = 0; i < n; ++i) f(i);
}

inline float *cis2_dev_alloc(size_t n) {
  float *p = (float *)malloc(n * sizeof(float));
  if (!p) {
    fprintf(stderr, "FATAL: malloc(%zu floats) failed\n", n);
    exit(2);
  }
  return p;
}
inline void cis2_dev_free(float *p) { free(p); }
// On the host build the "device" pointer IS the host pointer, so an upload
// or download of a buffer onto itself is a no-op and the weights are never
// duplicated in memory.
inline void cis2_upload(float *d, const float *h, size_t n) {
  if (d != h) memcpy(d, h, n * sizeof(float));
}
inline void cis2_download(float *h, const float *d, size_t n) {
  if (h != d) memcpy(h, d, n * sizeof(float));
}
#define CIS2_DEVICE_IS_HOST 1

#endif

// =====================================================================
// 2. Minimal JSON reader (config.json and the safetensors header)
// =====================================================================
// Enough of RFC 8259 for the two documents this program reads. Numbers go
// through strtod, i.e. correctly-rounded decimal -> double, which is what
// serde_json gives the Rust reference; the single narrowing to f32 then
// happens at exactly one place, as in src/main.rs.

struct Cis2Json {
  enum Kind { NUL, BOOL, NUM, STR, ARR, OBJ } kind = NUL;
  bool b = false;
  double num = 0.0;
  std::string str;
  std::vector<Cis2Json> arr;
  std::vector<std::pair<std::string, Cis2Json>> obj;

  const Cis2Json *get(const char *key) const {
    if (kind != OBJ) return nullptr;
    for (size_t i = 0; i < obj.size(); ++i)
      if (obj[i].first == key) return &obj[i].second;
    return nullptr;
  }
};

struct Cis2JsonParser {
  const char *p;
  const char *end;

  void ws() {
    while (p < end && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) ++p;
  }
  [[noreturn]] void die(const char *what) {
    fprintf(stderr, "FATAL: JSON parse error: %s\n", what);
    exit(2);
  }
  std::string parse_string() {
    if (p >= end || *p != '"') die("expected string");
    ++p;
    std::string s;
    while (p < end && *p != '"') {
      if (*p == '\\') {
        ++p;
        if (p >= end) die("truncated escape");
        char c = *p++;
        switch (c) {
          case 'n': s.push_back('\n'); break;
          case 't': s.push_back('\t'); break;
          case 'r': s.push_back('\r'); break;
          case 'b': s.push_back('\b'); break;
          case 'f': s.push_back('\f'); break;
          case '/': s.push_back('/'); break;
          case '"': s.push_back('"'); break;
          case '\\': s.push_back('\\'); break;
          case 'u': {
            if (end - p < 4) die("truncated \\u");
            unsigned v = 0;
            for (int i = 0; i < 4; ++i) {
              char h = p[i];
              v <<= 4;
              if (h >= '0' && h <= '9') v |= (unsigned)(h - '0');
              else if (h >= 'a' && h <= 'f') v |= (unsigned)(h - 'a' + 10);
              else if (h >= 'A' && h <= 'F') v |= (unsigned)(h - 'A' + 10);
              else die("bad \\u digit");
            }
            p += 4;
            // The two documents parsed here are ASCII; keep it simple and
            // faithful for the BMP-below-0x80 case, replace the rest.
            s.push_back(v < 0x80 ? (char)v : '?');
            break;
          }
          default: die("bad escape");
        }
      } else {
        s.push_back(*p++);
      }
    }
    if (p >= end) die("unterminated string");
    ++p;
    return s;
  }
  Cis2Json parse() {
    ws();
    if (p >= end) die("unexpected end");
    Cis2Json v;
    if (*p == '{') {
      v.kind = Cis2Json::OBJ;
      ++p; ws();
      if (p < end && *p == '}') { ++p; return v; }
      for (;;) {
        ws();
        std::string k = parse_string();
        ws();
        if (p >= end || *p != ':') die("expected ':'");
        ++p;
        v.obj.push_back(std::make_pair(k, parse()));
        ws();
        if (p < end && *p == ',') { ++p; continue; }
        if (p < end && *p == '}') { ++p; return v; }
        die("expected ',' or '}'");
      }
    }
    if (*p == '[') {
      v.kind = Cis2Json::ARR;
      ++p; ws();
      if (p < end && *p == ']') { ++p; return v; }
      for (;;) {
        v.arr.push_back(parse());
        ws();
        if (p < end && *p == ',') { ++p; continue; }
        if (p < end && *p == ']') { ++p; return v; }
        die("expected ',' or ']'");
      }
    }
    if (*p == '"') { v.kind = Cis2Json::STR; v.str = parse_string(); return v; }
    if (end - p >= 4 && memcmp(p, "true", 4) == 0) {
      v.kind = Cis2Json::BOOL; v.b = true; p += 4; return v;
    }
    if (end - p >= 5 && memcmp(p, "false", 5) == 0) {
      v.kind = Cis2Json::BOOL; v.b = false; p += 5; return v;
    }
    if (end - p >= 4 && memcmp(p, "null", 4) == 0) { p += 4; return v; }
    {
      char *stop = nullptr;
      // strtod stops at the first character that cannot extend the number;
      // the buffer is NUL-terminated by the caller.
      double d = strtod(p, &stop);
      if (stop == p) die("expected value");
      v.kind = Cis2Json::NUM;
      v.num = d;
      p = stop;
      return v;
    }
  }
};

inline Cis2Json cis2_json_parse(const std::string &text) {
  Cis2JsonParser ps;
  ps.p = text.c_str();
  ps.end = text.c_str() + text.size();
  return ps.parse();
}

inline std::string cis2_read_file(const std::string &path) {
  FILE *f = fopen(path.c_str(), "rb");
  if (!f) { fprintf(stderr, "FATAL: cannot open %s\n", path.c_str()); exit(2); }
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  std::string s;
  s.resize((size_t)n);
  if (n && fread(&s[0], 1, (size_t)n, f) != (size_t)n) {
    fprintf(stderr, "FATAL: short read on %s\n", path.c_str());
    exit(2);
  }
  fclose(f);
  return s;
}

inline void cis2_sha256_file(const std::string &path, unsigned char out[32]) {
  FILE *f = fopen(path.c_str(), "rb");
  if (!f) { fprintf(stderr, "FATAL: cannot open %s\n", path.c_str()); exit(2); }
  Cis2Sha256 h;
  static unsigned char buf[1 << 20];
  size_t n;
  while ((n = fread(buf, 1, sizeof(buf), f)) > 0) h.update(buf, n);
  fclose(f);
  h.finalize(out);
}

// =====================================================================
// 3. safetensors reader (bf16 -> f32 exactly as src/math.rs::widen_bf16)
// =====================================================================

struct Cis2TensorView {
  std::string dtype;
  std::vector<size_t> shape;
  size_t begin = 0, end = 0;  // byte offsets into the data section
};

struct Cis2SafeTensors {
  std::string blob;  // whole file
  const unsigned char *data = nullptr;  // start of the data section
  size_t data_len = 0;
  std::vector<std::pair<std::string, Cis2TensorView>> tensors;

  void open(const std::string &path) {
    blob = cis2_read_file(path);
    if (blob.size() < 8) { fprintf(stderr, "FATAL: safetensors too short\n"); exit(2); }
    uint64_t hlen = 0;
    for (int i = 0; i < 8; ++i)
      hlen |= (uint64_t)(unsigned char)blob[i] << (8 * i);
    if (8 + hlen > blob.size()) {
      fprintf(stderr, "FATAL: safetensors header length out of range\n");
      exit(2);
    }
    std::string header(blob.data() + 8, (size_t)hlen);
    Cis2Json j = cis2_json_parse(header);
    if (j.kind != Cis2Json::OBJ) { fprintf(stderr, "FATAL: safetensors header not an object\n"); exit(2); }
    for (size_t i = 0; i < j.obj.size(); ++i) {
      if (j.obj[i].first == "__metadata__") continue;
      const Cis2Json &t = j.obj[i].second;
      Cis2TensorView v;
      const Cis2Json *dt = t.get("dtype");
      const Cis2Json *sh = t.get("shape");
      const Cis2Json *of = t.get("data_offsets");
      if (!dt || !sh || !of) continue;
      v.dtype = dt->str;
      for (size_t k = 0; k < sh->arr.size(); ++k)
        v.shape.push_back((size_t)sh->arr[k].num);
      v.begin = (size_t)of->arr[0].num;
      v.end = (size_t)of->arr[1].num;
      tensors.push_back(std::make_pair(j.obj[i].first, v));
    }
    data = (const unsigned char *)blob.data() + 8 + hlen;
    data_len = blob.size() - 8 - (size_t)hlen;
  }

  const Cis2TensorView *find(const std::string &name) const {
    for (size_t i = 0; i < tensors.size(); ++i)
      if (tensors[i].first == name) return &tensors[i].second;
    return nullptr;
  }

  bool has(const std::string &name) const { return find(name) != nullptr; }

  // Widen a BF16 tensor into a device buffer. §4.1: the widening is the
  // exact bit shift, performed as pure bit manipulation (no arithmetic, so
  // FTZ/DAZ does not enter into it) — identical to
  // src/main.rs::load_f32_tensor.
  float *load_bf16(const std::string &name, const std::vector<size_t> &expect) const {
    const Cis2TensorView *v = find(name);
    if (!v) { fprintf(stderr, "FATAL: tensor %s missing\n", name.c_str()); exit(2); }
    if (v->dtype != "BF16") {
      fprintf(stderr, "FATAL: tensor %s dtype %s, expected BF16\n", name.c_str(), v->dtype.c_str());
      exit(2);
    }
    if (v->shape != expect) {
      fprintf(stderr, "FATAL: tensor %s shape mismatch\n", name.c_str());
      exit(2);
    }
    size_t nbytes = v->end - v->begin;
    if (nbytes % 2 || v->end > data_len) {
      fprintf(stderr, "FATAL: tensor %s byte range invalid\n", name.c_str());
      exit(2);
    }
    size_t n = nbytes / 2;
    size_t want = 1;
    for (size_t i = 0; i < expect.size(); ++i) want *= expect[i];
    if (n != want) { fprintf(stderr, "FATAL: tensor %s element count mismatch\n", name.c_str()); exit(2); }
    const unsigned char *raw = data + v->begin;
    float *dev = cis2_dev_alloc(n);
#if CIS2_DEVICE_IS_HOST
    float *host = dev;   // widen straight into the buffer; no second copy
#else
    std::vector<float> stage(n);
    float *host = stage.data();
#endif
    for (size_t i = 0; i < n; ++i) {
      uint16_t bits = (uint16_t)raw[2 * i] | ((uint16_t)raw[2 * i + 1] << 8);
      host[i] = cis2_widen_bf16(bits);
    }
    cis2_upload(dev, host, n);
    return dev;
  }
};

// =====================================================================
// 4. Model
// =====================================================================

struct Cis2Layer {
  const float *input_layernorm;
  const float *post_attention_layernorm;
  const float *q_proj;
  const float *k_proj;
  const float *v_proj;
  const float *o_proj;
  const float *gate_proj;
  const float *up_proj;
  const float *down_proj;
  const float *q_bias;  // nullptr when the checkpoint has no bias tensors
  const float *k_bias;
  const float *v_bias;
};

struct Cis2Model {
  const float *embed_tokens = nullptr;
  const float *lm_head = nullptr;  // nullptr => tied to embed_tokens
  const float *final_norm = nullptr;
  const float *inv_freq = nullptr;
  std::vector<Cis2Layer> layers;
  int hidden = 0, inter = 0, n_layers = 0, n_heads = 0, n_kv_heads = 0;
  int head_dim = 0, vocab = 0;
  float eps = 0.0f;
  std::vector<float> inv_freq_host;
  unsigned char inv_freq_table_digest[32];

  int kv_dim() const { return n_kv_heads * head_dim; }
  const float *lm_head_weights() const { return lm_head ? lm_head : embed_tokens; }
};

// §6.6 table digest — the same coefficients in the same declared order as
// src/math.rs::table_digest(), fed as raw little-endian bytes.
inline void cis2_table_digest(unsigned char out[32]) {
  // Explicit qualification, NOT `using namespace cis2_hostconst;`: under
  // __CUDACC__, cis2_hostconst holds its OWN distinct `static const`
  // copies of these names (cis2_math.h re-includes cis2_consts.inc inside
  // the namespace, since the global copies are __device__ __constant__ and
  // not host-addressable). A `using namespace` here would therefore bring
  // a second, distinct LOG_P0 (etc.) into scope alongside the global one
  // already visible from cis2_math.h's top-level include, making every
  // unqualified reference ambiguous (~28 "ambiguous" errors under real
  // nvcc device compilation). Host-only builds don't hit this because
  // cis2_hostconst::LOG_P0 there is a `using ::LOG_P0` alias for the same
  // entity as ::LOG_P0, not a second copy.
  namespace hc = cis2_hostconst;
  Cis2Sha256 h;
  const float f32s_a[3] = {hc::EXP_LOG2E, hc::EXP_C1, hc::EXP_C2};
  for (int i = 0; i < 3; ++i) h.update_u32le(cis2_f32_bits(f32s_a[i]));
  const float expp[6] = {hc::EXP_P0, hc::EXP_P1, hc::EXP_P2,
                          hc::EXP_P3, hc::EXP_P4, hc::EXP_P5};
  for (int i = 0; i < 6; ++i) h.update_u32le(cis2_f32_bits(expp[i]));
  {
    uint64_t b = cis2_f64_bits(hc::PI_2_F64);
    unsigned char le[8];
    for (int i = 0; i < 8; ++i) le[i] = (unsigned char)((b >> (8 * i)) & 0xFF);
    h.update(le, 8);
  }
  const float sinc[3] = {hc::SIN_C0, hc::SIN_C1, hc::SIN_C2};
  for (int i = 0; i < 3; ++i) h.update_u32le(cis2_f32_bits(sinc[i]));
  const float cosc[3] = {hc::COS_C0, hc::COS_C1, hc::COS_C2};
  for (int i = 0; i < 3; ++i) h.update_u32le(cis2_f32_bits(cosc[i]));
  h.update_u32le(cis2_f32_bits(hc::LOG_SQRTHF));
  h.update_u32le(cis2_f32_bits(hc::LOG_Q1));
  h.update_u32le(cis2_f32_bits(hc::LOG_Q2));
  const float logp[9] = {hc::LOG_P0, hc::LOG_P1, hc::LOG_P2, hc::LOG_P3, hc::LOG_P4,
                         hc::LOG_P5, hc::LOG_P6, hc::LOG_P7, hc::LOG_P8};
  for (int i = 0; i < 9; ++i) h.update_u32le(cis2_f32_bits(logp[i]));
  h.finalize(out);
}

// §7.2 pinned RoPE inv_freq table, built with the route-(b) polynomials
// only (src/main.rs, "§3.3(b)-pinned RoPE inv_freq"): no host powf, no std
// exp/ln. `frac` is an integer product, two exact int->f32 conversions and
// one correctly-rounded f32 divide.
inline void cis2_build_inv_freq(Cis2Model &m, double rope_theta) {
  float ln_theta = cis2_ln_pinned((float)rope_theta);
  int half = m.head_dim / 2;
  m.inv_freq_host.assign((size_t)half, 0.0f);
  for (int i = 0; i < half; ++i) {
    float frac = (float)(2 * i) / (float)m.head_dim;
    float a = frac * ln_theta;
    float neg_arg = -a;
    m.inv_freq_host[(size_t)i] = cis2_exp_pinned(neg_arg);
  }
  // The digest hashes the f32 VALUE bytes (`v.to_le_bytes()` in the Rust),
  // which for f32 are the bit-pattern bytes — see gpu/README.md §4.22.
  Cis2Sha256 h;
  for (int i = 0; i < half; ++i)
    h.update_u32le(cis2_f32_bits(m.inv_freq_host[(size_t)i]));
  h.finalize(m.inv_freq_table_digest);

  float *dev = cis2_dev_alloc((size_t)half);
  cis2_upload(dev, m.inv_freq_host.data(), (size_t)half);
  m.inv_freq = dev;
}

// =====================================================================
// 5. Trace hook (--trace); see gpu/README.md §5
// =====================================================================

struct Cis2Trace {
  FILE *fp = nullptr;
  std::vector<float> stage;

  bool on() const { return fp != nullptr; }
  void emit(int pos, int layer, const char *op, const float *dev, size_t n) {
    if (!fp) return;
    if (stage.size() < n) stage.resize(n);
    cis2_download(stage.data(), dev, n);
    unsigned char d[32];
    cis2_sha256_f32_bits(stage.data(), n, d);
    fprintf(fp, "pos=%d layer=%d op=%s sha256=%s\n", pos, layer, op,
            cis2_hex(d, 32).c_str());
  }
};

// =====================================================================
// 6. Kernels — one lambda per index space
// =====================================================================

// Embedding gather: 1 thread per hidden index.
inline void cis2_k_embed(const float *table, int token_id, int hidden, float *out) {
  const float *row = table + (size_t)token_id * (size_t)hidden;
  cis2_for_each(hidden, [=] CIS2_FN(int i) { out[i] = row[i]; });
}

// RMSNorm (src/main.rs::rmsnorm). Three kernels, because the middle one is
// the spec's strict left-to-right fold over the whole vector and is
// therefore a single thread.
inline void cis2_rmsnorm(const float *x, const float *w, float eps, int n,
                         float *sq, float *red, float *out) {
  cis2_for_each(n, [=] CIS2_FN(int i) { sq[i] = x[i] * x[i]; });
  cis2_for_each(1, [=] CIS2_FN(int) {
    float ss = CIS2_SUM(sq, n);
    float mean = ss / (float)n;
    red[0] = cis2_rsqrt_cr(mean + eps);
  });
  cis2_for_each(n, [=] CIS2_FN(int i) {
    float scaled = x[i] * red[0];
    out[i] = scaled * w[i];  // (x*inv)*w, in this order — README §4.1
  });
}

// matvec (src/main.rs::matvec): 1 thread per output feature, each running
// the strict left-to-right dot product over in_features.
inline void cis2_k_matvec(const float *w, const float *x, int out_f, int in_f,
                          float *y) {
  cis2_for_each(out_f, [=] CIS2_FN(int o) {
    y[o] = CIS2_DOT(w + (size_t)o * (size_t)in_f, x, in_f);
  });
}

// Optional per-output-feature bias (absent for SmolLM2-135M).
inline void cis2_k_add_bias(float *x, const float *bias, int n) {
  if (!bias) return;
  cis2_for_each(n, [=] CIS2_FN(int i) { x[i] = x[i] + bias[i]; });
}

inline void cis2_k_add(const float *a, const float *b, int n, float *out) {
  cis2_for_each(n, [=] CIS2_FN(int i) { out[i] = a[i] + b[i]; });
}

// RoPE rotate-half (src/main.rs::apply_rope_head): 1 thread per (head, i),
// each computing its own cos/sin. In-place is safe because a thread owns
// both i and i+half and reads both before writing either.
inline void cis2_k_rope(float *x, int n_heads_local, int head_dim, int pos,
                        const float *inv_freq) {
  const int half = head_dim / 2;
  cis2_for_each(n_heads_local * half, [=] CIS2_FN(int idx) {
    int hh = idx / half;
    int i = idx - hh * half;
    float *head = x + (size_t)hh * (size_t)head_dim;
    float angle = (float)pos * inv_freq[i];
    float cos_v = cis2_cos_pinned(angle);
    float sin_v = cis2_sin_pinned(angle);
    float x1 = head[i];
    float x2 = head[i + half];
    float t1 = x1 * cos_v;
    float t2 = (-x2) * sin_v;  // negate first — README §4.5
    float o1 = t1 + t2;
    float t3 = x2 * cos_v;
    float t4 = x1 * sin_v;
    float o2 = t3 + t4;
    head[i] = o1;
    head[i + half] = o2;
  });
}

// Attention scores: 1 thread per (query head, key position).
inline void cis2_k_scores(const float *q, const float *kcache, int n_heads,
                          int group, int head_dim, int kv_dim, int pos,
                          float scale, float *scores) {
  const int len = pos + 1;
  cis2_for_each(n_heads * len, [=] CIS2_FN(int idx) {
    int qh = idx / len;
    int j = idx - qh * len;
    int kv_head = qh / group;
    const float *q_head = q + (size_t)qh * (size_t)head_dim;
    const float *kj = kcache + (size_t)j * (size_t)kv_dim +
                      (size_t)kv_head * (size_t)head_dim;
    float d = CIS2_DOT(q_head, kj, head_dim);
    scores[(size_t)qh * (size_t)len + (size_t)j] = d * scale;  // scale AFTER
  });
}

// Softmax: 1 thread per query head, running the whole sequential softmax
// (max scan, pinned exp, sequential-sum denominator, divide) over its own
// pos+1 scores — the order §10 pins.
inline void cis2_k_softmax(float *scores, int n_heads, int pos) {
  const int len = pos + 1;
  cis2_for_each(n_heads, [=] CIS2_FN(int qh) {
    CIS2_SOFTMAX(scores + (size_t)qh * (size_t)len, len);
  });
}

// Attention weighted sum: 1 thread per (query head, head dim), serial over
// key positions in position order.
inline void cis2_k_attn_weighted_sum(const float *scores, const float *vcache,
                                     int n_heads, int group, int head_dim,
                                     int kv_dim, int pos, float *attn_out) {
  const int len = pos + 1;
  cis2_for_each(n_heads * head_dim, [=] CIS2_FN(int idx) {
    int qh = idx / head_dim;
    int d = idx - qh * head_dim;
    int kv_head = qh / group;
    const float *sc = scores + (size_t)qh * (size_t)len;
    float acc = 0.0f;
    for (int j = 0; j < len; ++j) {
      float vj = vcache[(size_t)j * (size_t)kv_dim +
                        (size_t)kv_head * (size_t)head_dim + (size_t)d];
      float p = sc[j] * vj;
      acc = acc + p;
    }
    attn_out[(size_t)qh * (size_t)head_dim + (size_t)d] = acc;
  });
}

inline void cis2_k_silu_mul(const float *gate, const float *up, int n, float *out) {
  cis2_for_each(n, [=] CIS2_FN(int i) {
    out[i] = cis2_silu_pinned(gate[i]) * up[i];
  });
}

// Copy one vector into a KV-cache slot (1 thread per element).
inline void cis2_k_store_kv(const float *src, float *cache, int kv_dim, int pos) {
  float *dst = cache + (size_t)pos * (size_t)kv_dim;
  cis2_for_each(kv_dim, [=] CIS2_FN(int i) { dst[i] = src[i]; });
}

// =====================================================================
// 7. Workspace + forward pass
// =====================================================================

struct Cis2Workspace {
  float *h = nullptr, *h2 = nullptr, *ln = nullptr;
  float *sq = nullptr, *red = nullptr;
  float *q = nullptr, *k = nullptr, *v = nullptr;
  float *attn_out = nullptr, *o = nullptr;
  float *gate = nullptr, *up = nullptr, *hid = nullptr, *down = nullptr;
  float *hn = nullptr, *logits = nullptr, *scores = nullptr;
  std::vector<float *> kcache, vcache;
  int max_pos = 0;

  void alloc(const Cis2Model &m, int max_positions) {
    max_pos = max_positions;
    int hidden = m.hidden, inter = m.inter, kvd = m.kv_dim();
    h = cis2_dev_alloc((size_t)hidden);
    h2 = cis2_dev_alloc((size_t)hidden);
    ln = cis2_dev_alloc((size_t)hidden);
    sq = cis2_dev_alloc((size_t)hidden);
    red = cis2_dev_alloc(1);
    q = cis2_dev_alloc((size_t)hidden);
    k = cis2_dev_alloc((size_t)kvd);
    v = cis2_dev_alloc((size_t)kvd);
    attn_out = cis2_dev_alloc((size_t)hidden);
    o = cis2_dev_alloc((size_t)hidden);
    gate = cis2_dev_alloc((size_t)inter);
    up = cis2_dev_alloc((size_t)inter);
    hid = cis2_dev_alloc((size_t)inter);
    down = cis2_dev_alloc((size_t)hidden);
    hn = cis2_dev_alloc((size_t)hidden);
    logits = cis2_dev_alloc((size_t)m.vocab);
    scores = cis2_dev_alloc((size_t)m.n_heads * (size_t)max_positions);
    kcache.resize((size_t)m.n_layers);
    vcache.resize((size_t)m.n_layers);
    for (int l = 0; l < m.n_layers; ++l) {
      kcache[(size_t)l] = cis2_dev_alloc((size_t)max_positions * (size_t)kvd);
      vcache[(size_t)l] = cis2_dev_alloc((size_t)max_positions * (size_t)kvd);
    }
  }
  void free_all() {
    float *ps[] = {h, h2, ln, sq, red, q, k, v, attn_out, o,
                   gate, up, hid, down, hn, logits, scores};
    for (size_t i = 0; i < sizeof(ps) / sizeof(ps[0]); ++i) cis2_dev_free(ps[i]);
    for (size_t l = 0; l < kcache.size(); ++l) {
      cis2_dev_free(kcache[l]);
      cis2_dev_free(vcache[l]);
    }
  }
};

// One decode step, mirroring src/main.rs::forward_token. Leaves the logits
// for `pos` in `ws.logits` (device memory).
inline void cis2_forward_token(const Cis2Model &m, Cis2Workspace &ws, int pos,
                               uint32_t token_id, Cis2Trace *trace) {
  const int hidden = m.hidden;
  const int head_dim = m.head_dim;
  const int n_heads = m.n_heads;
  const int group = m.n_heads / m.n_kv_heads;
  const int kvd = m.kv_dim();
  const float scale = cis2_rsqrt_cr((float)head_dim);

  cis2_k_embed(m.embed_tokens, (int)token_id, hidden, ws.h);
  if (trace && trace->on()) trace->emit(pos, -1, "embedding", ws.h, (size_t)hidden);

  for (int li = 0; li < m.n_layers; ++li) {
    const Cis2Layer &L = m.layers[(size_t)li];

    cis2_rmsnorm(ws.h, L.input_layernorm, m.eps, hidden, ws.sq, ws.red, ws.ln);
    if (trace && trace->on()) trace->emit(pos, li, "norm1", ws.ln, (size_t)hidden);

    cis2_k_matvec(L.q_proj, ws.ln, hidden, hidden, ws.q);
    cis2_k_add_bias(ws.q, L.q_bias, hidden);
    if (trace && trace->on()) trace->emit(pos, li, "q", ws.q, (size_t)hidden);
    cis2_k_matvec(L.k_proj, ws.ln, kvd, hidden, ws.k);
    cis2_k_add_bias(ws.k, L.k_bias, kvd);
    if (trace && trace->on()) trace->emit(pos, li, "k", ws.k, (size_t)kvd);
    cis2_k_matvec(L.v_proj, ws.ln, kvd, hidden, ws.v);
    cis2_k_add_bias(ws.v, L.v_bias, kvd);
    if (trace && trace->on()) trace->emit(pos, li, "v", ws.v, (size_t)kvd);

    cis2_k_rope(ws.q, n_heads, head_dim, pos, m.inv_freq);
    if (trace && trace->on()) trace->emit(pos, li, "rope_q", ws.q, (size_t)hidden);
    cis2_k_rope(ws.k, m.n_kv_heads, head_dim, pos, m.inv_freq);
    if (trace && trace->on()) trace->emit(pos, li, "rope_k", ws.k, (size_t)kvd);

    // The cache stores post-RoPE keys and pre-RoPE values, and a cached key
    // is never re-rotated at a later position (README §4.24).
    cis2_k_store_kv(ws.k, ws.kcache[(size_t)li], kvd, pos);
    cis2_k_store_kv(ws.v, ws.vcache[(size_t)li], kvd, pos);

    cis2_k_scores(ws.q, ws.kcache[(size_t)li], n_heads, group, head_dim, kvd,
                  pos, scale, ws.scores);
    if (trace && trace->on())
      trace->emit(pos, li, "scores", ws.scores, (size_t)n_heads * (size_t)(pos + 1));
    cis2_k_softmax(ws.scores, n_heads, pos);
    if (trace && trace->on())
      trace->emit(pos, li, "softmax", ws.scores, (size_t)n_heads * (size_t)(pos + 1));

    cis2_k_attn_weighted_sum(ws.scores, ws.vcache[(size_t)li], n_heads, group,
                             head_dim, kvd, pos, ws.attn_out);
    if (trace && trace->on()) trace->emit(pos, li, "attn_out", ws.attn_out, (size_t)hidden);

    cis2_k_matvec(L.o_proj, ws.attn_out, hidden, hidden, ws.o);
    if (trace && trace->on()) trace->emit(pos, li, "o_proj", ws.o, (size_t)hidden);
    cis2_k_add(ws.h, ws.o, hidden, ws.h2);
    { float *t = ws.h; ws.h = ws.h2; ws.h2 = t; }
    if (trace && trace->on()) trace->emit(pos, li, "resid1", ws.h, (size_t)hidden);

    cis2_rmsnorm(ws.h, L.post_attention_layernorm, m.eps, hidden, ws.sq, ws.red, ws.ln);
    if (trace && trace->on()) trace->emit(pos, li, "norm2", ws.ln, (size_t)hidden);
    cis2_k_matvec(L.gate_proj, ws.ln, m.inter, hidden, ws.gate);
    if (trace && trace->on()) trace->emit(pos, li, "gate", ws.gate, (size_t)m.inter);
    cis2_k_matvec(L.up_proj, ws.ln, m.inter, hidden, ws.up);
    if (trace && trace->on()) trace->emit(pos, li, "up", ws.up, (size_t)m.inter);
    cis2_k_silu_mul(ws.gate, ws.up, m.inter, ws.hid);
    if (trace && trace->on()) trace->emit(pos, li, "silu_mul", ws.hid, (size_t)m.inter);
    cis2_k_matvec(L.down_proj, ws.hid, hidden, m.inter, ws.down);
    if (trace && trace->on()) trace->emit(pos, li, "down", ws.down, (size_t)hidden);
    cis2_k_add(ws.h, ws.down, hidden, ws.h2);
    { float *t = ws.h; ws.h = ws.h2; ws.h2 = t; }
    if (trace && trace->on()) trace->emit(pos, li, "resid2", ws.h, (size_t)hidden);
  }

  cis2_rmsnorm(ws.h, m.final_norm, m.eps, hidden, ws.sq, ws.red, ws.hn);
  if (trace && trace->on()) trace->emit(pos, -1, "final_norm", ws.hn, (size_t)hidden);
  cis2_k_matvec(m.lm_head_weights(), ws.hn, m.vocab, hidden, ws.logits);
  if (trace && trace->on()) trace->emit(pos, -1, "logits", ws.logits, (size_t)m.vocab);
}

// Greedy argmax over the logits: sequential scan, strict `>`, so the FIRST
// maximum wins (src/main.rs, "for (idx, &v) in logits.iter().enumerate()").
inline uint32_t cis2_argmax(const float *logits_host, int n) {
  int best_idx = 0;
  float best_val = logits_host[0];
  for (int i = 0; i < n; ++i) {
    if (logits_host[i] > best_val) {
      best_val = logits_host[i];
      best_idx = i;
    }
  }
  return (uint32_t)best_idx;
}

#endif  // CIS2_MODEL_H
