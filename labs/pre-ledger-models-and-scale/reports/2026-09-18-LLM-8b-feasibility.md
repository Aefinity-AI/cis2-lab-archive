# LLM-8b Phase 1 feasibility: streamed-weights 1.5B digest on box1

Read-only investigation. No weights downloaded, no code written.

## Repo scope correction (important)
`Aefinity-AI/cis2-llm`'s vendored binary (`verifier/vendor/cis2-verify2`,
`server/app/runner.py`) only ever computes the **pinned §13.1 SmolLM2-135M
reference vector** — it takes no CLI args and has no 1.5B/7B path. The
actual multi-model runner used for LLM-4/LLM-5b (Qwen2-1.5B, Qwen2-7B) is
`~/projects/cis2-fp`'s `src/bin`/`src/main.rs` (`cis2_ref` binary, private
repo, separate from cis2-llm). LLM-8/LLM-8b's premise ("clone cis2-llm,
read its README for the 1.5B recipe") was slightly wrong — the recipe
lives in cis2-fp + `cis2-llm/tests/kaggle/LLM4-LOG.md` /
`LLM5B-LOG.md`. Phase 2 work would target cis2-fp, not cis2-llm.

## (a) How weights are currently loaded
As of `cis2-fp` commit `26c752c` ("cis2_ref: streaming widening (LLM-5b)",
already merged history, not a live branch — reachable via
`git show 26c752c`): tensors are streamed **per-tensor** off disk
(`stream_widen.rs`: parse safetensors header once, then per tensor
seek+read_exact its raw bf16 byte range, widen bf16->fp32 with the exact
§3.5 bit-shift, drop the raw buffer) — this already replaced the old
whole-file-into-one-`Vec<u8>` load (kept as `whole_buffer_widen.rs` for
tests only). **But** `main.rs`'s load loop (lines ~698-758 of that
revision) still calls this streaming loader for *every* tensor of *every*
layer up front, building one `Vec<LayerWeights>` for **all** `n_layers`
before the forward pass starts, plus a fully-materialized `embed_tokens`
f32 table. So current state: no double-buffering (LLM-5b fixed that), but
still whole-model-in-RAM for the compute step — streaming so far only
attacks the *load-time* peak (raw bf16 file + f32 model both resident),
not the *forward-pass* peak (all-layers f32 model resident).

## (b) Estimated peak RSS, 1.5B (Qwen2-1.5B: hidden=1536,
intermediate=8960, layers=28, heads=12, kv_heads=2, head_dim=128,
vocab=151936, tie_word_embeddings=true)
- `embed_tokens` f32: 151936*1536*4 = ~933 MB (materialized whole, even
  though only one row/position is read — current code has no partial
  read for this tensor).
- Per layer f32 (q/k/v/o/gate/up/down proj + 2 layernorms): q_proj
  1536*1536*4=9.4MB, k/v_proj (2*128)*1536*4=1.6MB each, o_proj 9.4MB,
  gate/up/down_proj 8960*1536*4=55MB each (x3=165MB) -> ~187MB/layer.
- 28 layers * 187MB = ~5.24 GB.
- Total: ~933MB + 5.24GB = **~6.17 GB**, matching the ~6.2 GB fp32
  1.5B-weights figure already cited in `state/BLOCKERS.md` (LLM-8 gate
  failure note) and consistent with `PROGRAMME.md`'s stated on-prem
  fp32-exact ceiling of ~2B params on this fleet. This is a from-scratch
  arithmetic estimate from config dims + dtype, not a measured `time -v`
  number (no measurement was run per task scope).

## (c) Sequential-vs-not verdict: **strictly layer-sequential, confirmed
by reading the forward pass**
`main.rs` decode step (`for (li, layer) in model.layers.iter().enumerate()`,
~line 263) touches exactly one `LayerWeights` struct per loop iteration;
nothing crosses layers except: the running hidden-state vector `h`
(size=hidden, tiny) and each layer's own `KvCache` entry (`caches[li]`,
bounded by hidden*n_kv_heads*head_dim*gen_toks, tiny at 16 tokens). No
layer's weights are read from within another layer's iteration. This
holds for both the reference decode and the determinism re-run (run1/run2,
same model object reused, not reloaded). **Streaming one layer's weights
in, using them, then dropping them before the next layer is a pure
loader/ordering change — it cannot alter the digest**, since CIS-2's fp32
math per layer is unchanged (same `stream_widen::load_tensor_streaming`
primitive already proven bit-exact against the old whole-buffer path in
`src/stream_widen.rs`'s own unit test, and proven bit-exact at 1.5B scale
end-to-end in LLM-5b: `9a463f4432...` matched LLM-4's digest byte-for-byte
on Kaggle). Caveat: because decode reprocesses every layer once per
generated token (16 tokens x 2 determinism runs = 32 passes per layer),
naive re-streaming-per-token would re-read+re-widen every layer's raw
bytes 32x instead of once — more disk I/O and CPU, but not a peak-RSS or
correctness problem (SSD, small files relative to run budget); could be
mitigated later by caching the current layer's widened f32 tensors across
the run1/run2 pair if that turns out to matter.

## Smaller pinned model to validate against first
Yes — `cis2-llm`'s vendored `cis2-verify2` computes the pinned §13.1
SmolLM2-135M reference vector (fixed digest, no CLI args needed). That
plus `cis2-fp`'s own `stream_widen::tests::streaming_matches_whole_buffer_bit_for_bit`
unit test (already exists, passing) satisfy the "prove no-digest-change on
the smallest pinned model first" gate — no NEEDS blocker on that count.

## RSS estimate if per-layer streaming is added
Dropping the all-layers-resident structure in favor of loading one
`LayerWeights` (~187 MB) at a time (embed_tokens ~933MB still resident
unless also made lazy) gives an estimated peak of roughly **~1.2 GB**
(933 MB embed table + ~187 MB current layer + KV caches/overhead),
comfortably under the 4.5 GB target — with headroom to also stream
embed_tokens per-row later if that table alone becomes a concern at
larger scale.

## Recommendation
**Phase 2 is worth attempting.** This is a runner change, not a math
change: the streaming primitive (`stream_widen.rs`) already exists,
already has a bit-exact unit test, and was already proven bit-exact at
1.5B scale on Kaggle (LLM-5b). The forward pass is confirmed
layer-sequential with no cross-layer weight dependency. A smaller pinned
digest (SmolLM2-135M) exists to gate correctness before the 1.5B run. The
main scope note for whoever picks up Phase 2: target `cis2-fp`
(`cm/llm8b-stream` branch there, per QUEUE.md), not `cis2-llm` — the
`--stream-weights` mode belongs in `cis2_ref`'s layer-loading loop
(replace the eager `for i in 0..n_layers { layers.push(...) }` with a
lazy per-layer loader called inside the decode loop), reusing
`stream_widen::load_tensor_streaming` as-is.
