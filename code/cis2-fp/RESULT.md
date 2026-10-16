> **SUPERSEDED 2026-10-16 (ERRATA.md E-1):** the "Kaggle-pinned target" `1501ed47...` below is the digest of a mis-merged checkpoint and is retired. Current EXPECTED = `a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3` (box1 value, reproduced bit-identically on Kaggle cis3-0n). History below is unedited.

# LLM-8b-7B digest result — box1 CPU streamed Qwen2-7B — 2026-09-18

- Host: aefinity-box (box1), CPU-only, streamed bf16->fp32 widening, MemoryMax=4600M+swap.
- Weights: merged `weights_qwen2_7b/model.safetensors`, size 15231272088, sha256
  `13200c88e7482d83ed9a2bb23a01b515e46663ab57dba853389587d4173dcfa3` (independently
  recomputed, matches all 4 shard-level pinned sha256 values; merge is NOT corrupt).
- Run: `cis2_ref`, prompt_toks=4, gen_toks=4, dtype=fp32, reduction_mode=sequential.
- Two runs on this box (run1, run2): **identical** — same token ids, same witness
  digest, same argmax digest. `runs_identical=true`. Box1 is internally deterministic.

  `CIS2_REF digest = a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3`

- Kaggle-pinned target (LLM-5b/LLM-5c, same recipe: prompt_toks=4 gen_toks=4 fp32
  sequential):

  `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a`

- **MISMATCH.** Box1's digest does not equal the Kaggle-pinned 7B digest, despite
  matching config (same prompt/gen token counts, same dtype, same reduction mode)
  and a verified-correct, uncorrupted weights file.

## Table digests match, output digests do not

Compared against `state/reports/2026-09-18-LLM-5c-7b-second-run.md` (Kaggle,
**CPU-only** kernel, `enable_gpu: false`) for the same 7B config:

| field | box1 (this run) | Kaggle (LLM-5c v2) | match? |
|---|---|---|---|
| table_digest | `23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d` | `23c7bfaf...` | YES |
| inv_freq_table_digest | `02908dae2c15329014dd986fec8033e03427fba0935b04b864ab2bc75fe3bc44` | `02908dae...` | YES |
| witness digest | `a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3` | `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a` | **NO** |
| argmax digest | `a8ed47fb9cca7b6ac1830fc12a18ebb9615b77e29b012f8c036ce7cb0183c265` | `67f771c5...` | **NO** |

Table/inv_freq digests match exactly — the fixed lookup tables (precomputed
constants baked from config, independent of the actual forward pass) are
identical, so weight-loading/config parsing agree. The witness AND argmax
digests both diverge, meaning the generated token ids or their logits
actually differ, not just an unrelated metadata field. Since Kaggle's 7B run
was **also CPU-only** (not GPU), this is a CPU-vs-CPU cross-machine
divergence specific to the 7B scale (1.5B matched bit-for-bit on the same
box1/Kaggle pair via LLM-8b). This directly contradicts the bit-identical-
across-platforms thesis at 7B and needs root-causing before any public claim
about 7B (or scale-independent) cross-platform identity.

## What this does NOT mean yet

This is the first cross-platform (CPU box1 vs Kaggle GPU/CPU kernel) attempt at the
Qwen2-7B digest, following a successful 1.5B cross-platform MATCH (LLM-8b, digest
9a463f44...) on the same box, same harness, same streaming code path. The 1.5B
success means the streaming/widening code is not obviously broken in general — the
mismatch is specific to 7B, or specific to whatever differs between the two runs
beyond the parameters logged here (e.g. Kaggle CPU vs Kaggle GPU kernel identity,
library/BLAS version, a numeric edge case that only appears at 7B scale).

Per QUEUE.md line 363 hard rule: **never rewrite EXPECTED.** This is filed as a
MISMATCH, not resolved, not root-caused. No claim of a fixed cross-ISA/cross-platform
bit-identical 7B digest may be made until this is root-caused.

## Next steps (not done this tick — budget)

1. Confirm exactly which of the two Kaggle 7B runs (LLM-5b provisional 29.42GB run,
   or LLM-5c second-run MATCH, both reporting 1501ed47...) used identical prompt
   token ids `[12522, 5193, 264, 882]` to box1's run — a prompt/tokenization mismatch
   would fully explain a digest divergence without any numerical bug.
2. If prompts match, this is a real box1-vs-Kaggle numerical divergence at 7B scale
   worth root-causing (candidate causes: different widening order, different BLAS/
   reduction associativity at larger matrix sizes, a bug specific to the 7B config
   e.g. GQA head count math) — do not speculate further without checking Kaggle's
   raw log for the actual prompt tokens used.

## cis3-0: H1 (untied lm_head streamed-loader bug) — RULED OUT, 2026-09-19

Hypothesis: Qwen2-7B has `tie_word_embeddings=false` (separate `lm_head.weight`
tensor), unlike Qwen2-1.5B (`tie_word_embeddings=true`, which reuses
`embed_tokens.weight` and matched Kaggle). Candidate bug: the streamed loader
(`stream_widen.rs`) might mis-load or mis-widen the untied `lm_head.weight`
tensor (wrong name, wrong dtype cast, byte-order bug, or silently falling back
to `embed_tokens.weight`) in a way that only shows up when
`tie_word_embeddings=false`.

Test: two independently-implemented reads of `lm_head.weight` from the actual
verified-uncorrupted merged `weights_qwen2_7b/model.safetensors`
(`sha256=13200c88...`, tensor `lm_head.weight` dtype=BF16 shape=[152064, 3584],
data_offsets=(11674848256, 12764843008)), both computing sha256 of the
resulting fp32 tensor's little-endian bytes in ascending element order:

1. **Production path**: `src/bin/h1_lm_head_check.rs`, a thin wrapper that
   calls the exact same `stream_widen::read_index` +
   `stream_widen::load_tensor_streaming("lm_head.weight", ...)` that
   `main.rs` line ~901 calls in both eager and `--stream-weights` modes (both
   modes use this one code path for `lm_head`/`embed_tokens`/`model.norm` —
   confirmed by diffing `main.rs`/`stream_widen.rs` between the Kaggle-pinned
   commit `26c752c` (cis2-fp PR #12, used for the LLM-5b/LLM-5c Kaggle 7B
   digest) and box1's run commit `bddac51`: `--stream-weights` (added later,
   PR for LLM-8b) only changes *when* per-layer tensors are loaded, never how
   `lm_head.weight` itself is read/widened — that code is byte-identical
   across both commits).
   Result: `sha256=fdb54cb6f089fe433bcc948cece87579d5bd36b14b9d53dffcf298918be79034`
2. **Independent path**: `scripts/h1_independent_lm_head.py`, zero shared code
   with cis2_ref — manually parses the safetensors header, `numpy.memmap`s
   only the tensor's byte range (never loads the 14.5 GiB file), widens
   bf16→fp32 via `uint16 << 16` reinterpreted as float32 bits (textbook exact
   widen, independently implemented, not calling `widen_bf16`), hashes the
   resulting float32 array's little-endian bytes.
   Result: `sha256=fdb54cb6f089fe433bcc948cece87579d5bd36b14b9d53dffcf298918be79034`

**MATCH.** The two independently-implemented reads of the real `lm_head.weight`
tensor produce the bit-identical fp32 tensor and sha256. H1 is **ruled out**:
the streamed loader correctly identifies, reads, and widens the untied
`lm_head.weight` tensor for Qwen2-7B; there is no lm_head-loading bug, no
name/dtype/byte-order bug, and no silent fallback to `embed_tokens.weight`.
(Also structurally: `main.rs` never had a *second*, divergent "whole-buffer"
lm_head-loading implementation to compare against in the first place — the
pre-LLM-5b whole-buffer path, kept only as `whole_buffer_widen.rs` for tests,
already uses the same `widen_bf16` math and is proven byte-identical to
`stream_widen` on a synthetic fixture by the existing
`stream_widen::tests::streaming_matches_whole_buffer_bit_for_bit` unit test —
H1's premise that the two loaders might disagree does not apply to lm_head
specifically, since lm_head has only ever gone through this one loader.)

**Next hypothesis to try (H2, per QUEUE.md cis3-0 brief order):** verify
Kaggle's raw log used the identical prompt token ids `[12522, 5193, 264, 882]`
as box1's run — a tokenization/prompt mismatch would fully explain a digest
divergence with no numerical bug anywhere. If H2 also clears, move to H3
(`--layer-digests` + systemd-run streamed 7B to find the first diverging
layer) per QUEUE.md line 18 (cis3-0k, Kaggle side).

Artifacts (this commit): `src/bin/h1_lm_head_check.rs`,
`scripts/h1_independent_lm_head.py`. Both run against the real, on-disk,
sha256-verified 7B weights (no re-download), RAM-safe (peak RSS ~3.2 GiB for
the Rust check; the Python check never materializes more than the tensor's
own byte range).
