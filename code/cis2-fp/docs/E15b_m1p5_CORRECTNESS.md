# E15b milestone 1.5 — correctness check vs a torch/transformers oracle

Published 2026-10-16 as part of the CIS-2 archive. No timing
numbers reported (Rule A).

## What this milestone answers

Milestone 1 (`docs/E15b_REFERENCE_RESULT.md`) proved the Rust CIS-2 fp32
reference forward pass for `HuggingFaceTB/SmolLM2-135M` is
**deterministic** (identical digests across repeated runs) but did not
establish it was **correct** — i.e. that it actually computes the right
function, not just a reproducible wrong one. This milestone compares it
against an independent oracle: HuggingFace `transformers` running the
same checkpoint through PyTorch's own fp32 forward pass.

## Oracle setup

- `torch==2.13.0+cpu` (CPU-only wheels from
  `https://download.pytorch.org/whl/cpu`, installed into
  `cis2-fp/.venv-oracle`, not the system Python)
- `transformers==5.16.1`, `safetensors==0.8.0`
- Determinism pins actually applied (`scripts/oracle_compare.py`):
  `torch.use_deterministic_algorithms(True)`,
  `torch.backends.cuda.matmul.allow_tf32 = False`,
  `torch.backends.cudnn.allow_tf32 = False`, `torch.set_num_threads(1)`,
  model loaded `dtype=torch.float32`, `model.eval()`, all forward passes
  under `torch.no_grad()`.
- Same checkpoint files as the Rust reference: loaded directly from
  `cis2-fp/weights/` (`model.safetensors` sha256
  `80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1`,
  matching milestone 1's provenance table — no re-download).
- Same prompt, same tokenizer file (`tokenizer.json` from the same
  `weights/` dir), same greedy-decode length (16 generated tokens, no
  sampling — argmax every step, KV-cache-free re-forward each step in the
  oracle for simplicity; this is mathematically equivalent to the Rust
  reference's KV-cached path since KV caching is pure memoization, not a
  reduction-order change).

Repro: `nice -n 10 .venv-oracle/bin/python scripts/oracle_compare.py /tmp/oracle_step0_logits.f32le`

## Rust reference re-run (with the m1.5 RoPE fix)

Before this comparison, `src/main.rs`'s RoPE `inv_freq` table was
switched from host `f64::powf` (an honest non-normative gap flagged in
milestone 1) to the pinned route-(b) `exp_pinned()` polynomial already
used elsewhere in `src/math.rs`, and a `CIS2_DUMP_STEP0_LOGITS` env-gated
debug dump was added (raw LE f32 bytes of the full step-0 logit vector,
not part of the normative witness/output).

```
CIS2_REF digest=ba88708bf4159a4057d4eef727820ebc5ce1744ae334bfe0cc0776e03509dd0f prompt_toks=4 gen_toks=16 dtype=fp32
inv_freq table_digest=da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12
run1_witness_digest == run2_witness_digest  (bit-identical, confirmed)
run1_argmax_digest  == run2_argmax_digest   (bit-identical, confirmed)
```

`cargo test --release` (6 unit tests) and `./scripts/no_fma_gate.sh` (both
FMA gates) still PASS after the RoPE change.

Note: the argmax digest (`0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff`)
is **unchanged** from milestone 1's pre-fix run — the 16 greedy token ids
are identical whether `inv_freq` comes from host `f64::powf` or the
pinned `exp_pinned` polynomial. Only the witness digest (which binds the
full logit bit pattern, not just the argmax) changed, as expected — the
logits shift by a few ULP-scale amounts from the different transcendental
route, but not enough to flip any argmax decision at this checkpoint/
prompt.

## Token-id comparison — all 16 generated tokens

| step | Rust reference | torch/transformers oracle | match |
|---|---|---|---|
| 0 | 28 | 28 | Y |
| 1 | 665 | 665 | Y |
| 2 | 436 | 436 | Y |
| 3 | 253 | 253 | Y |
| 4 | 1838 | 1838 | Y |
| 5 | 8180 | 8180 | Y |
| 6 | 3365 | 3365 | Y |
| 7 | 14176 | 14176 | Y |
| 8 | 30 | 30 | Y |
| 9 | 2306 | 2306 | Y |
| 10 | 4161 | 4161 | Y |
| 11 | 281 | 281 | Y |
| 12 | 253 | 253 | Y |
| 13 | 2066 | 2066 | Y |
| 14 | 2291 | 2291 | Y |
| 15 | 351 | 351 | Y |

Full lists:

```
prompt_tokens          = [6403, 1980, 253, 655]
rust reference (16)    = [28, 665, 436, 253, 1838, 8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351]
torch/transformers (16)= [28, 665, 436, 253, 1838, 8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351]
```

**16/16 exact match.** This is the primary correctness signal: the
argmax decoding path taken by the Rust reference is identical to
PyTorch's own fp32 forward pass of the same checkpoint, over 16
consecutive autoregressive steps (i.e. any small per-step logit
divergence never accumulated enough to flip a single greedy decision
across the whole generation).

## Step-0 full logit vector comparison

Compared all 49152 vocab-entry logits at generation step 0 (right after
prefill on the 4-token prompt, before the first generated token), raw f32
values, elementwise:

```
n = 49152
max_abs_diff        = 8.96453857421875e-05
  at vocab idx 40082: rust=5.486028671264648  oracle=5.486118316650391
max|logit| (rust)   = 22.531156539916992
relative max diff   = max_abs_diff / max|logit| = 3.98e-06
```

This is **well under** the pre-registered bar (`< 1e-2 * max|logit|`,
i.e. relative diff should be < 1e-2; actual is ~4e-6, roughly 4 orders of
magnitude tighter than the bar). As expected per the task brief, the
values are **not bit-identical** to torch — torch uses MKL/its own BLAS
reduction order, may use FMA internally, and its own libm transcendentals,
none of which CIS-2 pins — but they agree to within ordinary fp32
cross-implementation rounding noise. Bit-identity vs. torch was never the
goal; CIS-2 pins its *own* reduction order/no-FMA/table contract
specifically so that reproducibility does not depend on matching any
particular external framework's internals.

## Verdict

**CORRECT.** The Rust reference is a valid, semantically-correct fp32
forward pass of `HuggingFaceTB/SmolLM2-135M` under the CIS-2 §3 pinned
arithmetic contract:

- All 16 greedy-decoded token ids match the PyTorch/transformers oracle
  exactly, across the full autoregressive generation (not just step 0) —
  this is strong evidence the whole 30-layer forward pass (embedding,
  RMSNorm, RoPE, GQA causal attention, SwiGLU MLP, tied LM head) is wired
  correctly, not just superficially plausible.
- Step-0 full-vocab logits agree with the oracle to ~4e-6 relative
  (max abs diff ~9e-5 on a ~22.5-scale logit range), consistent with
  ordinary cross-implementation fp32 rounding differences (different
  reduction order, different transcendental routes, no FMA on the Rust
  side vs. torch/MKL's internal use of FMA) — not a bug.
- No divergence was found; there is nothing to localize layer-by-layer.

No timing numbers are reported (Rule A). This milestone does not test
cross-ISA (aarch64) reproducibility — that remains E15c's scope, as noted
in milestone 1's open questions.
