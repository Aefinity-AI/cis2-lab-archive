# ERRATA (Aefinity-AI/cis2-llm)

## E-1 2026-10-16: Qwen2-7B EXPECTED witness re-pinned (1501ed47... retired)

- Decision 2026-10-16 under the full authorization of 2026-10-15 (NEEDS DECISION-JUSTIN cis3-0n).
- OLD value (retired, kept for history): `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a`
  (LLM-5b, LLM-5c second run, cis3-0k).
- Why wrong: digest of a MIS-MERGED checkpoint. The Kaggle kernel's shard merge wrote safetensors
  header offsets in model.safetensors.index.json order but data in shard order; 338 of 339 tensors
  were mislabelled (Kaggle merged-file sha256 `0e218d28...65ee`). Proven by simulation in
  `tests/kaggle/runs/2026-09-19-cis3-0m-mergebug.md`.
- NEW EXPECTED: `a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3`.
- Bound to: cis2-fp `scripts/merge_shards.py` @ `c0a2c346430c34dd54c9c0adc78829beb8755d32` and kernel
  `tests/kaggle/kernels/cis3-0n-bytemerge.py` @ `499b925` (weights_sha256 binds merged FILE bytes).
- Merged file: sha256 `13200c88e7482d83ed9a2bb23a01b515e46663ab57dba853389587d4173dcfa3`,
  15,231,272,088 bytes, 339 tensors.
- Evidence: box1 2026-09-19 and Kaggle cis3-0n v3 bit-identical; raw log
  `tests/kaggle/runs/2026-09-19-cis3-0n-kernel.log` line 767; report
  `tests/kaggle/runs/2026-09-19-cis3-0n-result.md`.
- Canonical pin table lives in cis2-fp `gpu/EXPECTED_DIGESTS.md` (+ cis2-fp `ERRATA.md` E-1).
- Historical logs/reports that cite 1501ed47 as "the" 7B digest are unedited; that reading is void.
