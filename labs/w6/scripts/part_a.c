/* w6 Part A: exhaustive binary32 comparison of expf implementations.
 *
 * Compares, for every binary32 input in a range, the result bits of
 *   (i)   glibc expf (system libm, ifunc-dispatched),
 *   (ii)  cis2_exp_pinned (via pinned_exp.cpp, wrapper w6_pinned_exp),
 * against
 *   (iii) CORE-MATH cr_expf (correctly rounded).
 * Distance is the ULP distance on the ordered-integer image of the results
 * (signed zeros identified, infinity one step above the largest finite).
 *
 * Usage: part_a --range neg|pos|band|all-w6 | --lo HEXBITS --hi HEXBITS
 *               [--ftz] [--stride S] [--limit N]
 *   neg  = [-88, 0]        bits ordered 0xC2B00000 .. +0
 *   pos  = (0, 88]         bits 0x00000001 .. 0x42B00000
 *   band = (88, 88.7228]   bits 0x42B00001 .. 0x42B17217 (spec-guard band)
 *   --ftz   set MXCSR FTZ|DAZ in every thread (the engine runs with both)
 *   --limit N  smoke: only the lowest N ordered values of the range
 *   --stride S smoke: take every S-th ordered value
 * Output: RESULT/SMOKE lines, one per implementation. */
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <xmmintrin.h>

extern float cr_expf(float);
extern float w6_pinned_exp(float);

static inline uint32_t f2u(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
static inline float u2f(uint32_t u) { float f; memcpy(&f, &u, 4); return f; }
/* ordered integer: monotone in the float value, -0 and +0 both 0 */
static inline int64_t ord(uint32_t b) {
  return (b & 0x80000000u) ? -(int64_t)(b & 0x7fffffffu) : (int64_t)b;
}
static inline uint32_t unord(int64_t o) {
  return o < 0 ? (uint32_t)(0x80000000u | (uint32_t)(-o)) : (uint32_t)o;
}
static inline int64_t udist(uint32_t a, uint32_t b) {
  int64_t d = ord(a) - ord(b);
  return d < 0 ? -d : d;
}

typedef struct { int64_t max; uint64_t ge1, eq0, d1, d2, d3p; int64_t worst; } Acc;

static void accum(Acc *a, int64_t d, int64_t o) {
  if (d == 0) a->eq0++;
  else { a->ge1++; if (d == 1) a->d1++; else if (d == 2) a->d2++; else a->d3p++; }
  if (d > a->max || (d == a->max && d > 0 && o < a->worst)) { a->max = d; a->worst = o; }
}

static const char *variant_name(void) {
  /* glibc 2.41 sysdeps/x86_64/fpu/multiarch/e_expf.c selects the FMA body when
   * FMA and AVX2 are usable, the FMA4 body when FMA4 is, else the baseline.
   * Names follow the PREREG (__expf_fma). The resolved target offset inside
   * libm is printed separately (VARIANT: line) for corroboration with the
   * resolver disassembly done by run_partA.sh. */
  __builtin_cpu_init();
  if (__builtin_cpu_supports("fma") && __builtin_cpu_supports("avx2")) return "__expf_fma";
  return "__expf_sse2";
}

int main(int argc, char **argv) {
  const char *rname = NULL;
  uint32_t lo = 0, hi = 0;
  int ftz = 0, have = 0;
  int64_t stride = 1, limit = -1;
  for (int i = 1; i < argc; ++i) {
    if (!strcmp(argv[i], "--range") && i + 1 < argc) {
      rname = argv[++i];
      if (!strcmp(rname, "neg")) { lo = 0xC2B00000u; hi = 0x00000000u; }
      else if (!strcmp(rname, "pos")) { lo = 0x00000001u; hi = 0x42B00000u; }
      else if (!strcmp(rname, "band")) { lo = 0x42B00001u; hi = 0x42B17217u; }
      else { fprintf(stderr, "bad --range\n"); return 2; }
      have = 1;
    } else if (!strcmp(argv[i], "--lo") && i + 1 < argc) { lo = (uint32_t)strtoul(argv[++i], 0, 16); have = 1; }
    else if (!strcmp(argv[i], "--hi") && i + 1 < argc) { hi = (uint32_t)strtoul(argv[++i], 0, 16); have = 1; }
    else if (!strcmp(argv[i], "--ftz")) ftz = 1;
    else if (!strcmp(argv[i], "--stride") && i + 1 < argc) stride = atoll(argv[++i]);
    else if (!strcmp(argv[i], "--limit") && i + 1 < argc) limit = atoll(argv[++i]);
    else { fprintf(stderr, "bad arg %s\n", argv[i]); return 2; }
  }
  if (!have) { fprintf(stderr, "need --range or --lo/--hi\n"); return 2; }
  int smoke = (stride != 1 || limit >= 0);
  const char *tag = smoke ? "SMOKE" : "RESULT";

  int64_t olo = ord(lo), ohi = ord(hi);
  if (olo > ohi) { fprintf(stderr, "empty range\n"); return 2; }
  int64_t span = ohi - olo + 1;
  int64_t n = (span + stride - 1) / stride;
  if (limit >= 0 && limit < n) n = limit;

  float (*gp)(float) = expf; /* resolved ifunc target through the PLT */
  const char *var = variant_name();
  printf("VARIANT: glibc_expf_ptr=%p chosen=%s fma=%d avx2=%d ftz=%d\n", (void *)gp, var,
         __builtin_cpu_supports("fma") != 0, __builtin_cpu_supports("avx2") != 0, ftz);
  fflush(stdout);

  Acc ag = {0, 0, 0, 0, 0, 0, 0}, ap = {0, 0, 0, 0, 0, 0, 0};
  uint64_t pin_inf_cr_finite = 0, glibc_inf_cr_finite = 0;
  ag.worst = ap.worst = INT64_MAX;
#pragma omp parallel
  {
    if (ftz) _mm_setcsr(_mm_getcsr() | 0x8040u);
    Acc lg = {0, 0, 0, 0, 0, 0, 0}, lp = {0, 0, 0, 0, 0, 0, 0};
    lg.worst = lp.worst = INT64_MAX;
    uint64_t lpi = 0, lgi = 0;
#pragma omp for schedule(static, 65536) nowait
    for (int64_t k = 0; k < n; ++k) {
      int64_t o = olo + k * stride;
      uint32_t xb = unord(o);
      float x = u2f(xb);
      uint32_t c = f2u(cr_expf(x));
      uint32_t g = f2u(gp(x));
      uint32_t p = f2u(w6_pinned_exp(x));
      accum(&lg, udist(g, c), o);
      accum(&lp, udist(p, c), o);
      if ((p & 0x7fffffffu) == 0x7f800000u && (c & 0x7fffffffu) != 0x7f800000u) lpi++;
      if ((g & 0x7fffffffu) == 0x7f800000u && (c & 0x7fffffffu) != 0x7f800000u) lgi++;
    }
#pragma omp critical
    {
      Acc *src[2] = {&lg, &lp}, *dst[2] = {&ag, &ap};
      for (int t = 0; t < 2; ++t) {
        Acc *s = src[t], *d = dst[t];
        d->ge1 += s->ge1; d->eq0 += s->eq0; d->d1 += s->d1; d->d2 += s->d2; d->d3p += s->d3p;
        if (s->max > d->max || (s->max == d->max && s->max > 0 && s->worst < d->worst)) {
          d->max = s->max; d->worst = s->worst;
        }
      }
      pin_inf_cr_finite += lpi; glibc_inf_cr_finite += lgi;
    }
  }
  char rb[64];
  snprintf(rb, sizeof rb, "[%a,%a]", u2f(unord(olo)), u2f(unord(olo + (n - 1) * stride)));
  const char *impls[2] = {"glibc", "pinned"};
  Acc *as[2] = {&ag, &ap};
  for (int t = 0; t < 2; ++t) {
    Acc *a = as[t];
    printf("%s: OK w6-partA impl=%s range=%s name=%s n=%lld max_ulp=%lld count_ulp_ge1=%llu "
           "worst_x=0x%08x glibc_variant=%s\n",
           tag, impls[t], rb, rname ? rname : "custom", (long long)n, (long long)a->max,
           (unsigned long long)a->ge1, a->max ? unord(a->worst) : 0u, var);
    printf("DETAIL: impl=%s eq0=%llu d1=%llu d2=%llu d3plus=%llu inf_where_cr_finite=%llu\n",
           impls[t], (unsigned long long)a->eq0, (unsigned long long)a->d1,
           (unsigned long long)a->d2, (unsigned long long)a->d3p,
           (unsigned long long)(t == 0 ? glibc_inf_cr_finite : pin_inf_cr_finite));
  }
  /* list up to 16 inputs reaching the maximum distance, per implementation */
  for (int t = 0; t < 2; ++t) {
    if (as[t]->max == 0) continue;
    int found = 0;
    for (int64_t k = 0; k < n && found < 16; ++k) {
      int64_t o = olo + k * stride;
      float x = u2f(unord(o));
      uint32_t c = f2u(cr_expf(x));
      uint32_t r = f2u(t == 0 ? gp(x) : w6_pinned_exp(x));
      if (udist(r, c) == as[t]->max) {
        printf("WORST: impl=%s x=0x%08x result=0x%08x cr=0x%08x\n", impls[t], unord(o), r, c);
        found++;
      }
    }
  }
  return 0;
}
