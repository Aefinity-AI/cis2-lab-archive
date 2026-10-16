# cis3-0m witness note — why the witness differs while every layer digest matches 

Date: 2026-09-19 ~08:45Z. Author: Fable (operator), verified against raw logs and source.

## Verified facts
- Kaggle kernel `cis3-0m-mergefix` log (`2026-09-19-cis3-0m-kernel.log`): 32 `LAYER_DIGEST` lines
  (31 labels for 7B + 1 duplicate stdout line); the sorted unique set is byte-identical to box1's
  `llm8b_7b_layerdigests_aefinity-box_2026-09-19.log` (comm -3 → 0 lines).
- `argmax_digest` run1 == run2 == box1: `a8ed47fb…3265` (7B). 1.5B control: `9a463f44…4bf8` (known LLM-4 value).
- `witness_digest` 7B: box1 `a4a6770e…cfb3`, Kaggle `7752994d…2b57` (run1 == run2 on each host).
- `weights_sha256`: box1 `13200c88…cfa3`, Kaggle fixed-merge `4d4d9d7c…d6bc` (buggy merge was `0e218d28…`).

## Cause (source, cis2-fp @ c0a2c34, `src/main.rs:1084-1091`)
```
let mut witness = Sha256::new();
witness.update(weights_sha256);      // <- sha256 of the merged model.safetensors FILE BYTES
witness.update(tokenizer_sha256);
witness.update(config_sha256);
witness.update(math::table_digest());
witness.update(inv_freq_table_digest);
for &t in &prompt_ids { witness.update(t.to_le_bytes()); }
... per step: witness.update(logits bytes); witness.update(next_id)
```
The witness preimage begins with `weights_sha256`, which is the hash of the merged safetensors
file on disk, header included. box1's `scripts/merge_shards.py` writes the header in each shard's
own header order (`hdr.items()`), while the Kaggle kernel writes it in `weight_map` order grouped
by shard. Same tensor bytes, different header JSON → different `weights_sha256` → different witness,
even though every logit, every layer digest and every generated token is identical.

So: the witness delta is fully accounted for by a known, non-numerical input; there is no evidence of
any numerical divergence between box1 and Kaggle on the fixed merge. This is consistent with, and
sufficient to explain, the delta. It is NOT yet a bit-for-bit witness reproduction across hosts.

## What would make it definitive (proposed, not executed)
- cis3-0n: rerun the Kaggle kernel with a merge that reproduces box1's file bytes exactly
  (port `merge_shards.py` header order + padding), expect `weights_sha256 = 13200c88…` and
  `witness_digest = a4a6770e…`. ~25 min Kaggle CPU. Any other outcome = real finding.

## Spec consequence (decision for Justin, in NEEDS)
Binding the FILE hash means the 7B receipt is only cross-host reproducible when the merged file is
byte-identical, i.e. the merge recipe becomes part of the pinned artefact. Two options:
1. Keep file-hash binding, pin the merge recipe (`merge_shards.py` @ commit) next to EXPECTED.
2. Change the weights binding to a content digest (canonical: sorted tensor names, each name|dtype|
   shape|raw bytes) so any faithful merge or sharding yields the same witness. Spec change → new
   EXPECTED for every pinned receipt (CIS-2 1.5B included), so this is a v0.4-class decision.

No EXPECTED value was edited. The currently pinned 7B EXPECTED was produced with the buggy merge
(338/339 mislabelled tensors) and should be treated as a digest of corrupted weights.
