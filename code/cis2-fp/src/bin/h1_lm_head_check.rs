//! cis3-0 / H1: dumps sha256 of the fp32-widened `lm_head.weight` tensor
//! as produced by the production streamed loader (`stream_widen::
//! load_tensor_streaming`), for the real Qwen2-7B merged safetensors file
//! (untied lm_head, tie_word_embeddings=false).
//!
//! This is a targeted, RAM-safe re-run of exactly the tensor read that
//! `main.rs` line ~901 performs (`load_f32_tensor("lm_head.weight",
//! &[vocab, hidden])`), isolated from the rest of the model load so it
//! can be cross-checked against an independent widening (see
//! `scripts/h1_independent_lm_head.py`, which memmaps the same byte range
//! and widens bf16->f32 via a numpy left-shift, not via any cis2_ref
//! code) without ever holding the whole ~14.5 GiB file in RAM.
//!
//! Usage: h1_lm_head_check <path-to-model.safetensors> [tensor-name]
//! Prints: "<tensor-name> shape=<..> n_elems=<..> sha256=<hex>"

#[path = "../denormal.rs"]
mod denormal;
#[path = "../math.rs"]
mod math;
#[path = "../stream_widen.rs"]
mod stream_widen;
#[path = "../whole_buffer_widen.rs"]
mod whole_buffer_widen;

use sha2::{Digest, Sha256};
use std::fs::File;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    assert!(
        args.len() >= 2,
        "usage: h1_lm_head_check <path-to-model.safetensors> [tensor-name]"
    );
    let path = &args[1];
    let name = args.get(2).map(String::as_str).unwrap_or("lm_head.weight");

    let mut file = File::open(path).unwrap_or_else(|e| panic!("open {path}: {e}"));
    let (index, data_start) = stream_widen::read_index(&mut file);
    let entry = index
        .get(name)
        .unwrap_or_else(|| panic!("tensor {name} not found in {path}"));
    let shape = entry.shape.clone();

    eprintln!(
        "found {name}: dtype={} shape={:?} data_offsets={:?}",
        entry.dtype, shape, entry.data_offsets
    );

    let out = stream_widen::load_tensor_streaming(&mut file, data_start, &index, name, &shape);

    let mut hasher = Sha256::new();
    for f in &out {
        hasher.update(f.to_le_bytes());
    }
    let digest = hasher.finalize();
    let hex: String = digest.iter().map(|b| format!("{b:02x}")).collect();

    println!(
        "{name} shape={:?} n_elems={} sha256={hex}",
        shape,
        out.len()
    );
}
