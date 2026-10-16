// gpu/test_math.cpp — bit-exactness gate for gpu/cis2_math.h against the
// Rust reference (src/math.rs) over a large deterministic input sweep.
//
// The sweep and its expected outputs are NOT hand-typed: they are produced
// by `cargo run --release --bin math_dump`, which calls the very functions
// in src/math.rs that the decode path uses, under the same pinned FTZ/DAZ
// environment. This binary replays the recorded inputs through the C++
// port and requires every result to be bit-identical.
//
// Golden file layout (little-endian):
//   magic "CIS2MTH1" | u32 n_inputs | u32 n_funcs(=6)
//   then n_inputs records of: u32 x_bits, u32 out_bits[6]
//   function order: exp, sin, cos, ln, silu, rsqrt

#include "cis2_fpenv.h"
#include "cis2_math.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *kFuncNames[6] = {"exp_pinned", "sin_pinned",  "cos_pinned",
                                    "ln_pinned",  "silu_pinned", "rsqrt_cr"};

static float apply(int f, float x) {
  switch (f) {
    case 0: return cis2_exp_pinned(x);
    case 1: return cis2_sin_pinned(x);
    case 2: return cis2_cos_pinned(x);
    case 3: return cis2_ln_pinned(x);
    case 4: return cis2_silu_pinned(x);
    default: return cis2_rsqrt_cr(x);
  }
}

int main(int argc, char **argv) {
  cis2_fpenv_init();

  const char *path = (argc > 1) ? argv[1] : "gpu/math_golden.bin";
  FILE *fp = fopen(path, "rb");
  if (!fp) { fprintf(stderr, "cannot open golden file %s\n", path); return 2; }
  fseek(fp, 0, SEEK_END);
  long sz = ftell(fp);
  fseek(fp, 0, SEEK_SET);
  unsigned char *buf = (unsigned char *)malloc((size_t)sz);
  if (fread(buf, 1, (size_t)sz, fp) != (size_t)sz) {
    fprintf(stderr, "short read on %s\n", path); return 2;
  }
  fclose(fp);
  if (sz < 16 || memcmp(buf, "CIS2MTH1", 8) != 0) {
    fprintf(stderr, "bad magic in %s\n", path); return 2;
  }
  uint32_t n, nf;
  memcpy(&n, buf + 8, 4);
  memcpy(&nf, buf + 12, 4);
  if (nf != 6 || (long)(16 + (size_t)n * 28) != sz) {
    fprintf(stderr, "golden file shape mismatch (n=%u nf=%u sz=%ld)\n", n, nf, sz);
    return 2;
  }

  // Regression check from §5.1: dot_seq is order-sensitive by design.
  {
    const float a[3] = {1.0e8f, 1.0f, -1.0e8f};
    const float b[3] = {1.0f, 1.0f, 1.0f};
    float got = cis2_dot_seq(a, b, 3);
    if (cis2_f32_bits(got) != cis2_f32_bits(0.0f)) {
      fprintf(stderr, "FAIL dot_seq order check: got bits 0x%08x, want 0x00000000\n",
              cis2_f32_bits(got));
      return 1;
    }
  }
  // §4.1 widening spot checks (same three the Rust unit test uses).
  if (cis2_f32_bits(cis2_widen_bf16(0x3F80)) != 0x3F800000u ||
      cis2_f32_bits(cis2_widen_bf16(0x0000)) != 0x00000000u ||
      cis2_f32_bits(cis2_widen_bf16(0x8000)) != 0x80000000u) {
    fprintf(stderr, "FAIL widen_bf16 bit check\n");
    return 1;
  }

  size_t fails[6] = {0, 0, 0, 0, 0, 0};
  size_t total_fail = 0;
  for (uint32_t i = 0; i < n; ++i) {
    const unsigned char *rec = buf + 16 + (size_t)i * 28;
    uint32_t xb; memcpy(&xb, rec, 4);
    float x = cis2_f32_from_bits(xb);
    for (int f = 0; f < 6; ++f) {
      uint32_t want; memcpy(&want, rec + 4 + 4 * f, 4);
      uint32_t got = cis2_f32_bits(apply(f, x));
      if (got == want) continue;
      // Both NaN counts as equal only if the bit patterns match too — the
      // Rust side pins f32::NAN = 0x7FC00000 and so does the C++ port, so
      // this is a strict bit comparison with no NaN escape hatch.
      fails[f]++;
      if (total_fail < 20) {
        fprintf(stderr,
                "MISMATCH %s(x=0x%08x = %.9g): got 0x%08x, rust 0x%08x\n",
                kFuncNames[f], xb, (double)x, got, want);
      }
      total_fail++;
    }
  }

  printf("test_math: %u inputs x 6 functions = %llu comparisons\n", n,
         (unsigned long long)n * 6ull);
  for (int f = 0; f < 6; ++f)
    printf("  %-12s mismatches: %zu\n", kFuncNames[f], fails[f]);
  free(buf);
  if (total_fail) {
    printf("test_math: FAIL (%zu mismatches)\n", total_fail);
    return 1;
  }
  printf("test_math: PASS (bit-exact vs Rust src/math.rs)\n");
  return 0;
}
