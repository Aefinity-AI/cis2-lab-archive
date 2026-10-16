//! LLM-5b: the OLD widening path, kept only as a reference for tests and
//! the `mem_probe` peak-memory comparison binary (see
//! `docs/LLM5b_STREAMING_WIDEN.md`). Not used by `main.rs`'s production
//! load path any more (that now goes through `stream_widen`), but kept
//! byte-for-byte identical to what `main.rs` used to do so the bit-exact
//! and memory tests are comparing against the real old behavior, not a
//! reconstruction of it.
//!
//! This is exactly the pre-LLM-5b `load_f32_tensor` from `main.rs`,
//! unmodified: it requires the WHOLE safetensors file already in one
//! buffer (`st: &safetensors::SafeTensors`, built from a `Vec<u8>` the
//! caller reads and keeps alive), which is the double-hold LLM-5b fixes.

use crate::math::widen_bf16;

pub fn load_f32_tensor_whole_buffer(
    st: &safetensors::SafeTensors,
    name: &str,
    expect_shape: &[usize],
) -> Vec<f32> {
    let view = st
        .tensor(name)
        .unwrap_or_else(|e| panic!("tensor {name} missing: {e}"));
    assert_eq!(view.shape(), expect_shape, "tensor {name} shape mismatch");
    assert_eq!(
        view.dtype(),
        safetensors::Dtype::BF16,
        "tensor {name} dtype {:?} is not BF16; CIS-2 pins bf16-on-disk weights (\u{00a7}3.5)",
        view.dtype()
    );
    let raw = view.data();
    assert_eq!(raw.len() % 2, 0, "bf16 tensor {name} has odd byte length");
    let n = raw.len() / 2;
    let mut out = vec![0.0f32; n];
    for i in 0..n {
        let lo = raw[2 * i];
        let hi = raw[2 * i + 1];
        let bits = u16::from_le_bytes([lo, hi]);
        out[i] = widen_bf16(bits);
    }
    out
}
