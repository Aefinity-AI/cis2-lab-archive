# cis3-0m — root cause of the LLM-8b-7B box1/Kaggle digest mismatch: Kaggle kernel merge bug

**Status:** Mechanism proven on box1 2026-09-19 08:0xZ (Fable). Fixed-merge Kaggle
re-run pending (kernel `tests/kaggle/kernels/cis3-0m-mergefix.py`). **No EXPECTED digest has
been rewritten.**

## One-line finding

All three Kaggle Qwen2-7B runs (LLM-5B, LLM-5c, cis3-0k → witness `1501ed47…`) ran `cis2_ref`
on a **mis-merged checkpoint**: the kernel's `download_and_merge_sharded` computed the merged
safetensors header offsets in `weight_map` (index.json) order but wrote the tensor bytes
grouped by sorted shard, so 338 of 339 tensors were mislabelled. box1's run (`a4a6770e…`)
loaded the pinned, sha256-verified shards correctly. The 7B "cross-machine divergence" was a
corrupted input on the Kaggle side, not a forward-pass or hardware difference.

## Evidence chain (all reproducible, no engine run needed)

1. **cis3-0k per-layer diff** (`2026-09-19-cis3-0k-layerdiff.md`): first diverging
   `LAYER_DIGEST` label is `embed` — box1 `20d1c311…`, Kaggle `38e87ad1…`. `embed` is
   `hash_f32_slice` over `model.embed_tokens[882*3584 .. +3584]` widened bf16→fp32
   (cis2-fp `src/main.rs` 318-324, 374-384; position = last prompt token, id 882).
2. **Ground truth from the pinned shards on box1** (python over raw safetensors, no
   `safetensors` lib): row 882 of `model.embed_tokens.weight` in
   `model-00001-of-00004.safetensors` (sha256 matches its pin) widened → `20d1c3114f5af596…`
   **== box1's embed digest.** Same row read from box1's merged `model.safetensors`
   (`merge_shards.py`) is byte-identical. So box1 hashed the true embedding row.
3. **Swap hypothesis refuted:** `lm_head.weight` row 882 widened → `ec4c8200…` ≠ Kaggle's.
4. **Kernel source** (pulled with `kaggle kernels pull aefinityaiinc/cis3-0k-layerdigests`,
   saved as `tests/kaggle/kernels/cis3-0k-layerdigests.py`, lines 156-192): header loop
   `for name in tensor_names:` (weight_map order) vs data loop `for shard_name in shard_names:`
   (sorted shards). Qwen2-7B's index.json lists `lm_head.weight` (shard 4) **first**, so the
   orders differ.
5. **Mechanism proven** (`2026-09-19-cis3-0m-simulate-kaggle-merge.py`, run on box1 against the
   pinned shards, simulating exactly that layout):

   ```
   index order first 4: ['lm_head.weight', 'model.embed_tokens.weight',
                         'model.layers.0.input_layernorm.weight', 'model.layers.0.mlp.down_proj.weight']
   Kaggle-layout embed row 882 actually comes from tensor: model.layers.0.mlp.down_proj.weight
   simulated Kaggle LAYER_DIGEST embed: 38e87ad1ec58e68ce6a8586a59f5f37c983b3718edb5fe8783b77d41f70f784c
   Kaggle logged value                : 38e87ad1ec58e68c...
   tensors whose Kaggle header offset != data offset: 338 of 339
   ```

   The simulated digest matches Kaggle's logged `LAYER_DIGEST embed` to all 64 hex digits
   (Kaggle log: `2026-09-19-cis3-0k-kernel.log`). That is a 256-bit coincidence otherwise.

## Corroboration

- Kaggle's 7B output was degenerate (`run1_tokens` tail `1305,1305,3811,3811`); box1's was
  fluent (`11,1052,572,264`). Weights read through the wrong header produce garbage.
- Kaggle's Qwen2-1.5B reproductions (single-file checkpoint, no merge step) match box1
  bit-for-bit (LLM-8b, `9a463f44…`). Only the sharded model goes through the buggy merge.
- The same merge code appears verbatim in LLM-5B / LLM-5c kernels (`LLM5B-kernel.log` lines
  645/667 "merging 4 shards one at a time"); LLM5B-LOG.md line 140 records the data-only
  byte count 15,231,233,024, consistent with this layout.
- `weights_sha256` differs between box1 (`13200c88…`) and Kaggle (`0e218d28…`) because the
  merged headers differ (key order / `__metadata__` / offsets) — which is exactly why the
  pre-cis3-0m H4 hypothesis ("streamed vs whole-buffer widening") could not have explained an
  `embed`-level divergence. H4 is superseded and should not be run.

## Consequences

- The pinned Kaggle 7B witness digest `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a`
  is the digest of a **corrupted checkpoint**. Under the hard rule it stays pinned as-is until a
  fixed-merge Kaggle run exists; the "reproduced twice on Kaggle" note is void because all three
  Kaggle runs shared the bug (a reproduction of the same corruption is not independent evidence).
- box1's `a4a6770e…` (28 block digests + final_norm + logits in cis2-fp
  `docs/hardware_logs/llm8b_7b_layerdigests_aefinity-box_2026-09-19.log`) is the current best
  candidate for the true Qwen2-7B fp32 sequential digest. It becomes a re-pin **proposal** only
  after the fixed Kaggle kernel reproduces all 31 LAYER_DIGESTs and the witness on a second
  machine.
- The receipt system did its job: the corrupted weights were caught at the weights/witness
  digest level, and `--layer-digests` localised the fault to the first tensor touched. That is
  the CIS-3 value proposition, stated without "validated"/"proves correctness".

## Fix

`tests/kaggle/kernels/cis3-0m-mergefix.py` (diff vs the cis3-0k kernel): build the merged
header in the same shard-grouped write order (`write_order`), and self-check after writing that
every tensor's header offset equals its physical position. Same engine dataset
(`aefinityaiinc/cis2-fp-engine-cis3-0k`, cis2-fp `c0a2c34` = `8326397` + marker), same prompt
set, `--layer-digests`. Expected outcome: 31/31 LAYER_DIGESTs and witness `a4a6770e…` equal to
box1. Note `weights_sha256` will still differ from box1's `13200c88…` unless the merged header
bytes happen to be identical; compare layer digests and witness, not the file hash.

## Wording for other docs

Replace "7B reproduced twice on Kaggle, box1 divergent under investigation" with:
"Kaggle 7B runs used a mis-merged checkpoint (kernel merge bug, proven 2026-09-19); box1 run
matches the pinned shards; fixed-merge Kaggle reproduction pending."
