//! LLM-5b: peak-memory regression test.
//!
//! Runs the `mem_probe` binary's `old` and `new` widening paths, each in
//! its own process (so one process's allocator/page-cache state can't
//! pollute the other's peak measurement), against the same synthetic
//! multi-tensor safetensors fixture, and checks the OLD (whole-buffer)
//! path's peak RSS against the NEW (streaming) path's peak RSS.
//!
//! Numbers actually observed on the dev box for this fixture (4 tensors x
//! 8M bf16 elems = 32M elems total, f32-equivalent model size = 128 MiB =
//! 131072 KiB):
//!   old (whole-buffer): VmHWM ~= 198792 KiB (~1.52x the f32 model size)
//!   new (streaming):    VmHWM ~= 149516 KiB (~1.14x the f32 model size)
//!   ratio old/new ~= 1.33x
//!
//! Note on the task's "old path holds >= 2x, new path holds < 1.6x"
//! expectation: the analytic peak for the old path is ~1.5x the f32
//! model size (0.5x still-held bf16 raw bytes + 1x the finished f32
//! model), not 2x -- 2x would require the bf16 raw bytes to also be
//! stored at full f32 width somewhere, which they are not. This matches
//! tests/kaggle/LLM4-LOG.md's own math (~45 GB peak vs. ~28-30 GB
//! f32-equivalent for the 7B model, i.e. ~1.5-1.6x). This test therefore
//! asserts the real, analytically-grounded thresholds -- old path >=
//! 1.35x the f32 size, new path < 1.6x the f32 size -- rather than the
//! task's illustrative "2x" figure, and asserts new < old with headroom.

use std::io::Write as _;
use std::process::Command;

const N_TENSORS: u64 = 4;
const ELEMS_PER_TENSOR: u64 = 8 * 1024 * 1024;
const F32_MODEL_SIZE_KIB: f64 = (N_TENSORS * ELEMS_PER_TENSOR * 4) as f64 / 1024.0;

fn run_probe(mode: &str, fixture: &std::path::Path) -> u64 {
    let exe = env!("CARGO_BIN_EXE_mem_probe");
    let out = Command::new(exe)
        .arg(mode)
        .arg(fixture)
        .output()
        .unwrap_or_else(|e| panic!("spawn mem_probe {mode}: {e}"));
    assert!(
        out.status.success(),
        "mem_probe {mode} failed: stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    text.trim()
        .parse()
        .unwrap_or_else(|e| panic!("mem_probe {mode} stdout {text:?} not an integer: {e}"))
}

#[test]
fn streaming_path_holds_meaningfully_less_peak_memory() {
    // Skip cleanly (rather than false-fail) if /proc/self/status VmHWM
    // isn't available -- this measurement is Linux-specific by
    // construction (per mem_probe.rs's doc comment).
    if !std::path::Path::new("/proc/self/status").exists() {
        eprintln!(
            "SKIP streaming_path_holds_meaningfully_less_peak_memory: \
             no /proc/self/status (not Linux); VmHWM peak-memory assertion \
             cannot be measured on this platform, skipping rather than \
             asserting an unverifiable number."
        );
        return;
    }

    let dir = std::env::temp_dir();
    let fixture_old = dir.join(format!("llm5b_mem_probe_old_{}.safetensors", std::process::id()));
    let fixture_new = dir.join(format!("llm5b_mem_probe_new_{}.safetensors", std::process::id()));
    // Each mode builds its own fixture file on first use (mem_probe.rs),
    // and each runs in its own process, so there is no shared state
    // between the two measurements beyond the (identical, deterministic)
    // fixture-building logic.
    let old_kib = run_probe("old", &fixture_old);
    let new_kib = run_probe("new", &fixture_new);
    let _ = std::fs::remove_file(&fixture_old);
    let _ = std::fs::remove_file(&fixture_new);
    let mut log = std::io::stderr();
    let _ = writeln!(
        log,
        "mem_probe: old={old_kib} KiB ({:.3}x f32 model), new={new_kib} KiB ({:.3}x f32 model)",
        old_kib as f64 / F32_MODEL_SIZE_KIB,
        new_kib as f64 / F32_MODEL_SIZE_KIB
    );

    assert!(
        (old_kib as f64) >= 1.35 * F32_MODEL_SIZE_KIB,
        "old (whole-buffer) path peak {old_kib} KiB is below the expected \
         double-hold floor of 1.35x the f32 model size ({F32_MODEL_SIZE_KIB} KiB); \
         either the fixture is too small for RSS granularity or the old \
         path's double-hold characterization is wrong"
    );
    assert!(
        (new_kib as f64) < 1.6 * F32_MODEL_SIZE_KIB,
        "new (streaming) path peak {new_kib} KiB exceeds 1.6x the f32 model \
         size ({F32_MODEL_SIZE_KIB} KiB); streaming widening should never \
         hold more than the f32 model plus one tensor's raw bf16 bytes"
    );
    assert!(
        new_kib < old_kib,
        "streaming path ({new_kib} KiB) did not beat whole-buffer path \
         ({old_kib} KiB) at all"
    );
}
