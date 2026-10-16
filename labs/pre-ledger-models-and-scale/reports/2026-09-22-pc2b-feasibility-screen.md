# pc-2b: feasibility screen for the next CIS-2 conformance candidate

Research only. No model runs, no weight downloads, no code/spec changes.
Already pinned: SmolLM2-135M (normative, §13.1) and SmolLM2-360M (informative,
PR #24, `state/reports/2026-09-22-pc2-smollm2-360m.md`).

## Timing anchor used for scaling
Only real measured anchor available (135M has no recorded wall time by
policy — `EXPECTED_DIGESTS.md`: "No timing numbers are recorded anywhere in
this repository"): SmolLM2-360M (360M params) box1 (i5-5200U, AVX2, 2c/4t)
= **23.9s**, box2 (Celeron N4020, scalar, 2c/2t) = **43.2s**
(`2026-09-22-pc2-smollm2-360m.md`). Scaling below is naive linear-in-params
(forward-pass FLOPs for a fixed 16-token greedy decode scale ~linearly with
weight count) — treat as order-of-magnitude, not a measured number; also
box1 has 5.8GB RAM, box2 has ~3.7GB total / ~2.2GB free (same report).
Phone has no CIS-2 wall-time anchor at all (past phone legs, e.g.
`2026-09-13-E5-E15-PHONE-SAMSUNG-RESULT.md`, are Rule-A identity-only, no
timing) — phone column below is an unverified guess, flagged.

## Table

| Model | Params | fp32 RAM est. (params×4B×1.2–1.5x) | box1 verify est. (×23.9s/360M) | box2 verify est. (×43.2s/360M) | phone est. (unverified) | License | Verdict |
|---|---|---|---|---|---|---|---|
| SmolLM2-1.7B | 1.71B | 6.84GB×1.2–1.5 = **8.2–10.3GB** | 4.75× → **~113s** | 4.75× → **~205s** | ~guess 150–300s | Apache-2.0 (HuggingFaceTB/SmolLM2-1.7B) | **MARGINAL** — same family/tokenizer as pinned vectors, untied embeddings (unlike 135M/360M) exercises a new code path, but 8–10GB fp32 RAM exceeds box1's 5.8GB outright; would need streaming (cis2-fp already has a streaming loader per `2026-09-18-LLM-8b-feasibility.md`, not yet wired into `verify3`'s hardcoded-135M C driver) or a bigger host. Not runnable as-is on box1/box2. |
| TinyLlama-1.1B | 1.1B | 4.4GB×1.2–1.5 = **5.3–6.6GB** | 3.06× → **~73s** | 3.06× → **~132s** | ~guess 100–200s | Apache-2.0 (TinyLlama/TinyLlama-1.1B-Chat-v1.0 and base checkpoints) | **MARGINAL** — fits box1's 5.8GB only at the low end of the estimate (tight, same "at ceiling" zone LLM-8b flagged for 1.5B Qwen); does not fit box2 (3.7GB) at all. Different family (Llama2 tokenizer/arch, not SmolLM2) — genuinely new cross-family evidence, unlike a same-family SmolLM2 step, which is a point in its favor for validation coverage. |
| Phi-2 (2.7B) | 2.7B | 10.8GB×1.2–1.5 = **13.0–16.2GB** | 7.5× → **~179s** | 7.5× → **~324s** | not attempted (too big) | MIT (was Microsoft Research license until it was changed to MIT — verified via `microsoft/phi-2/discussions/70` and `LICENSE` file at main) | **SKIP for now** — RAM (13–16GB) is far beyond both box1 (5.8GB) and box2 (3.7GB); also Phi-2 uses a parallel attn+MLP block (not the standard sequential Llama-style block SmolLM2/Qwen/TinyLlama share), so it is not a drop-in for the existing reference implementation — would need real architecture-support code, out of scope for a "next pin" pick. License is fine (MIT, ungated) but that's not the blocker here. |
| BitNet-b1.58 reproductions (1bitLLM `bitnet_b1_58-large` 700M / `-3B`; microsoft `bitnet-b1.58-2B-4T`) | 700M / 3B / 2B | 700M: 2.8GB×1.2–1.5=**3.4–4.2GB**; 2B-4T: 8GB×1.2–1.5=**9.6–12GB** | 700M: 1.94× → **~46s** (arch caveat below) | 700M: 1.94× → **~84s** | not attempted | 1bitLLM repos: no clear license tag found on the model card itself (unverified — flagged, not confirmed permissive); microsoft/bitnet-b1.58-2B-4T: MIT | **SKIP** — not architecturally a drop-in regardless of size: `BitnetForCausalLM` uses a custom `BitLinear` layer (ternary-weight simulated quantization at inference, `configuration_bitnet.py`), not the standard Llama-style linear/RMSNorm stack the current CIS-2 reference construction assumes. Pinning this would mean writing and validating new §-level operator semantics for BitLinear, not just a weights/config swap like the SmolLM2/Qwen family — a spec-extension project, not a "next conformance vector" pick. Also the 1bitLLM checkpoints' license is unverified (no tag found), an independent blocker if this were otherwise in scope. |

## Notes
- SmolLM2-1.7B and TinyLlama-1.1B are both nominally within reach of box1's
  RAM only at the low end of the 1.2–1.5x overhead band; neither fits box2
  (3.7GB) fp32 without a streaming loader change to `cis2-fp`'s `main.rs`
  (per `2026-09-18-LLM-8b-feasibility.md`, the streaming primitive exists
  and is unit-tested bit-exact but is not wired into the eager
  all-layers-in-RAM load loop, nor into `verify3`'s hardcoded-135M C
  driver used for the normative vector).
- Phone estimates in this table are unverified guesses (order-of-magnitude
  vs. box2) — no phone CIS-2 timing has ever been recorded per Rule A;
  do not treat the phone column as evidence.
- All Apache-2.0/MIT licenses above were spot-checked via HF search results
  in this session, not by opening each model card by hand; treat as
  "reported," not independently re-verified against the live LICENSE file
  except Phi-2 (whose license file was directly cited: `microsoft/phi-2`
  discussion #70 + `LICENSE` blob at main).

## Recommendation
No candidate here is a clean "pin it now" the way 360M was (same family,
fits both boxes, no arch work). Priority order if Fable wants to proceed
anyway:
1. **TinyLlama-1.1B** — first choice: new family (genuine cross-family
   evidence, not just a bigger SmolLM2), Apache-2.0, standard Llama block
   (no new op semantics needed), RAM is tight-but-plausible on box1 alone
   (box2 likely out — informative-only on box1, matching how 360M was
   informative not normative).
2. **SmolLM2-1.7B** — runner-up: safest architecturally (proven family/
   tokenizer, exercises untied embeddings) but RAM (8–10GB) requires the
   streaming loader work from LLM-8b Phase 2 first; do that work before
   attempting this, not this before that work.
Phi-2 and the BitNet reproductions are SKIP until either more RAM is
available (Phi-2) or someone scopes a BitLinear operator addition to the
spec (BitNet) — neither belongs in a "next pc-2c pin" pick.
