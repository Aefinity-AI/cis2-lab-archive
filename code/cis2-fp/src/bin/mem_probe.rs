//! LLM-5b: peak-memory comparison of the OLD whole-buffer widening path
//! vs. the NEW streaming widening path.
//!
//! Builds a synthetic multi-tensor safetensors file on disk (several
//! ~16 MiB BF16 tensors, chosen small enough to be safe in a
//! memory-constrained dev environment while still being big enough that
//! process RSS is dominated by the tensors, not process/runtime
//! overhead), then either:
//!   - `old`: reads the whole file into one Vec<u8>, builds a
//!     safetensors::SafeTensors view over it, and widens every tensor to
//!     f32 while keeping the whole raw buffer alive throughout (this is
//!     the pre-LLM-5b main.rs behavior, reproduced via
//!     `whole_buffer_widen::load_f32_tensor_whole_buffer`), or
//!   - `new`: streams the header only, then widens each tensor via one
//!     seek+read_exact per tensor (`stream_widen::load_tensor_streaming`),
//!     never holding the whole file at once.
//! and reports this process's peak RSS (`VmHWM` from /proc/self/status,
//! Linux-specific, kernel-tracked high-water mark — not a self-measured
//! sample, so it can't miss a transient peak between polls) in KiB on
//! stdout as a single integer, so a test can spawn this binary twice (one
//! process per path, so the two measurements can't share/pollute a peak)
//! and compare.
//!
//! Not part of the normative decode path.

#[path = "../denormal.rs"]
mod denormal;
#[path = "../math.rs"]
mod math;
#[path = "../stream_widen.rs"]
mod stream_widen;
#[path = "../whole_buffer_widen.rs"]
mod whole_buffer_widen;

use std::fs::File;
use std::io::Write;

const N_TENSORS: usize = 4;
const ELEMS_PER_TENSOR: usize = 8 * 1024 * 1024; // 8M bf16 elems = 16 MiB/tensor raw

fn tensor_name(i: usize) -> String {
    format!("model.layers.{i}.weight")
}

fn build_fixture_file(path: &std::path::Path) {
    let mut tensor_views: Vec<(String, safetensors::tensor::TensorView)> = Vec::new();
    let mut byte_bufs: Vec<Vec<u8>> = Vec::new();
    for t in 0..N_TENSORS {
        let mut bytes = Vec::with_capacity(ELEMS_PER_TENSOR * 2);
        for i in 0..ELEMS_PER_TENSOR {
            let bits: u16 = 0x3F80u16.wrapping_add(((t * ELEMS_PER_TENSOR + i) as u16) & 0x7F);
            bytes.extend_from_slice(&bits.to_le_bytes());
        }
        byte_bufs.push(bytes);
    }
    for t in 0..N_TENSORS {
        let view = safetensors::tensor::TensorView::new(
            safetensors::Dtype::BF16,
            vec![ELEMS_PER_TENSOR],
            &byte_bufs[t],
        )
        .unwrap();
        tensor_views.push((tensor_name(t), view));
    }
    let buf =
        safetensors::tensor::serialize(tensor_views.iter().map(|(n, v)| (n.clone(), v)), None)
            .expect("serialize mem_probe fixture");
    let mut f = File::create(path).expect("create fixture file");
    f.write_all(&buf).expect("write fixture file");
}

fn vm_hwm_kib() -> u64 {
    let status = std::fs::read_to_string("/proc/self/status").expect("read /proc/self/status");
    for line in status.lines() {
        if let Some(rest) = line.strip_prefix("VmHWM:") {
            let digits: String = rest.chars().filter(|c| c.is_ascii_digit()).collect();
            return digits.parse().expect("parse VmHWM value");
        }
    }
    panic!("VmHWM not found in /proc/self/status (not Linux, or field missing)");
}

fn run_old(path: &std::path::Path) {
    let raw = std::fs::read(path).expect("read fixture (old path: whole file into one Vec<u8>)");
    let st = safetensors::SafeTensors::deserialize(&raw).expect("parse safetensors");
    let mut held: Vec<Vec<f32>> = Vec::new();
    for t in 0..N_TENSORS {
        let name = tensor_name(t);
        let out = whole_buffer_widen::load_f32_tensor_whole_buffer(&st, &name, &[ELEMS_PER_TENSOR]);
        held.push(out);
    }
    drop(st);
    drop(raw);
    std::hint::black_box(&held);
}

fn run_new(path: &std::path::Path) {
    let mut file = File::open(path).expect("open fixture");
    let (index, data_start) = stream_widen::read_index(&mut file);
    let mut held: Vec<Vec<f32>> = Vec::new();
    for t in 0..N_TENSORS {
        let name = tensor_name(t);
        let out = stream_widen::load_tensor_streaming(
            &mut file,
            data_start,
            &index,
            &name,
            &[ELEMS_PER_TENSOR],
        );
        held.push(out);
    }
    drop(file);
    std::hint::black_box(&held);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    assert_eq!(
        args.len(),
        3,
        "usage: mem_probe <old|new> <fixture-path>"
    );
    let mode = &args[1];
    let path = std::path::Path::new(&args[2]);
    if !path.exists() {
        build_fixture_file(path);
    }
    match mode.as_str() {
        "old" => run_old(path),
        "new" => run_new(path),
        other => panic!("unknown mode {other}, expected old or new"),
    }
    println!("{}", vm_hwm_kib());
    let _ = std::io::stdout().flush();
}
