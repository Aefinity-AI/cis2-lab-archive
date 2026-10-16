#!/bin/bash
# gpu/kaggle/make_dataset.sh — pack the E18b/E18c CUDA-portable port +
# weights + pre-computed CPU-side expected values (BOTH the spec-normative
# sequential v0.3b path AND the v0.4 CANDIDATE tree path) into a Kaggle
# dataset directory, and push it with `kaggle datasets create` (first
# time) or `kaggle datasets version` (dataset already exists).
#
# This step needs no GPU and no CUDA toolchain — it is plain file staging
# plus an upload, safe to run on this box. It does NOT push the GPU kernel
# (see push.sh — that step is gated on GPU quota and is not run by this
# script).
#
# Usage: gpu/kaggle/make_dataset.sh [--dry-run]
#   --dry-run   stage the directory and print the kaggle command, but do
#               not actually invoke kaggle.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GPU="$(dirname "$HERE")"
ROOT="$(dirname "$GPU")"
STAGE="$HERE/dataset_staging"
KAGGLE_BIN="${KAGGLE_BIN:-$HOME/.local/bin/kaggle}"
DATASET_SLUG="aefinityaiinc/cis2-e18b-gpu"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

echo "== staging into $STAGE =="
rm -rf "$STAGE"
mkdir -p "$STAGE/gpu" "$STAGE/weights" "$STAGE/gate"

# ---- 1. gpu/ sources: everything the host/host-gcc/host-tree/cuda/
# cuda-tree Makefile targets need to build cis2_host.cpp. The tree
# reduction (v0.4 CANDIDATE) lives behind -DCIS2_REDUCTION_TREE entirely
# inside cis2_math.h and cis2_host.cpp (verified: `grep -n
# CIS2_REDUCTION_TREE gpu/*.h gpu/*.cpp` — no other file references the
# macro), so no new source file is needed for the tree build; the same
# six files this loop already copied for E18b cover both modes.
# Copying the Makefile itself (not just its flags) means the kernel
# builds with the SAME recipe this box verified — no flag transcription,
# no drift between what was gated here and what runs on Kaggle.
for f in Makefile cis2_host.cpp cis2_model.h cis2_math.h cis2_fpenv.h \
         cis2_sha256.h cis2_consts.inc cis2_sass_probe.cu; do
  cp -L "$GPU/$f" "$STAGE/gpu/$f"
done

# ---- 2. weights/: config.json, model.safetensors, tokenizer.json.
# -L dereferences the symlinks this worktree's weights/ holds so the
# dataset carries real files, not broken links.
for f in config.json model.safetensors tokenizer.json; do
  cp -L "$ROOT/weights/$f" "$STAGE/weights/$f"
done

# ---- 3. token id files, both modes, from the host gates already run in
# this worktree (gpu/.gate/, gitignored — generated, not source-controlled).
# Sequential ids come from `make -C gpu gate`/`gate-128`; tree ids from
# `make -C gpu gate-tree`/`gate-tree-128`. The prompt and token counts are
# identical across modes (same --dump-ids flag, same weights, same
# prompt) — --reduction only changes the reduction ORDER used to compute
# logits from a given prefix, never which token id is fed in — but the
# tree run's ids file is staged separately anyway so nothing here assumes
# that invariant rather than just shipping what each gate produced.
GATE_SRC="$GPU/.gate"
for f in ids.txt ids128.txt cpp.trace ids_tree.txt ids128_tree.txt cpp_tree.trace; do
  if [ ! -f "$GATE_SRC/$f" ]; then
    echo "FATAL: $GATE_SRC/$f missing." >&2
    echo "Run 'make -C gpu gate gate-128 gate-tree gate-tree-128' first." >&2
    exit 1
  fi
done
cp -L "$GATE_SRC/ids.txt"        "$STAGE/gate/ids_16tok.txt"
cp -L "$GATE_SRC/ids128.txt"     "$STAGE/gate/ids_128tok.txt"
cp -L "$GATE_SRC/ids_tree.txt"   "$STAGE/gate/ids_16tok_tree.txt"
cp -L "$GATE_SRC/ids128_tree.txt" "$STAGE/gate/ids_128tok_tree.txt"

# ---- 4. CPU trace + expected-digest files, both modes.
# The 16-token traces are the HOST C++ BUILD's own traces
# (gpu/.gate/cpp.trace, cpp_tree.trace), not the Rust ones — `gate`/
# `gate-tree` already proved the two are byte-identical in each mode, so
# using the C++ trace as the GPU comparison target isolates
# host-vs-device execution differences from host-language (Rust-vs-C++)
# differences, which are already a closed question in both modes.
cp -L "$GATE_SRC/cpp.trace"      "$STAGE/gate/host_cpu_trace_16tok.txt"
cp -L "$GATE_SRC/cpp_tree.trace" "$STAGE/gate/host_cpu_trace_16tok_tree.txt"

cat > "$STAGE/gate/expected_digests.json" <<'EOF'
{
  "sequential": {
    "16": {
      "digest": "d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df",
      "prompt_toks": 4,
      "gen_toks": 16,
      "trace_file": "host_cpu_trace_16tok.txt",
      "note": "spec-NORMATIVE v0.3b sequential reduction order. Value pinned by docs/E15m_RESULT.md; matches Rust reference, verify2 (Rust), verify3 (C11), and this repo's own host C++ build (clang++ and g++). This is the digest that governs the leg's exit status."
    },
    "128": {
      "digest": "22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6",
      "prompt_toks": 4,
      "gen_toks": 128,
      "trace_file": null,
      "note": "no trace comparison at 128 tokens (the 16-token trace already localises any divergence); digest equality only."
    }
  },
  "tree": {
    "16": {
      "digest": "3f3b1ffceca02e8e0e78d5c653963480ea988ef41a378acc5393006ad378e1b3",
      "prompt_toks": 4,
      "gen_toks": 16,
      "trace_file": "host_cpu_trace_16tok_tree.txt",
      "note": "v0.4 CANDIDATE pinned blocked-tree reduction order (docs/design/CIS2_V04_TREE_REDUCTION.md), --reduction tree / -DCIS2_REDUCTION_TREE. Deliberately NOT equal to the sequential digest (non-associative fp32 addition, different rounding by design). Reported as CANDIDATE PASS/FAIL; never governs the leg's exit status."
    },
    "128": {
      "digest": "112661fbfcb11440ae7d27c43e45135f8a6ff9f6bc01189d756c76dac96a0fdf",
      "prompt_toks": 4,
      "gen_toks": 128,
      "trace_file": null,
      "note": "tree mode, 128 tokens, digest equality only, CANDIDATE — see 16-token note."
    }
  }
}
EOF

cat > "$STAGE/dataset-metadata.json" <<EOF
{
  "title": "cis2-e18b-gpu",
  "id": "$DATASET_SLUG",
  "licenses": [{"name": "unknown"}]
}
EOF

echo "== staged files =="
find "$STAGE" -type f -printf '%10s  %P\n' | sort -k2

SIZE=$(du -sh "$STAGE" | cut -f1)
echo "== total staged size: $SIZE =="

if $KAGGLE_BIN datasets list --mine 2>/dev/null | grep -q "^$DATASET_SLUG "; then
  CMD=("$KAGGLE_BIN" datasets version -p "$STAGE" -m "E18c GPU leg: both kernels (sequential + tree), rebuild $(date -Is)" --dir-mode zip)
else
  CMD=("$KAGGLE_BIN" datasets create -p "$STAGE" --dir-mode zip)
fi

echo "== command =="
printf '%q ' "${CMD[@]}"; echo

if [ "$DRY_RUN" = "1" ]; then
  echo "(--dry-run: not invoking kaggle)"
  exit 0
fi

"${CMD[@]}"
echo "== done: https://www.kaggle.com/datasets/$DATASET_SLUG =="
