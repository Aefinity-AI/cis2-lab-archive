# shape-1 RESULT (2026-10-03)

Verdict: bar (a) MET, bar (b) MET (own verdict). Scope: one extra shape (llama-160m, MHA, untied head), one prompt set (100 prompts), 32 greedy tokens; nothing about larger models, other tokenizers or throughput.

Process disclosure: the `start` record was entered LATE (after box3/4/5 runs finished 15:32-16:26Z). Bar text and sha256 (8ddab495...) unchanged since registration 14:15:59Z. The penguin run happened after the start record.

Evidence (re-derived from raw rows.jsonl files, not from RESULT lines): rows from penguin (AVX2), box3 (N4020C), box4 (Sempron SI-42), box5 (Pentium T2310) each have 100 rows; idx sets equal; ids_out, witness and argmax identical on 100 of 100 prompts across all four hosts. C-driver tokens equal ref.jsonl (stock torch fp32 greedy, bf16-widened weights) on 100/100 on each host; no differing position. rows_sha256 fa3e52cfd8624eaea0d7f2dd63d07c836ab684656484d2658572cd9b5427e272. Inputs: prompts.jsonl c9684006..., model.safetensors 261167a0... verified. Prediction (a) yes, (b) 97-100: held.
Penguin run: systemd-run scope, MemoryMax=2500M, CPUQuota=60%. Box rows rsynced for comparison only (mtimes predate start; only penguin outputs given to cm-exp result).
Caveat: single run per prompt; cross-host seconds per prompt not tabulated here.
