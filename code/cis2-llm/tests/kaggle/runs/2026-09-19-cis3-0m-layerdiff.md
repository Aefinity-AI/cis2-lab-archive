# cis3-0m: fixed-merge Kaggle 7B rerun vs box1 (H3 cross-host diff, retry)

Published 2026-10-16 as part of the CIS-2 archive. Leg cis3-0m. Reruns cis3-0k with the shard-merge bug fixed
(tests/kaggle/kernels/cis3-0m-mergefix.py), using the same engine dataset
(`aefinityaiinc/cis2-fp-engine-cis3-0k`, cis2-fp `c0a2c34`) and the same
kernel settings as cis3-0k (CPU-only, private, internet enabled, dataset
source `aefinityaiinc/cis2-fp-engine-cis3-0k`).

## Kernel run

- Kernel: `aefinityaiinc/cis3-0m-mergefix` (private), version 1.
- Pushed via `kaggle kernels push`; polled every ~120s.
  ```
  08:14:53 RUNNING
  08:16:55 RUNNING
  08:19:12 RUNNING
  08:21:17 RUNNING
  08:23:22 RUNNING
  08:19:21 (transient) HTTPSConnectionPool ... Connection to api.kaggle.com timed out
  08:21:25 RUNNING
  08:23:30 RUNNING
  08:25:36 RUNNING
  08:27:40 RUNNING
  08:29:44 COMPLETE
  ```
  RUNNING -> COMPLETE in roughly 25 min wall time (push confirmed shortly before
  the 08:14:53 poll).
- Raw stdout/stderr log retrieved via the Kaggle Python API
  (`KaggleApi().kernels_logs('aefinityaiinc/cis3-0m-mergefix')`, same method
  used for cis3-0k — the CLI's `kernels output` only fetches
  dataset/build artifacts, not stdout). Saved verbatim (JSON array of
  `{stream_name,time,data}` entries, 978 entries) as
  `tests/kaggle/runs/2026-09-19-cis3-0m-kernel.log`.

## Merged header self-check (verbatim from the kernel log)

```
merging 4 shards one at a time -> /kaggle/working/hf/qwen2-7b-merged.safetensors
merged 339 tensors, 15231233024 bytes, in 117.0s
merged header self-check OK: 339 tensors contiguous in write order
```

## Per-layer digest table (31 labels, box1 vs Kaggle)

| label | box1 digest | kaggle digest | status |
|---|---|---|---|
| embed | `20d1c3114f5af59661f1d30c60e45d3d220cd9cceff7c7cb19fc4924b69cd416` | `20d1c3114f5af59661f1d30c60e45d3d220cd9cceff7c7cb19fc4924b69cd416` | MATCH |
| block_0 | `b62ef72537abbda08442ec68b8349a8d52c3eb7cb452447358a43cfe2dc23aa5` | `b62ef72537abbda08442ec68b8349a8d52c3eb7cb452447358a43cfe2dc23aa5` | MATCH |
| block_1 | `a2cc20831a8dc837a570d10a67cc6608f6eefcca8e9248474eeed7c5c80f1909` | `a2cc20831a8dc837a570d10a67cc6608f6eefcca8e9248474eeed7c5c80f1909` | MATCH |
| block_2 | `4e6dcc65d55d3efd21a04438081a4063efae3cad215fd718e4c31a9522d1344f` | `4e6dcc65d55d3efd21a04438081a4063efae3cad215fd718e4c31a9522d1344f` | MATCH |
| block_3 | `443ad0746320603624af67330fedcf74c2a25272bbe0439f3fdf0b71c7faa278` | `443ad0746320603624af67330fedcf74c2a25272bbe0439f3fdf0b71c7faa278` | MATCH |
| block_4 | `a98a54d7c4532916ff04f4570482d1e3e247c0d5d0b3e5c4882cb39f7ba3e3a7` | `a98a54d7c4532916ff04f4570482d1e3e247c0d5d0b3e5c4882cb39f7ba3e3a7` | MATCH |
| block_5 | `3c5dc16e6503405e63a29dce215154991acb8fc29f1a6e67cc27ff6a52618d1d` | `3c5dc16e6503405e63a29dce215154991acb8fc29f1a6e67cc27ff6a52618d1d` | MATCH |
| block_6 | `73108bd54eeb56315441b375ed5b596796f6c8acdc138114c97c87518f5843b1` | `73108bd54eeb56315441b375ed5b596796f6c8acdc138114c97c87518f5843b1` | MATCH |
| block_7 | `fedc90c2fd17bb45f4fa2c0d415658ecb716f037d763884ea61c2d8c75c06b16` | `fedc90c2fd17bb45f4fa2c0d415658ecb716f037d763884ea61c2d8c75c06b16` | MATCH |
| block_8 | `d12a46e22296606f0274f9f7a80c7f98c8b0c6fb90306f57092845697075567f` | `d12a46e22296606f0274f9f7a80c7f98c8b0c6fb90306f57092845697075567f` | MATCH |
| block_9 | `31461e2b932b2bb75b881a3f9156b02a6e89244831b2405e348066f303c92d5d` | `31461e2b932b2bb75b881a3f9156b02a6e89244831b2405e348066f303c92d5d` | MATCH |
| block_10 | `0ef7caac10b4661d5519713378a9bc2fa2f699aa95da036cc44953f257355f28` | `0ef7caac10b4661d5519713378a9bc2fa2f699aa95da036cc44953f257355f28` | MATCH |
| block_11 | `cb8827a5da643087a64e193b63a570aa56340555b98bd48253878de5daa9caeb` | `cb8827a5da643087a64e193b63a570aa56340555b98bd48253878de5daa9caeb` | MATCH |
| block_12 | `3687ab01ba2e8f5224e8aae417b87228ca1d76b477676e133e1702708fd9003e` | `3687ab01ba2e8f5224e8aae417b87228ca1d76b477676e133e1702708fd9003e` | MATCH |
| block_13 | `a791fa976435ef6c6523c1f54d103059b8f7ee589d6c2bd001c3c15d2586c9e5` | `a791fa976435ef6c6523c1f54d103059b8f7ee589d6c2bd001c3c15d2586c9e5` | MATCH |
| block_14 | `84f2885eec84f38b4cf4e641217588c4a2b0e391eabbb3a395499fcba0e983a2` | `84f2885eec84f38b4cf4e641217588c4a2b0e391eabbb3a395499fcba0e983a2` | MATCH |
| block_15 | `e80116e25956b323b95f4f10fcb452e6a19e90ce340d2c5c45b69389afa5035c` | `e80116e25956b323b95f4f10fcb452e6a19e90ce340d2c5c45b69389afa5035c` | MATCH |
| block_16 | `8b2ebdd363e41b713b563f904ad068ef90652465a0ec442a12375947ef28dcb1` | `8b2ebdd363e41b713b563f904ad068ef90652465a0ec442a12375947ef28dcb1` | MATCH |
| block_17 | `d3ecfa6c24ca82c911279f838dc6d14a0501de891b9cd780f427ab2f01e03c34` | `d3ecfa6c24ca82c911279f838dc6d14a0501de891b9cd780f427ab2f01e03c34` | MATCH |
| block_18 | `4bd660746cffa6641629702549d25e35fbb1536d0d0fad1fa1227cc25c9da6a8` | `4bd660746cffa6641629702549d25e35fbb1536d0d0fad1fa1227cc25c9da6a8` | MATCH |
| block_19 | `a3dd6400e6ca62bfb42ae4824b1b1e03ea8f6dfea9a7bddbc676c78395e626e0` | `a3dd6400e6ca62bfb42ae4824b1b1e03ea8f6dfea9a7bddbc676c78395e626e0` | MATCH |
| block_20 | `7b171eec2c0355f118a36922dc809569486c5cc73b527d03fd7e27f21851770c` | `7b171eec2c0355f118a36922dc809569486c5cc73b527d03fd7e27f21851770c` | MATCH |
| block_21 | `71a618e7fc4d4518988e090f33931a302521c664d0a7c21a9e41625885881908` | `71a618e7fc4d4518988e090f33931a302521c664d0a7c21a9e41625885881908` | MATCH |
| block_22 | `68abc10432f83af0b600db15061607d71b7bc659c17a6a9b62778df1e3d2207d` | `68abc10432f83af0b600db15061607d71b7bc659c17a6a9b62778df1e3d2207d` | MATCH |
| block_23 | `53b24c6deaebb1762cbbc82ceaf7ce8fa37c760214eed9e8a81100ad3b825124` | `53b24c6deaebb1762cbbc82ceaf7ce8fa37c760214eed9e8a81100ad3b825124` | MATCH |
| block_24 | `afbb187dedc45ca9a5c62a3a0aa6ac07d8e2bf67e60a3c4698de966432e15343` | `afbb187dedc45ca9a5c62a3a0aa6ac07d8e2bf67e60a3c4698de966432e15343` | MATCH |
| block_25 | `35fbd3afbf78d3530b15eb07568478049f40a8daa5b95b512810223d3072cb0a` | `35fbd3afbf78d3530b15eb07568478049f40a8daa5b95b512810223d3072cb0a` | MATCH |
| block_26 | `5ffad7dd3d795659642cdc1479bf058c25e610f3b2291fe7481d895844a56ad7` | `5ffad7dd3d795659642cdc1479bf058c25e610f3b2291fe7481d895844a56ad7` | MATCH |
| block_27 | `e3117c5b404be9e1cd17b7759b6983f1e26bd7e2cda4c7c3b914dc753ed06a44` | `e3117c5b404be9e1cd17b7759b6983f1e26bd7e2cda4c7c3b914dc753ed06a44` | MATCH |
| final_norm | `c56066fa9594801fbf6fee2ca925a39977ad8041335a323989c1808521b477d2` | `c56066fa9594801fbf6fee2ca925a39977ad8041335a323989c1808521b477d2` | MATCH |
| logits | `e24e704bfdd04f10fdec91307e013f238d0d207b421f6e441ac2a6fa65780073` | `e24e704bfdd04f10fdec91307e013f238d0d207b421f6e441ac2a6fa65780073` | MATCH |

FIRST_DIVERGING_LABEL: NONE (ALL 31 MATCH) — output of
`tests/kaggle/runs/2026-09-19-cis3-0m-layerdiff.py` run against box1's
`docs/hardware_logs/llm8b_7b_layerdigests_aefinity-box_2026-09-19.log` and
the Kaggle plain-text log.

## Witness / output digests (7B)

Generated tokens (run1/run2, both hosts):

- box1: `run1_tokens=[12522, 5193, 264, 882, 11, 1052, 572, 264]`,
  `run2_tokens=[12522, 5193, 264, 882, 11, 1052, 572, 264]` (identical, matches
  Kaggle's generated continuation `11, 1052, 572, 264` after the same 4-token
  prompt).
- Kaggle: `run1_tokens=[12522, 5193, 264, 882, 11, 1052, 572, 264]`,
  `run2_tokens=[12522, 5193, 264, 882, 11, 1052, 572, 264]`.
- Generated token ids are bit-identical across both hosts.

argmax digest — MATCH:

- box1: `run1_argmax_digest=a8ed47fb9cca7b6ac1830fc12a18ebb9615b77e29b012f8c036ce7cb0183c265`
- Kaggle: `run1_argmax_digest=a8ed47fb9cca7b6ac1830fc12a18ebb9615b77e29b012f8c036ce7cb0183c265`

witness digest / CIS2_REF digest — **DIFFERS**:

- box1: `CIS2_REF digest=a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3 prompt_idx=0 prompt_toks=4 gen_toks=4 dtype=fp32 reduction_mode=sequential`
- Kaggle: `CIS2_REF digest=7752994d5d6e0dfd1a8889f781d46d057469f28ce3e3622dc99f6ffeab392b57 prompt_idx=0 prompt_toks=4 gen_toks=4 dtype=fp32 reduction_mode=sequential`

This is an observed finding, not a template match: all 31 `LAYER_DIGEST`
checkpoints match bit-for-bit, the generated token sequence matches, and the
`argmax_digest` matches — but the `witness_digest`/`CIS2_REF digest` differs
between box1 and the fixed-merge Kaggle kernel. Neither of the two prescribed
verdict sentences ("all 31 layer digests and the witness match box1" / "first
diverging label = X") fits this result cleanly; reporting exactly what was
observed instead.

## weights_sha256 (expected to differ, confirmed different — not a failure)

- box1: `weights_sha256=13200c88e7482d83ed9a2bb23a01b515e46663ab57dba853389587d4173dcfa3`
- Kaggle: `weights_sha256=4d4d9d7cbe8aa9049d7fcf8c4d4af909bfc3b562a0d3c17492acace9b78ad6bc`

Both differ from cis3-0k's buggy-merge `weights_sha256` as well (not quoted
here — see `2026-09-19-cis3-0k-layerdiff.md`). `tokenizer_sha256` and
`config_sha256` match box1 for the tokenizer (`f7c9b2dba4a296b1aa76c16a34b8225c0c118978400d4bb66bff0902d702f5b8`
on both); `config_sha256` also matches
(`d318b49c4a29771e259d93053084eb752f5bfe69c20c4f2e041bd1017884f810` on both).
Only `weights_sha256` differs, which is expected since the merged
safetensors file's header/data byte layout is a build artifact of the merge
process, not of tensor content — the fixed kernel's self-check confirms
tensor content is contiguous and in write order, but the exact byte offsets
Kaggle produces are not required to match box1's independently-built merge
byte-for-byte.

## Phase 2 (1.5B control) — verbatim result lines

```
weights_sha256=6f3a62caedc5c5278275bf5eed428806eeac8df927a3d333c3c850402c24cdeb
tokenizer_sha256=f7c9b2dba4a296b1aa76c16a34b8225c0c118978400d4bb66bff0902d702f5b8
config_sha256=f8c6c681f7c28386e333775bb78de28f9de3ce6a676059dc35792022adcb7e36
table_digest=23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d
inv_freq_table_digest=02908dae2c15329014dd986fec8033e03427fba0935b04b864ab2bc75fe3bc44
prompt_idx=0 prompt_tokens=[12522, 5193, 264, 882]
prompt_idx=0 run1_tokens=[12522, 5193, 264, 882, 11, 1052, 572, 264, 2632, 3743, 879, 10245]
prompt_idx=0 run2_tokens=[12522, 5193, 264, 882, 11, 1052, 572, 264, 2632, 3743, 879, 10245]
prompt_idx=0 run1_witness_digest=9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8
prompt_idx=0 run2_witness_digest=9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8
prompt_idx=0 run1_argmax_digest=bbc7a8447acb5ee40cc1e9660d77c34e52dcf5f635f41cd54a934c64a717cbd4
prompt_idx=0 run2_argmax_digest=bbc7a8447acb5ee40cc1e9660d77c34e52dcf5f635f41cd54a934c64a717cbd4
prompt_idx=0 runs_identical=true
prompt_idx=0 reduction_mode=sequential
CIS2_REF digest=9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8 prompt_idx=0 prompt_toks=4 gen_toks=8 dtype=fp32 reduction_mode=sequential
```

The 1.5B digest `9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8`
matches the "known LLM-4 digest" cited in `LLM5B-LOG.md` and reproduced
identically by cis3-0k's 1.5B control run (1.5B path is unaffected by the 7B
merge bug, as expected — it doesn't go through the shard-merge code path).

## Verdict

All 31 `LAYER_DIGEST` labels (embed, block_0..block_27, final_norm, logits)
are bit-identical between box1 and this fixed-merge Kaggle rerun, and the
generated token sequence and `argmax_digest` are also bit-identical. The
overall `witness_digest`/`CIS2_REF digest` still differs
(box1 `a4a6770e...` vs Kaggle `7752994d...`), and `weights_sha256` differs as
expected from differing merged-file byte layout. Per the task's fixed
wordings, this result is neither "all 31 layer digests and the witness match
box1" (witness does not match) nor a "first diverging label" case (no label
diverges) — reporting the observation as-is rather than forcing it into
either template. No EXPECTED digest anywhere was edited.

PROPOSAL: none — a re-pin proposal was contingent on the witness digest
matching box1's `a4a6770e...`, which it does not; this needs operator/Justin
investigation into why the witness digest differs from a per-layer-identical,
argmax-identical run before any re-pin is considered.
