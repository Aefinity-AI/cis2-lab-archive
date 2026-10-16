# 6. Mechanism, in detail

§3 states the nine gates as a contract; this section walks through how each is actually enforced
at the instruction and byte level, and how the witness chain composes them into one checkable
value — including the one place the mechanism itself was found to be misdescribed.

## 6.1 Denormal handling: FTZ/DAZ pinned and readback-verified

IEEE-754 binary32 subnormal numbers are handled differently by default on the two ISAs this
contract targets: x86_64 SSE/AVX units read the MXCSR control register (bit 15 = FTZ,
flush-to-zero on output; bit 6 = DAZ, denormals-as-zero on input), while aarch64 NEON/FP units
read FPCR bit 24 (FZ). Left at hardware defaults, whether a subnormal intermediate value is
flushed to zero or kept can differ between the two ISAs on the exact same arithmetic sequence.
CIS-2 pins both bits on before any decode-path arithmetic runs, via a direct register
read-modify-write (not a wrapper function whose correctness a caller must assume) — and then
**reads the register back** to assert the bits actually took, rather than merely asserting "we
called the setter and did not error." An adversarial unit test feeds a genuine subnormal value
through a `black_box`-guarded operation (so the compiler cannot constant-fold the subnormal away
at compile time) and asserts it flushes to zero, on both ISAs, in CI.

## 6.2 Round-to-nearest-even

CIS-2 does not set any rounding-mode control bit: IEEE-754's default rounding mode, and the
default assumed by essentially every conforming CPU floating-point unit at process start, is
round-to-nearest-even. The contract's requirement here is negative — that nothing in the decode
path changes the rounding mode away from this default — verified by absence rather than presence
(no rounding-mode-control call appears anywhere in the decode path's source).

## 6.3 No FMA contraction, enforced by disassembly

Fused multiply-add computes `a*b + c` with a single rounding, rather than rounding the product
and then rounding the sum separately — a real accuracy improvement, and exactly the kind of
compiler- or hardware-introduced degree of freedom this contract cannot tolerate, because whether
a given `a*b+c` gets contracted depends on optimization level, target CPU flags, and instruction
scheduling, none of which is under a spec author's control unless explicitly forbidden. CIS-2
writes every multiply-accumulate as two separate statements (`let p = a[i]*b[i]; acc = acc + p;`)
and never calls `f32::mul_add`, but does not stop at trusting the source: a disassembly gate
(`objdump -d` filtered for `vfmadd`/`vfnmadd`/`vfmsub`/`vfnmsub` on x86_64 and `fmadd`/`fmsub` on
aarch64) runs against the actual release binary in CI, and a mechanical grep test additionally
scans the source tree for `mul_add` calls. This was adversarially rebuilt with
`RUSTFLAGS="-C target-cpu=native"` on FMA-capable local hardware specifically to give the compiler
every opportunity to contract — the resulting binary still shows zero FMA instructions and an
unchanged digest, and the same check passes across a 20-cell `{opt-level 0,1,2,3,s} ×
{target-cpu generic,native} × {x86_64,aarch64}` matrix.

## 6.4 Scalar, strictly left-to-right reductions

Every dot product, sum-of-squares, and weighted accumulation in the decode path — matrix-vector
rows, RMSNorm's sum of squares, softmax's normalizing denominator, the attention value-mix — folds
in a plain `for` loop over index order `0..n-1`, one scalar accumulator, no pairwise-tree
reduction, no SIMD-lane reordering, no chunked partial sums recombined afterward. This matters
because fp32 addition is not associative: summing the same set of numbers in two different valid
orders can produce two different, both individually "correct," results. A regression test makes
this concrete rather than asserting it abstractly: dotting `[1e8, 1.0, -1e8]` against `[1.0, 1.0,
1.0]` in the pinned left-to-right order returns exactly `0.0_f32` (the middle `1.0` term is
entirely lost to rounding against the `1e8` partial sum before the `-1e8` term arrives), while
almost any other valid summation order returns a different, nonzero answer for the same three
numbers. Pinning order this precisely, and testing that the precision loss is exactly what pinning
predicts, is the direct fp32 analogue of CIS-1's bounded-integer-accumulator gate — except CIS-2
cannot get away with pinning only the type, because the type here (`f32`) does not make the
answer order-independent on its own.

## 6.5 Pinned transcendentals: Cephes-pattern polynomials, hex-specified coefficients, no libm

IEEE-754 mandates that `sqrt` and division be *correctly rounded* — the unique closest
representable result — so any conformant hardware unit already agrees bit-for-bit on these two
operations across ISAs; CIS-2 pins nothing further for `sqrt`/`/` and uses the hardware
instruction directly. `rsqrt_cr` (spec §6.1) is the composition of two such correctly-rounded
operations, `1.0 / x.sqrt()`; this composition is deterministic and cross-ISA-identical by
construction (both component operations are individually correctly rounded on any conformant
hardware), but the composite result is not itself guaranteed correctly rounded — composing two
correctly-rounded operations does not, in general, yield a correctly-rounded answer to the
composite function. IEEE 754-2019 §9.2 makes no rounding guarantee at all for `exp`, `sin`, `cos`,
and `ln` — it only *recommends*, and does not require, correctly-rounded results for these
functions; the actual behavior of a platform's implementation is governed by the C standard, not
IEEE-754, and glibc's own regression-testing infrastructure documents that its `libm` does not
guarantee identical rounding for these functions across architectures (glibc ships separate,
per-architecture allowed-error tables, `sysdeps/<arch>/libm-test-ulps`, precisely because observed
behavior differs by target). CIS-2 sidesteps this class of divergence entirely rather than trying
to characterize and match it: it never calls a platform
math library for any of the four functions, computing each instead as a Cephes-pattern range
reduction followed by a fixed-degree Horner-scheme polynomial evaluation, over coefficients
specified in the spec text as exact hexadecimal `f32` bit patterns (not decimal literals, which
would themselves be a source-to-binary rounding ambiguity). A dedicated numerical characterization
against a 60-digit `mpmath` oracle plus correctly-rounded-fp32 neighbor search (H2) found
`exp_pinned` accurate to ≤1 ULP and `ln_pinned` exactly 0 ULP at both pinned `rope_theta` values
used in this document's test vectors — but also found `sin_pinned`/`cos_pinned` reaching up to
1104 ULP (~1.00e-4 relative error) by decode position 19 on the pinned model's grid, traced to
catastrophic cancellation in the two-constant range reduction (`reduce_2pi`) rather than to the
polynomial itself, an accuracy limitation stated in full in §8 that does not affect the
determinism claim — the same wrong-by-1104-ULP value is still computed identically on both ISAs,
every time.

## 6.6 Theta-general RoPE `inv_freq`

Rotary position embeddings require `inv_freq[i] = theta^(-2i/head_dim)`, computed once per model
and reused every decode step. An earlier internal version of this construction hardcoded the
natural log of one specific `rope_theta` value as a literal, which technically worked for the one
model tested but silently made the "general spec" claim false for any other checkpoint. v0.2
replaced the literal with `inv_freq[i] = exp_pinned(-(2i/head_dim) · ln_pinned(rope_theta))`,
computed from whatever `rope_theta` value is actually read out of the checkpoint's `config.json`
— validated against two different `rope_theta` values (100,000 for SmolLM2-135M, 1,000,000 for
Qwen2.5-0.5B/1.5B) and confirmed to reproduce the same `inv_freq_table_digest` on SmolLM2 as the
older literal-based construction, i.e., generalizing the formula did not silently move the one
value already validated.

## 6.7 The witness chain, §12.1, and the defect the C clean-room exposed

The receipt (`CIS2_REF`) is one continuous SHA-256 hash object, fed in order and finalized once —
not a step-wise re-hash of `running_digest || new_data`, which would be a different and weaker
construction. The five 32-byte seed values are the three artifact hashes (weights, tokenizer,
config, each as raw bytes) followed by the two transcendental table digests (the pinned
coefficient table, then the RoPE `inv_freq` table); then every prompt token id as little-endian
`u32`; then, per decode step, the complete 49,152-entry fp32 logit vector's raw bit pattern
(`v.to_bits().to_le_bytes()` for every vocabulary entry, in index order — not just the winning
entry) followed by the chosen token id.

This exact order is itself the mechanism's one documented failure and repair. The spec's own
prose, as originally written, described the five seed items in the *reverse* group order (table
digests first, then artifact hashes) — a documentation error that did not match what the reference
binary actually computed, and was invisible until a from-spec-text clean-room implementer in a
different language (C, `verify3/`) transcribed the prose faithfully and produced every downstream
value correctly except the final witness digest, because SHA-256 output is a discontinuous
function of input order: five already-bit-identical 32-byte blocks fed in a different sequence
produce a completely unrelated hash, with no partial credit. Diagnosing this required first
proving, layer by layer, that the forward pass itself was already bit-identical between the two
implementations (ruling out every numeric candidate), which left only the receipt-assembly step
as the remaining explanation — found, confirmed against the unmodified and independently
cross-ISA/cross-compiler-validated reference binary as the source of truth, and fixed by
correcting the spec's prose (not the reference, which was already correct) and the C
implementation to match. Full detail and the CI evidence for this repair are in §4.

---

**Source map**
- FTZ/DAZ: `CIS2_SPEC_v0.2.md` §1.3; `Appendix B: E15c-verify` item 2.
- No-FMA gate: `CIS2_SPEC_v0.2.md` §1.4; `docs/E15d_v0.2_DIGESTS.md`.
- Reduction order: `CIS2_SPEC_v0.2.md` §5.1, §5.3.
- Transcendentals and accuracy characterization: `CIS2_SPEC_v0.2.md` §6.1–§6.7;
  `Appendix B: H2-result`.
- RoPE `inv_freq` generalization: `CIS2_SPEC_v0.2.md` §7.1–§7.2.
- Witness chain and its corrected order: `CIS2_SPEC_v0.2.md` §12.1;
  `docs/E15j_CLEANROOM_C_RESULT.md`; `docs/E15k_DIVERGENCE_LOCALIZATION.md`.
