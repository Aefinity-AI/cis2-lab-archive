//! cis3-1b (H3 instrumentation): smoke test for `--layer-digests`.
//!
//! This only asserts the flag doesn't crash and emits the expected labeled
//! `LAYER_DIGEST` lines (embed, one per transformer block, final_norm,
//! logits) -- it does NOT hardcode any expected digest value, since the
//! whole point of this flag is to locate an as-yet-unexplained divergence
//! (see docs/LLM8b_STREAM_WEIGHTS.md); a hardcoded digest here would either
//! be meaningless (small model, not the one that diverges) or would bake in
//! a value we haven't independently verified against an oracle.
//!
//! Runs against `weights_qwen2_1_5b/`, the known-good model whose streamed
//! and non-streamed digests already match (this test uses `--stream-weights`
//! to keep peak RSS low). That weights directory is gitignored (checked out
//! locally by earlier LLM-8b legs, not committed -- see .gitignore), so this
//! test skips cleanly rather than failing when it is absent.

use std::path::Path;
use std::process::Command;

#[test]
fn layer_digests_flag_runs_and_labels_every_layer() {
    let weights_dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("weights_qwen2_1_5b");
    if !weights_dir.join("model.safetensors").exists() {
        eprintln!(
            "SKIP layer_digests_flag_runs_and_labels_every_layer: \
             weights_qwen2_1_5b/model.safetensors not present locally \
             (gitignored, not checked into the repo); nothing to run against."
        );
        return;
    }

    let exe = env!("CARGO_BIN_EXE_cis2_ref");
    let out = Command::new(exe)
        .args([
            "--weights-dir",
            "weights_qwen2_1_5b",
            "--gen-toks",
            "0",
            "--layer-digests",
            "--stream-weights",
        ])
        .output()
        .unwrap_or_else(|e| panic!("spawn cis2_ref --layer-digests: {e}"));
    assert!(
        out.status.success(),
        "cis2_ref --layer-digests exited non-zero: stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );

    let stdout = String::from_utf8_lossy(&out.stdout);
    let lines: Vec<&str> = stdout
        .lines()
        .filter(|l| l.starts_with("LAYER_DIGEST "))
        .collect();

    // 1 embed + N blocks (Qwen2-1.5B has 28) + final_norm + logits.
    let n_layers = 28;
    assert_eq!(
        lines.len(),
        n_layers + 3,
        "expected 1 embed + {n_layers} block + final_norm + logits LAYER_DIGEST \
         lines, got {}: {lines:?}",
        lines.len()
    );

    let is_hex64 = |s: &str| s.len() == 64 && s.chars().all(|c| c.is_ascii_hexdigit());

    assert!(
        lines[0].starts_with("LAYER_DIGEST embed ") && is_hex64(lines[0].split(' ').nth(2).unwrap()),
        "first LAYER_DIGEST line should be the embed digest, got {:?}",
        lines[0]
    );
    for li in 0..n_layers {
        let label = format!("LAYER_DIGEST block_{li} ");
        let line = lines[li + 1];
        assert!(
            line.starts_with(&label) && is_hex64(line.split(' ').nth(2).unwrap()),
            "expected {label:?} at position {}, got {line:?}",
            li + 1
        );
    }
    let final_norm = lines[n_layers + 1];
    assert!(
        final_norm.starts_with("LAYER_DIGEST final_norm ")
            && is_hex64(final_norm.split(' ').nth(2).unwrap()),
        "expected final_norm digest, got {final_norm:?}"
    );
    let logits = lines[n_layers + 2];
    assert!(
        logits.starts_with("LAYER_DIGEST logits ") && is_hex64(logits.split(' ').nth(2).unwrap()),
        "expected logits digest, got {logits:?}"
    );

    // Additive-only: the existing witness/argmax digest lines must still be
    // present and both runs must still agree (--layer-digests must not
    // perturb the normative CIS2_REF output at all).
    assert!(
        stdout.contains("runs_identical=true"),
        "existing runs_identical output missing or false with --layer-digests set: {stdout}"
    );
}
