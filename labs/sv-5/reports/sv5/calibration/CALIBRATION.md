# sv-5 calibration record (written 2026-10-01 19:54Z, before any TEST-split or tampered run)

100 CALIBRATION prompts, clean model only. Provider box1. Raw rows on penguin: ~/sv5-data/runs/{A,torch,verify}
(sha256 of the calibration rows of each pair is inside the thresholds file of that pair). Thresholds recomputed
independently from the raw verify rows by Fable (max over the 100 checks and both proofs): equal to the files.

| pair | class relation | B-cal T_exp / T_mean / T_median | B-pub rejects (38/10/8) | token ids equal | fp32 hidden hash equal |
|---|---|---|---|---|---|
| box1→penguin | same class (AVX2) | 0 / 0 / 0 | 0 of 100 | 100 of 100 | 100 of 100 |
| box1→box2 | cross class (AVX2 → no AVX2) | 1 / 0 / 0 | 0 of 100 | 100 of 100 | 0 of 100 |
| box1→box3 | cross class (AVX2 → no AVX2) | 1 / 0 / 0 | 0 of 100 | 100 of 100 | 0 of 100 |

In each cross-class pair exactly one of the 100 checks showed one exponent mismatch among the top-128 values; all
other TOPLOC statistics were zero.

Arm A (CIS-2 driver), clean, same 100 prompts: token ids, witness digest and argmax digest equal to box1 on
penguin 100/100, box2 100/100, box3 100/100, box4 100/100, box5 100/100. By Amendment 2 all six hosts may compute
arm A provider runs. The CIS-2 runtime and stock PyTorch gave the same 32 greedy tokens on 100 of 100 prompts (box1).

Median seconds per run (one thread): arm A driver box1 9.0, penguin 8.9, box2 9.6, box3 13.6, box4 14.5, box5 13.8;
PyTorch provider box1 2.6; PyTorch verify (prefill + greedy rerun) penguin 2.6, box2 9.8, box3 9.1.

These are clean-run calibration numbers. No TEST prompt and no tampered model, patch or prompt had been run when
this file was committed (0 non-calibration row files existed under ~/sv5-data/runs).
Host map sha256 2f76c7329d784380d112f8ad57794b12d89f9ea5d1623611e47e148d70d30b51; prompts sha256 4b4e7924…bf9bc.
