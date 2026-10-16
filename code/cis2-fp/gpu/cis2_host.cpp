// gpu/cis2_host.cpp — driver for the CUDA-portable CIS-2 v0.3b forward
// pass. Loads the checkpoint, replays the reference tokenization from a
// file, greedy-decodes N tokens and folds the CIS2_REF witness exactly as
// src/main.rs does. Prints the same field names as the Rust reference so
// the two outputs can be diffed line for line.
//
//   ./cis2_host --weights-dir weights --ids ids.txt --gen-toks 16 \
//               [--trace trace.txt]
//
// Tokenization is NOT re-implemented: `--ids` is produced by the Rust
// reference's `--dump-ids` flag, so the two implementations are compared on
// arithmetic, which is the claim, and not on tokenizer behaviour.

#include "cis2_fpenv.h"
#include "cis2_math.h"
#include "cis2_model.h"
#include "cis2_sha256.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <string>
#include <vector>

static std::vector<uint32_t> read_ids(const std::string &path) {
  std::string text = cis2_read_file(path);
  std::vector<uint32_t> ids;
  size_t i = 0;
  while (i < text.size()) {
    while (i < text.size() && (text[i] == '\n' || text[i] == '\r' ||
                               text[i] == ' ' || text[i] == '\t' || text[i] == ','))
      ++i;
    if (i >= text.size()) break;
    size_t j = i;
    while (j < text.size() && text[j] >= '0' && text[j] <= '9') ++j;
    if (j == i) {
      fprintf(stderr, "FATAL: %s: expected a decimal token id at byte %zu\n",
              path.c_str(), i);
      exit(2);
    }
    ids.push_back((uint32_t)strtoul(text.substr(i, j - i).c_str(), nullptr, 10));
    i = j;
  }
  if (ids.empty()) { fprintf(stderr, "FATAL: %s: no token ids\n", path.c_str()); exit(2); }
  return ids;
}

static std::string ids_debug(const std::vector<uint32_t> &v) {
  std::string s = "[";
  for (size_t i = 0; i < v.size(); ++i) {
    if (i) s += ", ";
    char b[16];
    snprintf(b, sizeof(b), "%u", v[i]);
    s += b;
  }
  s += "]";
  return s;
}

int main(int argc, char **argv) {
  // §1.3 — pin FTZ|DAZ, assert the readback, run the adversarial self-test,
  // all before any decode-path fp32 arithmetic.
  cis2_fpenv_init();

  std::string weights_dir = "weights";
  std::string ids_path;
  std::string trace_path;
  int gen_toks = 16;
  int prompt_idx = 0;

  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if (a == "--weights-dir" && i + 1 < argc) weights_dir = argv[++i];
    else if (a == "--ids" && i + 1 < argc) ids_path = argv[++i];
    else if (a == "--gen-toks" && i + 1 < argc) gen_toks = atoi(argv[++i]);
    else if (a == "--trace" && i + 1 < argc) trace_path = argv[++i];
    else if (a == "--prompt-idx" && i + 1 < argc) prompt_idx = atoi(argv[++i]);
    else { fprintf(stderr, "FATAL: unknown CLI argument: %s\n", a.c_str()); return 2; }
  }
  if (ids_path.empty()) {
    fprintf(stderr, "FATAL: --ids FILE is required (produce it with "
                    "`cargo run --release --bin cis2_ref -- --dump-ids FILE`)\n");
    return 2;
  }

  const std::string weights_path = weights_dir + "/model.safetensors";
  const std::string tokenizer_path = weights_dir + "/tokenizer.json";
  const std::string config_path = weights_dir + "/config.json";

  unsigned char weights_sha[32], tokenizer_sha[32], config_sha[32];
  cis2_sha256_file(weights_path, weights_sha);
  cis2_sha256_file(tokenizer_path, tokenizer_sha);
  cis2_sha256_file(config_path, config_sha);

  // ---- config.json -----------------------------------------------------
  Cis2Json cfg = cis2_json_parse(cis2_read_file(config_path));
  auto need = [&](const char *k) -> const Cis2Json & {
    const Cis2Json *v = cfg.get(k);
    if (!v) { fprintf(stderr, "FATAL: config.json missing %s\n", k); exit(2); }
    return *v;
  };
  Cis2Model model;
  model.hidden = (int)need("hidden_size").num;
  model.inter = (int)need("intermediate_size").num;
  model.n_layers = (int)need("num_hidden_layers").num;
  model.n_heads = (int)need("num_attention_heads").num;
  model.n_kv_heads = (int)need("num_key_value_heads").num;
  model.vocab = (int)need("vocab_size").num;
  // Read as f64 (correctly-rounded decimal parse) and narrow ONCE, as
  // `config["rms_norm_eps"].as_f64().unwrap() as f32` does.
  model.eps = (float)need("rms_norm_eps").num;
  const double rope_theta = need("rope_theta").num;
  model.head_dim = model.hidden / model.n_heads;
  bool tie_word_embeddings = true;
  if (const Cis2Json *t = cfg.get("tie_word_embeddings"))
    tie_word_embeddings = (t->kind == Cis2Json::BOOL) ? t->b : true;

  // ---- §6.6 table digest, asserted against the Rust value --------------
  unsigned char table_dig[32];
  cis2_table_digest(table_dig);

  // ---- §7.2 pinned inv_freq table + its digest -------------------------
  cis2_build_inv_freq(model, rope_theta);

  // ---- weights ---------------------------------------------------------
  fprintf(stderr, "loading + widening weights (bf16 -> fp32, exact bit-shift)...\n");
  Cis2SafeTensors st;
  st.open(weights_path);
  const size_t H = (size_t)model.hidden, I = (size_t)model.inter;
  const size_t KV = (size_t)model.n_kv_heads * (size_t)model.head_dim;
  const size_t V = (size_t)model.vocab;

  model.embed_tokens = st.load_bf16("model.embed_tokens.weight", {V, H});
  model.layers.resize((size_t)model.n_layers);
  for (int i = 0; i < model.n_layers; ++i) {
    char nb[128];
    auto nm = [&](const char *suffix) {
      snprintf(nb, sizeof(nb), "model.layers.%d.%s", i, suffix);
      return std::string(nb);
    };
    Cis2Layer &L = model.layers[(size_t)i];
    L.input_layernorm = st.load_bf16(nm("input_layernorm.weight"), {H});
    L.post_attention_layernorm = st.load_bf16(nm("post_attention_layernorm.weight"), {H});
    L.q_proj = st.load_bf16(nm("self_attn.q_proj.weight"), {H, H});
    L.k_proj = st.load_bf16(nm("self_attn.k_proj.weight"), {KV, H});
    L.v_proj = st.load_bf16(nm("self_attn.v_proj.weight"), {KV, H});
    L.o_proj = st.load_bf16(nm("self_attn.o_proj.weight"), {H, H});
    L.gate_proj = st.load_bf16(nm("mlp.gate_proj.weight"), {I, H});
    L.up_proj = st.load_bf16(nm("mlp.up_proj.weight"), {I, H});
    L.down_proj = st.load_bf16(nm("mlp.down_proj.weight"), {H, I});
    // Optional QKV bias — absent for Llama-family SmolLM2, present for
    // Qwen2-family checkpoints (attention_bias=true).
    L.q_bias = st.has(nm("self_attn.q_proj.bias")) ? st.load_bf16(nm("self_attn.q_proj.bias"), {H}) : nullptr;
    L.k_bias = st.has(nm("self_attn.k_proj.bias")) ? st.load_bf16(nm("self_attn.k_proj.bias"), {KV}) : nullptr;
    L.v_bias = st.has(nm("self_attn.v_proj.bias")) ? st.load_bf16(nm("self_attn.v_proj.bias"), {KV}) : nullptr;
  }
  model.final_norm = st.load_bf16("model.norm.weight", {H});
  model.lm_head = tie_word_embeddings ? nullptr : st.load_bf16("lm_head.weight", {V, H});
  st.blob.clear();
  st.blob.shrink_to_fit();
  st.data = nullptr;
  fprintf(stderr, "weights loaded.\n");

  // ---- prompt ----------------------------------------------------------
  std::vector<uint32_t> prompt_ids = read_ids(ids_path);
  fprintf(stderr, "[prompt %d] token ids (%zu toks): %s\n", prompt_idx,
          prompt_ids.size(), ids_debug(prompt_ids).c_str());

  Cis2Workspace ws;
  ws.alloc(model, (int)prompt_ids.size() + gen_toks);

  Cis2Trace trace;
  if (!trace_path.empty()) {
    trace.fp = fopen(trace_path.c_str(), "wb");
    if (!trace.fp) { fprintf(stderr, "FATAL: cannot write %s\n", trace_path.c_str()); return 2; }
  }

  // ---- §12.1 witness header: RAW 32-byte digests, never hex ASCII ------
  Cis2Sha256 witness;
  witness.update(weights_sha, 32);
  witness.update(tokenizer_sha, 32);
  witness.update(config_sha, 32);
  witness.update(table_dig, 32);
  witness.update(model.inv_freq_table_digest, 32);
  for (size_t i = 0; i < prompt_ids.size(); ++i) witness.update_u32le(prompt_ids[i]);

  std::vector<uint32_t> all_token_ids = prompt_ids;
  std::vector<float> logits_host((size_t)model.vocab);

  // Prefill: every prompt position, populating the KV cache.
  for (size_t pos = 0; pos < prompt_ids.size(); ++pos)
    cis2_forward_token(model, ws, (int)pos, prompt_ids[pos], &trace);
  cis2_download(logits_host.data(), ws.logits, (size_t)model.vocab);

  for (int step = 0; step < gen_toks; ++step) {
    // `logits_host` holds the logits for the last position already
    // processed — for step 0 that is the final prefill position, not a
    // fresh forward pass (README §4.23).
    uint32_t next_id = cis2_argmax(logits_host.data(), model.vocab);

    for (int i = 0; i < model.vocab; ++i)
      witness.update_u32le(cis2_f32_bits(logits_host[(size_t)i]));
    witness.update_u32le(next_id);

    all_token_ids.push_back(next_id);
    int pos = (int)prompt_ids.size() + step;
    cis2_forward_token(model, ws, pos, next_id, &trace);
    cis2_download(logits_host.data(), ws.logits, (size_t)model.vocab);
    fprintf(stderr, "[run1] step %d: token_id=%u\n", step, next_id);
  }

  unsigned char wdig[32];
  witness.finalize(wdig);
  Cis2Sha256 ah;
  for (size_t i = 0; i < all_token_ids.size(); ++i) ah.update_u32le(all_token_ids[i]);
  unsigned char adig[32];
  ah.finalize(adig);

  if (trace.fp) fclose(trace.fp);

  printf("weights_sha256=%s\n", cis2_hex(weights_sha, 32).c_str());
  printf("tokenizer_sha256=%s\n", cis2_hex(tokenizer_sha, 32).c_str());
  printf("config_sha256=%s\n", cis2_hex(config_sha, 32).c_str());
  printf("table_digest=%s\n", cis2_hex(table_dig, 32).c_str());
  printf("inv_freq_table_digest=%s\n",
         cis2_hex(model.inv_freq_table_digest, 32).c_str());
  printf("prompt_idx=%d prompt_tokens=%s\n", prompt_idx, ids_debug(prompt_ids).c_str());
  printf("prompt_idx=%d run1_tokens=%s\n", prompt_idx, ids_debug(all_token_ids).c_str());
  printf("prompt_idx=%d run1_witness_digest=%s\n", prompt_idx, cis2_hex(wdig, 32).c_str());
  printf("prompt_idx=%d run1_argmax_digest=%s\n", prompt_idx, cis2_hex(adig, 32).c_str());
  // v0.4 CANDIDATE (E18c): reduction_mode is receipt metadata mirroring
  // main.rs's printed field, selected at compile time by
  // -DCIS2_REDUCTION_TREE (gpu/README.md / design doc §4-§5). It is not
  // folded into the witness above, so it cannot change wdig/adig either
  // way.
#ifdef CIS2_REDUCTION_TREE
  printf("prompt_idx=%d reduction_mode=tree\n", prompt_idx);
  printf("CIS2_REF digest=%s prompt_idx=%d prompt_toks=%zu gen_toks=%d dtype=fp32 reduction_mode=tree\n",
         cis2_hex(wdig, 32).c_str(), prompt_idx, prompt_ids.size(), gen_toks);
#else
  printf("prompt_idx=%d reduction_mode=sequential\n", prompt_idx);
  printf("CIS2_REF digest=%s prompt_idx=%d prompt_toks=%zu gen_toks=%d dtype=fp32 reduction_mode=sequential\n",
         cis2_hex(wdig, 32).c_str(), prompt_idx, prompt_ids.size(), gen_toks);
#endif

  ws.free_all();
  return 0;
}
