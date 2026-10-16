# LLM-8b: `--stream-weights` per-layer streaming mode

Published 2026-10-16 as part of the CIS-2 archive. Phase 2 of LLM-8b (Phase 1
feasibility: `claudius-maximus` `state/reports/2026-09-18-LLM-8b-feasibility.md`).

## What changed

`cis2_ref` gains an opt-in `--stream-weights` flag. With it set, the eager
per-layer preload loop in `main()` (`for i in 0..n_layers { layers.push(...) }`,
building the whole `Vec<LayerWeights>` up front) is skipped; instead each
layer's weights are loaded from disk immediately before `forward_token`
uses them (`get_layer`/`load_layer_weights`/`StreamCtx`) and dropped when
that layer's loop iteration ends, so at most one layer's f32 weights (plus
the always-eager `embed_tokens`/`final_norm`/`lm_head`) are resident at
once.

`load_layer_weights` is the single source of truth for a layer's tensor
names/shapes/order and is called by both the eager preload path and the
`--stream-weights` path — they cannot drift apart. It reuses
`stream_widen::load_tensor_streaming` exactly as the pre-existing eager
path already did (LLM-5b, `26c752c`). No arithmetic changed: same op
order, same accumulation, only when/how memory is allocated.

Caveat (by design, not a bug): `--stream-weights` re-reads and re-widens
every layer's raw bytes from disk on every generated token (no cross-token
weight cache), so it does more disk I/O/CPU than the eager path for the
same run. This is a correctness-neutral tradeoff, not a peak-RSS or digest
problem.

## Digest match proof (SmolLM2-135M, §13.1 pinned vector)

Weights: `HuggingFaceTB/SmolLM2-135M` (local copy, `sha256` unchanged from
prior runs), prompt "Once upon a time", `gen_toks=16` (defaults).

```
$ ./target/release/cis2_ref
CIS2_REF digest=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df ...

$ ./target/release/cis2_ref --stream-weights
CIS2_REF digest=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df ...
```

Both runs' full stdout are byte-identical (`diff` empty) and both match
the pinned `docs/spec` (`cis2-spec/EXPECTED_DIGESTS.md`) §13.1 value:
`d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df`.

## Qwen2-1.5B run (LLM-8b Phase 2 main leg)

Weights: `Qwen/Qwen2-1.5B` (downloaded fresh via `curl` from
huggingface.co, no `huggingface_hub`/python dependency, into
`weights_qwen2_1_5b/`, gitignored). Pinned comparison target from
`cis2-llm/tests/kaggle/LLM4-LOG.md`/`LLM5B-LOG.md` (Kaggle CPU, `--gen-toks
8`, 2 independent runs, identical digest):

```
CIS2_REF (LLM-4/LLM-5b, Kaggle) = 9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8
```

Run started as a detached systemd user unit (`leg-llm8b-1p5b`) on box1; see
`docs/hardware_logs/llm8b_1p5b_box1_*.log` for the raw output once it
finishes. Not waited on by the agent that started it (can take up to 8h).

## H3 instrumentation: `--layer-digests` (2026-09-19)

Added `--layer-digests` to `cis2_ref` to root-cause the real fp32
forward-pass divergence between a Kaggle Qwen2-7B run (digest
`1501ed47...`) and a box1 CPU streamed run of the same weights and prompt
tokens `[12522, 5193, 264, 882]` (digest `a4a6770e...`). H1 (untied
lm_head streamed-loader bug, see `570d4c6`) and H2 (prompt token mismatch)
are both already ruled out; table_digest and inv_freq_table_digest already
match between the two runs, so the divergence is inside the transformer
forward pass itself.

The flag prints one `LAYER_DIGEST <label> <hex>` line per stage of a
single forward pass (run1/prompt 0's last prefill position only): `embed`,
`block_0`..`block_{N-1}`, `final_norm`, `logits`. Purely additive —
verified against `weights_qwen2_1_5b` that `--layer-digests` does not
change `runs_identical`, the witness digest, or the argmax digest (see
`tests/layer_digests_smoke.rs`).

Smoke-tested locally against `weights_qwen2_1_5b` (`--stream-weights
--gen-toks 0 --layer-digests`): 28 `LAYER_DIGEST block_*` lines plus
`embed`/`final_norm`/`logits`, all well-formed sha256 hex, no digest
values hardcoded anywhere (this model already matches Kaggle, so its
per-layer digests aren't useful for localizing the 7B divergence — they
only prove the flag itself works).

**Still pending (separate leg, not run by this instrumentation change):**
run `cis2_ref --layer-digests` against `weights_qwen2_7b` on box1 via
`systemd-run` (full ~5h streamed run) with the same prompt tokens, and
diff its `LAYER_DIGEST` lines against the equivalent Kaggle-side dump, to
find the first layer at which the two diverge.

## Errata 2026-10-16

The `1501ed47...` digest cited in the H3 section is retired (mis-merged Kaggle checkpoint); the EXPECTED 7B witness is `a4a6770e...`. See `ERRATA.md` E-1.
