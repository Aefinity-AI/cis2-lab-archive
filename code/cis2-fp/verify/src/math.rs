//! Clean-room scalar fp32 kernel primitives for cis2-verify.
//!
//! Built strictly from the E14a design memo §3 (reduction order, no-FMA,
//! transcendental route, denormal handling, bf16 widening). No cis2-fp
//! src/ was consulted. See ../SPEC_GAPS.md for open ambiguities this
//! implementation had to resolve by independent choice.

/// §3.1 (a): strict left-to-right sequential sum. No FMA (§3.2): every
/// term is a plain `a + b`, never `.mul_add`.
pub fn sum_seq(xs: &[f32]) -> f32 {
    let mut acc = 0.0f32;
    for i in 0..xs.len() {
        acc = acc + xs[i];
    }
    acc
}

/// §3.1 (a): strict left-to-right sequential dot product. `a*b + acc` is
/// written as two separate ops (never `.mul_add`) so LLVM cannot contract
/// it into an FMA (§3.2, §2's compiler-flags row).
pub fn dot_seq(a: &[f32], b: &[f32]) -> f32 {
    debug_assert_eq!(a.len(), b.len());
    let mut acc = 0.0f32;
    for i in 0..a.len() {
        let term = a[i] * b[i];
        acc = acc + term;
    }
    acc
}

/// §3.3, RMSNorm's "cheap win": rsqrt via two mandatory-correctly-rounded
/// IEEE-754 ops (sqrt, then divide) — route (a), no pinned table needed.
pub fn rsqrt(x: f32) -> f32 {
    1.0f32 / x.sqrt()
}

/// §3.5: bf16 -> fp32 exact widening via zero-extending bit-shift. No
/// rounding, no library call.
pub fn widen_bf16(bits: u16) -> f32 {
    f32::from_bits((bits as u32) << 16)
}

/// Transcendental route actually used by this clean-room implementation:
/// route (a) as the memo recommends (§3.3), but using the host's std/libm
/// `exp`/`sin`/`cos` as the best available approximation of a
/// correctly-rounded implementation, since (matching E15b's own finding)
/// no CORE-MATH/RLIBM Rust crate was available to this sandbox either.
/// This is NOT guaranteed correctly-rounded (glibc libm is only
/// "faithfully rounded", <=1 ULP, not proven exact-to-nearest on every
/// input) — see SPEC_GAPS.md item 2. No fast-math flags are in effect
/// (Rust has none), so this is at least a deterministic, non-fused call.
pub fn exp_route_a(x: f32) -> f32 {
    x.exp()
}
pub fn sin_route_a(x: f32) -> f32 {
    x.sin()
}
pub fn cos_route_a(x: f32) -> f32 {
    x.cos()
}

/// SiLU: x * sigmoid(x) = x / (1 + exp(-x)). Written with the pinned
/// exp route and ordinary (non-FMA) arithmetic.
pub fn silu(x: f32) -> f32 {
    let denom = 1.0f32 + exp_route_a(-x);
    x / denom
}

/// Sequential max-scan (§2's softmax row: "safe if implemented as a
/// strict sequential ... max, matching the reduction-order fix").
pub fn max_seq(xs: &[f32]) -> f32 {
    let mut m = xs[0];
    for i in 1..xs.len() {
        if xs[i] > m {
            m = xs[i];
        }
    }
    m
}

/// argmax with first-index tie-break (strict `>`, not `>=`).
pub fn argmax(xs: &[f32]) -> usize {
    let mut best_i = 0usize;
    let mut best_v = xs[0];
    for i in 1..xs.len() {
        if xs[i] > best_v {
            best_v = xs[i];
            best_i = i;
        }
    }
    best_i
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dot_seq_is_order_sensitive_by_design() {
        // [1e8, 1, -1e8] . [1,1,1] is exactly 0.0 only under strict
        // left-to-right fp32 accumulation; a tree/pairwise reduction
        // gives a different (nonzero) rounded answer. Independent
        // regression check, same shape as the memo's own §3.1
        // justification for route (a).
        let a = [1.0e8f32, 1.0, -1.0e8];
        let b = [1.0f32, 1.0, 1.0];
        assert_eq!(dot_seq(&a, &b), 0.0);
    }

    #[test]
    fn widen_bf16_exact() {
        assert_eq!(widen_bf16(0x3F80), 1.0f32); // bf16 1.0
        assert_eq!(widen_bf16(0x0000), 0.0f32);
        assert_eq!(widen_bf16(0x8000), -0.0f32);
    }
}
