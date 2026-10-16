# ERRATA (Aefinity-AI/cis2-fp)

## E-1 2026-10-16: Qwen2-7B EXPECTED witness re-pinned (1501ed47... retired)

- Decision 2026-10-16 under the full authorization of 2026-10-15 (NEEDS DECISION-JUSTIN cis3-0n).
- OLD value (retired, kept for history): `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a`
  (Kaggle LLM-5b / LLM-5c / cis3-0k, prompt_toks=4 gen_toks=4 fp32 sequential).
- Why wrong: it is the digest of a MIS-MERGED checkpoint. The Kaggle kernel's shard merge wrote
  safetensors header offsets in model.safetensors.index.json order but the data in shard order,
  so 338 of 339 tensors were mislabelled (merged-file sha256 `0e218d28...65ee`, not the
  faithful `13200c88...`). Not a numerical divergence of the engine.
- NEW EXPECTED: `a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3`
  (Qwen/Qwen2-7B, prompt_toks=4 gen_toks=4 fp32 sequential, prompt tokens [12522, 5193, 264, 882]).
- Bound to: merge recipe `scripts/merge_shards.py` @ cis2-fp `c0a2c346430c34dd54c9c0adc78829beb8755d32`
  and kernel cis2-llm `tests/kaggle/kernels/cis3-0n-bytemerge.py` @ `499b925`.
  weights_sha256 binds the merged FILE bytes, so the witness is only valid for this byte layout.
- Merged file: sha256 `13200c88e7482d83ed9a2bb23a01b515e46663ab57dba853389587d4173dcfa3`,
  15,231,272,088 bytes, 339 tensors.
- Evidence: box1 run 2026-09-19 (docs/hardware_logs/llm8b_7b_aefinity-box_2026-09-18.log, RESULT.md)
  and Kaggle `cis3-0n-bytemerge` v3 are bit-identical (31/31 layer digests, argmax, tokens, witness);
  raw log cis2-llm `tests/kaggle/runs/2026-09-19-cis3-0n-kernel.log` line 767.
- Historical documents (RESULT.md, docs/LLM8b_STREAM_WEIGHTS.md, hardware logs) are kept unedited
  except for a pointer; statements in them that 1501ed47 is "the pin" are void.
