# pre-ledger-models-and-scale

- Scope: CIS-2 digests on other models and scales: SmolLM2-360M, Qwen2.5-0.5B, 7B, 8B feasibility; cross-box replays
- Verdict: **no ledger rows exist for these (they predate the experiment ledger, or were run as plain legs).** What each report says about itself is quoted below; this archive does not restate it as MET / NOT MET.

## Reports

- `reports/2026-09-08-CROSS-ISA-QWEN25-0.5B-CORPORATE-CHECKPOINT.md`: Bit-identical fp32 inference on a shipped corporate checkpoint, two ISAs — 2026-09-08
  - report states: **Result.** Alibaba's shipped **Qwen2.5-0.5B-Instruct** checkpoint replays **bit-identically** on two x86
- `reports/2026-09-18-LLM-5c-7b-second-run.md`: LLM-5c: second independent 7B CIS-2 run (Kaggle)
  - report states: - Status polled to `KernelWorkerStatus.COMPLETE` (kernel push ~02:39Z, complete ~02:56Z, ~17 min wall time).
- `reports/2026-09-18-LLM-8b-feasibility.md`: LLM-8b Phase 1 feasibility: streamed-weights 1.5B digest on box1
- `reports/2026-09-18-llm8b-7b-digest-result.md`: llm8b-7b merge verify + digest tail — 2026-09-18
  - report states: Both match the claimed values exactly (size 15231272088, sha256
- `reports/2026-09-22-pc2-smollm2-360m.md`: pc-2 RESULT: SmolLM2-360M as a second CIS-2 conformance case
- `reports/2026-09-22-pc2b-feasibility-screen.md`: pc-2b: feasibility screen for the next CIS-2 conformance candidate
  - report states: `2026-09-13-E5-E15-PHONE-SAMSUNG-RESULT.md`, are Rule-A identity-only, no
- `reports/2026-09-23-fast1b-crossbox-replay.md`: fast-1b: cross-box replay of KV-cache decode fix (cis2-spec verify3/)
- `reports/qwen05-rows-2026-10-16.md`: Qwen2.5-0.5B rows, 2026-10-16 (legs cis2-qwen05-{hq,w2,w3,w4})
  - report states: Source: state/feed/cm-{hq,w2,w3,w4}/done/cis2-qwen05-*/RESULT.txt. All four: weights sha256 prefix 88c14255, prompt ids 53ea8e67.
