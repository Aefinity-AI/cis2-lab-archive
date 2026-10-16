// gpu/cis2_fpenv.h — CIS-2 v0.3b §1.3 floating-point environment pin.
//
// Host (x86-64): set MXCSR bit 15 (FTZ) and bit 6 (DAZ) by direct
// read-modify-write, then ASSERT the readback — mirroring
// src/denormal.rs::pin_ftz_daz / ftz_daz_on, and run §1.3's adversarial
// self-test before any decode-path arithmetic.
//
// Device (CUDA): FTZ/DAZ is not a runtime register but a compile-time code
// generation choice; `nvcc -ftz=true` makes every single-precision
// arithmetic instruction flush denormal inputs and outputs to zero, which
// is the device-side equivalent of the pin below. There is no runtime
// readback to assert, so `cis2_assert_device_ftz_flag()` documents the
// requirement and fails the build if the flag was not passed.

#ifndef CIS2_FPENV_H
#define CIS2_FPENV_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#if defined(__x86_64__) || defined(_M_X64)
#include <emmintrin.h>
#define CIS2_FPENV_X86 1
#elif defined(__aarch64__) || defined(_M_ARM64)
#define CIS2_FPENV_AARCH64 1
#elif defined(__wasm32__) || defined(__EMSCRIPTEN__)
#define CIS2_FPENV_WASM32 1
#endif

// Optimization barrier: keeps the compiler from constant-folding the
// adversarial self-test's arithmetic and masking a broken pin (§1.3's
// "must be checked with the operands passed through an optimization
// barrier" requirement; the Rust reference uses std::hint::black_box).
static inline float cis2_black_box(float x) {
#if defined(CIS2_FPENV_X86) && (defined(__GNUC__) || defined(__clang__))
  asm volatile("" : "+x"(x) : : "memory");  // "x" = SSE/AVX register
#elif defined(CIS2_FPENV_AARCH64) && (defined(__GNUC__) || defined(__clang__))
  asm volatile("" : "+w"(x) : : "memory");  // "w" = AArch64 FP/SIMD register
#endif
  return x;
}

// aarch64: FPCR.FZ (bit 24) is the single flush-to-zero control for both
// inputs and outputs of scalar and Advanced SIMD binary32/binary64
// arithmetic — no separate DAZ bit exists on this ISA. Mirrors
// src/denormal.rs::pin_ftz_daz's aarch64 arm exactly: same bit (24), same
// mrs/msr fpcr read-modify-write-readback sequence, and FZ16 (bit 19) is
// deliberately left untouched (this reference never uses fp16).
#if defined(CIS2_FPENV_AARCH64)
#define CIS2_FPCR_FZ_BIT (1ull << 24)

static inline uint64_t cis2_read_fpcr(void) {
  uint64_t fpcr;
  __asm__ __volatile__("mrs %0, fpcr" : "=r"(fpcr));
  return fpcr;
}

static inline void cis2_write_fpcr(uint64_t fpcr) {
  __asm__ __volatile__("msr fpcr, %0" : : "r"(fpcr));
}
#endif

static inline void cis2_pin_ftz_daz(void) {
#if defined(CIS2_FPENV_X86)
  const unsigned FTZ_BIT = 1u << 15;
  const unsigned DAZ_BIT = 1u << 6;
  unsigned csr = _mm_getcsr();
  _mm_setcsr(csr | FTZ_BIT | DAZ_BIT);
#elif defined(CIS2_FPENV_AARCH64)
  uint64_t fpcr = cis2_read_fpcr();
  fpcr |= CIS2_FPCR_FZ_BIT;
  cis2_write_fpcr(fpcr);
#elif defined(CIS2_FPENV_WASM32)
  // WebAssembly has no FTZ/DAZ control: nothing to pin. Say so, loudly.
  fprintf(stderr, "fpenv: wasm32 no FTZ/DAZ control\n");
#else
#error "CIS-2 §1.3 pins only x86-64 MXCSR and aarch64 FPCR.FZ; refuse to run"
#endif
}

static inline int cis2_ftz_daz_on(void) {
#if defined(CIS2_FPENV_X86)
  unsigned csr = _mm_getcsr();
  return ((csr & (1u << 15)) != 0) && ((csr & (1u << 6)) != 0);
#elif defined(CIS2_FPENV_AARCH64)
  uint64_t fpcr = cis2_read_fpcr();
  return (fpcr & CIS2_FPCR_FZ_BIT) != 0;
#elif defined(CIS2_FPENV_WASM32)
  return 1;  // nothing to read back; init skips the readback assert below
#else
  return 0;
#endif
}

// §1.3 adversarial self-test — MUST run and pass before decode.
static inline void cis2_fpenv_selftest(void) {
  union { float f; uint32_t u; } c;
  float smallest_normal = 1.17549435082228750797e-38f;  // 2^-126
  float tiny = 1.0e-10f;
  float product = cis2_black_box(smallest_normal) * cis2_black_box(tiny);
  c.f = product;
  if (!(product == 0.0f) || (c.u >> 31) != 0u) {
    fprintf(stderr, "FATAL: FTZ self-test failed: 2^-126 * 1e-10 = %e (bits 0x%08x)\n",
            (double)product, c.u);
    exit(2);
  }
  c.u = 0x00000001u;  // smallest positive subnormal
  float flushed = cis2_black_box(c.f) + cis2_black_box(0.0f);
  c.f = flushed;
  if (!(flushed == 0.0f)) {
    fprintf(stderr, "FATAL: DAZ self-test failed: subnormal + 0.0 = bits 0x%08x\n", c.u);
    exit(2);
  }
}

static inline void cis2_fpenv_init(void) {
  cis2_pin_ftz_daz();
  if (!cis2_ftz_daz_on()) {
    fprintf(stderr, "FATAL: MXCSR FTZ|DAZ did not read back as set (§1.3)\n");
    exit(2);
  }
#if defined(CIS2_FPENV_WASM32)
  // The §1.3 self-test would (correctly) fail: wasm cannot flush. Skip it,
  // loudly; a digest from this build is valid only if no subnormal arises.
  fprintf(stderr, "fpenv: wasm32 FTZ/DAZ self-test SKIPPED (not pinned)\n");
  return;
#endif
  cis2_fpenv_selftest();
}

#if defined(__CUDACC__)
// Compile-time assertion that -ftz=true was actually passed to nvcc.
//
// nvcc has NO built-in preprocessor macro that reflects -ftz=true: it is a
// PTXAS code-generation flag, not visible to the front end (confirmed on
// nvcc 12.9 — a `#pragma message` probe under `#ifdef __CUDA_FTZ` never
// fires, with or without -ftz=true on the command line). The previous
// `#if !defined(__CUDA_FTZ) ...` guard tested a macro that never exists,
// so it always errored under real CUDA compilation. Since the compiler
// can't tell us, the build script must: it passes -DCIS2_CUDA_FTZ=1
// alongside -ftz=true (see gpu/Makefile's NVCCFLAGS and
// gpu/kaggle/e18b_gpu.py's NVCCFLAGS_BASE), and this guard just checks
// that the build script did its job.
#if !defined(CIS2_CUDA_FTZ) || (CIS2_CUDA_FTZ != 1)
#error "CIS-2 §1.3 device build requires nvcc -ftz=true AND -DCIS2_CUDA_FTZ=1 (denormals flushed)"
#endif
#endif

#endif  // CIS2_FPENV_H
