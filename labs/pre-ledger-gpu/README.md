# pre-ledger-gpu

- Scope: CIS-2 on GPUs: E18/E18B, gpu2 batch sweeps, Kaggle and Lightning T4 replays, bf16 design memo
- Verdict: **no ledger rows exist for these (they predate the experiment ledger, or were run as plain legs).** What each report says about itself is quoted below; this archive does not restate it as MET / NOT MET.

## Reports

- `reports/2026-09-02-E18-cis2-gpu-memo.md`: E18 — CIS-2 on GPU: design memo (research workflow wf_43bbc2d9-074, 2026-09-02)
  - report states: (3) a pinned blocked-tree revision (v0.4) is a *performance* leg (E18c) and must not precede the feasibility result, or a failure could not be attributed.
- `reports/2026-09-02-E18-prior-art.md`: E18 — Prior art: fp32 (or FP) CPU↔GPU bit-identical transformer/LLM inference from a spec
  - report states: | 1 | **RepDL** (Microsoft), arXiv:2510.09180, github.com/microsoft/RepDL | "Bitwise-consistent results for DL training/inference across multiple executions with the same or different CPU or GPU systems," via correct rou
- `reports/2026-09-03-E22-CIS2.5-bf16-design.md`: E22 — CIS-2.5: bf16-weight / fp32-accumulate inference, a design memo
  - report states: **Date:** 2026-09-03 · **Status:** design memo, not a spec, not normative, HELD (no publish decision made). **Rule A:** no timing/throughput/speed claim appears below. **Rule B:** every number below cites the command/fil
- `reports/2026-09-06-E18B-GPU-RESULT.md`: E18b/E18c GPU run — CIS-2 receipt reproduced bit-for-bit on a Tesla P100 (2026-09-06)
  - report states: | check | verdict |
- `reports/2026-09-18-gpu2-batch-int8-progress-2.md`: gpu-2: batch+int8 determinism — progress 2 (step 4, int8 quantization)
  - report states: BATCH_TEST RESULT: MATCH
- `reports/2026-09-18-gpu2-batch-int8-progress.md`: gpu-2: batch={4,8}/int8 digest sweep — 2026-09-18 tick 2 progress
  - report states: **MATCH.** Both digests equal
- `reports/2026-09-18-gpu2-batch-int8.md`: gpu-2: batch={4,8} + INT8 extension of E18 — status report
  - report states: existing sequential reduction, expected to MATCH batch=1 — low
- `reports/2026-09-19-gpu2-kaggle-sweep.md`: gpu-2 (cis2-fp) steps 5-6: Kaggle GPU sweep v2 — SUCCESS, all arms match expected pattern
  - report states: HOST_GATE digest=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df expected=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df MATCH
- `reports/2026-09-25-lt2-lightning-t4-batched.md`: lt-2: Lightning AI T4 replay of gpu-3k batched-forward sweep (third GPU host)
  - report states: `==== gpu-3 --batch B: PASS ====` verdict. Row 0 digest is identical
- `reports/2026-09-25-lt3-lightning-t4-fm5-replay.md`: lt-3: Lightning AI T4 replay of the fm-5 deterministic-KD run (second GPU host)
  - report states: 1. Connected to `scratch-studio-devbox` (status `Stopped`), started it on
