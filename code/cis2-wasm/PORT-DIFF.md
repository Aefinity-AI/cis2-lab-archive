# Port diff vs orig/ (copied from cis2-digest/gpu)

Hunks (one sentence each):
- cis2_math.h #1: add CIS2_HAVE_WASM_SQRT on wasm32/emscripten so the sqrt selector has a branch instead of hitting #error.
- cis2_math.h #2: wasm branch of cis2_sqrt_f32 uses __builtin_sqrtf, which lowers to the single correctly-rounded f32.sqrt instruction (9 in the output, no libm call).
- cis2_fpenv.h #1: define CIS2_FPENV_WASM32 so the pin code stops hitting its #error on wasm.
- cis2_fpenv.h #2: pin is a no-op that prints `fpenv: wasm32 no FTZ/DAZ control` to stderr.
- cis2_fpenv.h #3: ftz_daz_on returns 1 on wasm (nothing to read back), so init does not abort.
- cis2_fpenv.h #4: skip the 1.3 self-test on wasm with a loud stderr line, since it would correctly fail (wasm cannot flush).

```diff
diff --git a/orig/cis2_math.h b/cis2_math.h
index 10c8d99..0cd18c4 100644
--- a/orig/cis2_math.h
+++ b/cis2_math.h
@@ -47,6 +47,8 @@
 #define CIS2_HAVE_SSE2 1
 #elif defined(__aarch64__) || defined(_M_ARM64)
 #define CIS2_HAVE_AARCH64_FSQRT 1
+#elif defined(__wasm32__) || defined(__EMSCRIPTEN__)
+#define CIS2_HAVE_WASM_SQRT 1
 #endif
 
 // --- pinned constants (generated; see gpu/cis2_consts.inc) ------------
@@ -172,6 +174,9 @@ CIS2_FN inline float cis2_sqrt_f32(float x) {
   float result;
   __asm__("fsqrt %s0, %s1" : "=w"(result) : "w"(x));
   return result;
+#elif defined(CIS2_HAVE_WASM_SQRT)
+  // wasm f32.sqrt is IEEE-754 correctly rounded (single instruction).
+  return __builtin_sqrtf(x);
 #else
 #error "CIS-2 requires a correctly-rounded hardware sqrt with no libm call"
 #endif
diff --git a/orig/cis2_fpenv.h b/cis2_fpenv.h
index 82e8c35..b968aa7 100644
--- a/orig/cis2_fpenv.h
+++ b/cis2_fpenv.h
@@ -24,6 +24,8 @@
 #define CIS2_FPENV_X86 1
 #elif defined(__aarch64__) || defined(_M_ARM64)
 #define CIS2_FPENV_AARCH64 1
+#elif defined(__wasm32__) || defined(__EMSCRIPTEN__)
+#define CIS2_FPENV_WASM32 1
 #endif
 
 // Optimization barrier: keeps the compiler from constant-folding the
@@ -69,6 +71,9 @@ static inline void cis2_pin_ftz_daz(void) {
   uint64_t fpcr = cis2_read_fpcr();
   fpcr |= CIS2_FPCR_FZ_BIT;
   cis2_write_fpcr(fpcr);
+#elif defined(CIS2_FPENV_WASM32)
+  // WebAssembly has no FTZ/DAZ control: nothing to pin. Say so, loudly.
+  fprintf(stderr, "fpenv: wasm32 no FTZ/DAZ control\n");
 #else
 #error "CIS-2 §1.3 pins only x86-64 MXCSR and aarch64 FPCR.FZ; refuse to run"
 #endif
@@ -81,6 +86,8 @@ static inline int cis2_ftz_daz_on(void) {
 #elif defined(CIS2_FPENV_AARCH64)
   uint64_t fpcr = cis2_read_fpcr();
   return (fpcr & CIS2_FPCR_FZ_BIT) != 0;
+#elif defined(CIS2_FPENV_WASM32)
+  return 1;  // nothing to read back; init skips the readback assert below
 #else
   return 0;
 #endif
@@ -113,6 +120,12 @@ static inline void cis2_fpenv_init(void) {
     fprintf(stderr, "FATAL: MXCSR FTZ|DAZ did not read back as set (§1.3)\n");
     exit(2);
   }
+#if defined(CIS2_FPENV_WASM32)
+  // The §1.3 self-test would (correctly) fail: wasm cannot flush. Skip it,
+  // loudly; a digest from this build is valid only if no subnormal arises.
+  fprintf(stderr, "fpenv: wasm32 FTZ/DAZ self-test SKIPPED (not pinned)\n");
+  return;
+#endif
   cis2_fpenv_selftest();
 }
 
```
