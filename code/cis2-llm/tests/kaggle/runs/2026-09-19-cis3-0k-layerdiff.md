# cis3-0k: Kaggle per-layer digests vs box1 (H3 cross-host diff)

Published 2026-10-16 as part of the CIS-2 archive. Leg cis3-0k. Goal: reproduce box1's H3 per-layer digest run
(Qwen2-7B, cis2-fp `--layer-digests`) on a CPU-only Kaggle kernel at the
same cis2-fp commit as box1's run, then diff every `LAYER_DIGEST` label to
find the first layer at which box1 and Kaggle disagree.

## Engine build

- cis2-fp commit: `c0a2c346430c34dd54c9c0adc78829beb8755d32` (branch
  `cm/cis3-0k`, worktree of `origin/cm/llm8b-stream`).
  - This commit is a descendant of `3530cc17331fcc5ea81bcf47d40526a454b4717f`
    (adds `--layer-digests`) — confirmed via
    `git merge-base --is-ancestor 3530cc1 c0a2c34` (rc=0).
  - box1's H3 log (cis2-fp commit `8326397`,
    `docs/hardware_logs/llm8b_7b_layerdigests_aefinity-box_2026-09-19.log`)
    was built at the same `3530cc1` tag line; the only diff between that
    commit's parent and `c0a2c34` is a cosmetic log-append marker — no
    functional engine change between the two builds.
- Kaggle private dataset: `aefinityaiinc/cis2-fp-engine-cis3-0k`
  (https://www.kaggle.com/datasets/aefinityaiinc/cis2-fp-engine-cis3-0k),
  packaged from the `c0a2c34` worktree via `kaggle datasets create -p <dir> -r zip`.

## Kaggle kernel

- Kernel: `aefinityaiinc/cis3-0k-layerdigests`
  (https://www.kaggle.com/code/aefinityaiinc/cis3-0k-layerdigests), version 1,
  CPU-only, private, internet enabled.
- Script: copy of the LLM5B/LLM5c kernel script
  (`kaggle kernels pull aefinityaiinc/llm5b-scale-kaggle`), patched only to:
  - point `ENGINE_SRC_NAME` at `cis2-fp-engine-cis3-0k`
  - print `ENGINE_COMMIT=c0a2c346430c34dd54c9c0adc78829beb8755d32`, `free -h`,
    `nproc`, `uname -a`, `df -h /kaggle/working`, and `lscpu` avx2/avx512/fma
    flags before the build
  - pass `--layer-digests` on the 7B `cis2_ref` invocation only (1.5B control
    runs unchanged, `layer_digests=False`)
- Exact 7B command (from `run_cis2_ref(binary, q7_weights, GEN_TOKS_7B, "7B", layer_digests=True)`):
  ```
  cis2_ref --weights-dir <staged Qwen2-7B weights dir> --gen-toks 4 --layer-digests
  ```
- Push/poll: pushed once, no retry needed. Poll log
  (`kaggle kernels status aefinityaiinc/cis3-0k-layerdigests`, ~5 min interval):
  ```
  2026-09-19T07:30:39Z aefinityaiinc/cis3-0k-layerdigests has status "KernelWorkerStatus.RUNNING"
  2026-09-19T07:35:46Z aefinityaiinc/cis3-0k-layerdigests has status "KernelWorkerStatus.RUNNING"
  2026-09-19T07:41:10Z aefinityaiinc/cis3-0k-layerdigests has status "KernelWorkerStatus.RUNNING"
  2026-09-19T07:46:15Z aefinityaiinc/cis3-0k-layerdigests has status "KernelWorkerStatus.COMPLETE"
  ```
  Ran RUNNING -> COMPLETE in ~16 min, consistent with LLM5B/LLM5c timing.
- Raw log retrieved via the Kaggle Python API (`KaggleApi().kernels_logs(...)`,
  the CLI's `kernels output` only fetches dataset/build artifacts, not stdout —
  same known limitation documented in `tests/kaggle/LLM5B-LOG.md`). Saved
  verbatim (JSON array of `{stream_name,time,data}` entries, 977 entries) as
  `tests/kaggle/runs/2026-09-19-cis3-0k-kernel.log`.

## Environment (from the kernel's printed environment block)

```
$ bash -c free -h; nproc; uname -a; df -h /kaggle/working; lscpu | grep -i flags | tr " " "\n" | grep -Ei "^(avx2|avx512|fma)" | sort -u; echo ENGINE_COMMIT=c0a2c346430c34dd54c9c0adc78829beb8755d32
               total        used        free      shared  buff/cache   available
Mem:            31Gi       420Mi        28Gi       1.0Mi       2.3Gi        30Gi
Swap:             0B          0B          0B
4
Linux bc97e9ac9382 6.12.90+ #1 SMP Sat May 30 15:40:53 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
Filesystem      Size  Used Avail Use% Mounted on
/dev/loop1       20G  144K   20G   1% /kaggle/working
avx2
fma
ENGINE_COMMIT=c0a2c346430c34dd54c9c0adc78829beb8755d32
```

box1's H3 log does not itself print an equivalent `free -h`/`lscpu` block
inline (only the leg header + commit line), so a side-by-side environment
table beyond CPU-feature inference is not possible from these two logs alone.

## Diff method

A small Python script (`tests/kaggle/runs/2026-09-19-cis3-0k-layerdiff.py`,
also archived at
`<tmp>/<session>/scratchpad/layerdiff.py`)
parses `LAYER_DIGEST <label> <hex>` lines out of both raw logs (box1's
`docs/hardware_logs/llm8b_7b_layerdigests_aefinity-box_2026-09-19.log` from
cis2-fp commit `8326397`, and this kernel's parsed log) and compares label by
label in file order. Script output, verbatim:

```
box1 LAYER_DIGEST count: 31
kaggle LAYER_DIGEST count: 31

label          status box1_digest / kaggle_digest
----------------------------------------------------------------------------------------------------
embed          DIFF   box1=20d1c3114f5af59661f1d30c60e45d3d220cd9cceff7c7cb19fc4924b69cd416
                      kagl=38e87ad1ec58e68ce6a8586a59f5f37c983b3718edb5fe8783b77d41f70f784c
block_0        DIFF   box1=b62ef72537abbda08442ec68b8349a8d52c3eb7cb452447358a43cfe2dc23aa5
                      kagl=06f8d7ea601cc9674dd7c0ffde56589ba7ed2b5705320c5cadf3c52cdc9bb5e5
block_1        DIFF   box1=a2cc20831a8dc837a570d10a67cc6608f6eefcca8e9248474eeed7c5c80f1909
                      kagl=e146a4e136aba43de0e44f7002742e49cb3a4b578a92c71258de988c2d68163f
block_2        DIFF   box1=4e6dcc65d55d3efd21a04438081a4063efae3cad215fd718e4c31a9522d1344f
                      kagl=54e7e0a8cd2f59f1e2c717a2d579132d8279004a664e8bc8779032f61a6c80b2
block_3        DIFF   box1=443ad0746320603624af67330fedcf74c2a25272bbe0439f3fdf0b71c7faa278
                      kagl=f06d3416219ace2d6286702a64a8685e4ce34c0a75887540a9262f9e56f06752
block_4        DIFF   box1=a98a54d7c4532916ff04f4570482d1e3e247c0d5d0b3e5c4882cb39f7ba3e3a7
                      kagl=ef62f2e0d59f5a39feb551f9da16bd7277b119d808e9430290b4e39e4aa06e74
block_5        DIFF   box1=3c5dc16e6503405e63a29dce215154991acb8fc29f1a6e67cc27ff6a52618d1d
                      kagl=05e879ef99e01a0f6ad5acc62e360225de0f0224223e010d1fcbf451c1ee26dc
block_6        DIFF   box1=73108bd54eeb56315441b375ed5b596796f6c8acdc138114c97c87518f5843b1
                      kagl=0ce3ec1185c6b72b88bd105e62a56216bca229b5fc2004b06d6db082c0b02d61
block_7        DIFF   box1=fedc90c2fd17bb45f4fa2c0d415658ecb716f037d763884ea61c2d8c75c06b16
                      kagl=7cd525b5e97fdf7ab675ff0246b8105bc545c3977a05a03b6e37b2327af3cef0
block_8        DIFF   box1=d12a46e22296606f0274f9f7a80c7f98c8b0c6fb90306f57092845697075567f
                      kagl=6a44eccb40c24aa65083cf82050e0c20cc8e0684cfc54a97e79a0c1ab471b949
block_9        DIFF   box1=31461e2b932b2bb75b881a3f9156b02a6e89244831b2405e348066f303c92d5d
                      kagl=4421354038c0c54340ce1d5a8858753404832eb0e7fb73d2e8ccaf25e6e5fc2c
block_10       DIFF   box1=0ef7caac10b4661d5519713378a9bc2fa2f699aa95da036cc44953f257355f28
                      kagl=c151ae76468f87e6bf44dd1b23bffee212569b931ed19c00df12d54dfd8a0a17
block_11       DIFF   box1=cb8827a5da643087a64e193b63a570aa56340555b98bd48253878de5daa9caeb
                      kagl=43dc14684e44316c54bbb73f000848e943d0e8feb2bad28d12d96d5d1b5b8778
block_12       DIFF   box1=3687ab01ba2e8f5224e8aae417b87228ca1d76b477676e133e1702708fd9003e
                      kagl=10140ec4626cce158b116d4783bd30908a7a6122209c03cdb20a45974829597b
block_13       DIFF   box1=a791fa976435ef6c6523c1f54d103059b8f7ee589d6c2bd001c3c15d2586c9e5
                      kagl=70b845bc165194f5d3553afca76d33cffe2448616dce79b0876c3ff1888950c5
block_14       DIFF   box1=84f2885eec84f38b4cf4e641217588c4a2b0e391eabbb3a395499fcba0e983a2
                      kagl=ffda1c0c1f1d57f728a87d42127ea12ce6f60fdc52dee9231f4201ba2ccc9bac
block_15       DIFF   box1=e80116e25956b323b95f4f10fcb452e6a19e90ce340d2c5c45b69389afa5035c
                      kagl=73a1ec64758039f5686c1c830743d53620c5a6866fcf54d95aa86c405bb3f354
block_16       DIFF   box1=8b2ebdd363e41b713b563f904ad068ef90652465a0ec442a12375947ef28dcb1
                      kagl=d069a4df805bcaa8884a89e6e0a1e49f071a8171ef10b9a1972d05c8319ade86
block_17       DIFF   box1=d3ecfa6c24ca82c911279f838dc6d14a0501de891b9cd780f427ab2f01e03c34
                      kagl=9593204c31ba27b778307080ebb740733ee73558597c7a473358d7592aa0a9aa
block_18       DIFF   box1=4bd660746cffa6641629702549d25e35fbb1536d0d0fad1fa1227cc25c9da6a8
                      kagl=520c587080d6c4da7090f6e15ca606d277e8eb99142421dab8ef7465531a0746
block_19       DIFF   box1=a3dd6400e6ca62bfb42ae4824b1b1e03ea8f6dfea9a7bddbc676c78395e626e0
                      kagl=aafe261b479696b11532c055e7af5909ef9b75e2f3815e28921863aa18cd52db
block_20       DIFF   box1=7b171eec2c0355f118a36922dc809569486c5cc73b527d03fd7e27f21851770c
                      kagl=9e383eeb2e1d1237ebc9896946e19d3d407e50e0f9b152c1bc942feb0c0936c2
block_21       DIFF   box1=71a618e7fc4d4518988e090f33931a302521c664d0a7c21a9e41625885881908
                      kagl=f6a408c4bd86ec63f4678762f59ffdf0e3a938f9eee93da317eaaae960d93fda
block_22       DIFF   box1=68abc10432f83af0b600db15061607d71b7bc659c17a6a9b62778df1e3d2207d
                      kagl=19d49fa3e682e6e3b997c65f3c627cea54c89c3dbf143a237067a040d5f275fe
block_23       DIFF   box1=53b24c6deaebb1762cbbc82ceaf7ce8fa37c760214eed9e8a81100ad3b825124
                      kagl=9730eec95e4b494b1b1a9e076529cb4883f1cf1863fb069a1a103d2e05547eb5
block_24       DIFF   box1=afbb187dedc45ca9a5c62a3a0aa6ac07d8e2bf67e60a3c4698de966432e15343
                      kagl=653985da69d21943c0e0d59f921d2b211b5daa396627e103d1b6744187f302c2
block_25       DIFF   box1=35fbd3afbf78d3530b15eb07568478049f40a8daa5b95b512810223d3072cb0a
                      kagl=2d81462fc4c187fe5f3eff9edfb7066156441c4876817673dac52c55d76050a3
block_26       DIFF   box1=5ffad7dd3d795659642cdc1479bf058c25e610f3b2291fe7481d895844a56ad7
                      kagl=109ca7621f6b34d345794676370fae9159fd5a028fece6fc2451289348f66ed4
block_27       DIFF   box1=e3117c5b404be9e1cd17b7759b6983f1e26bd7e2cda4c7c3b914dc753ed06a44
                      kagl=297f5e5e4ff316bf326ef9a193aff8d811b2b5a623e2f2887046926b217c1b1d
final_norm     DIFF   box1=c56066fa9594801fbf6fee2ca925a39977ad8041335a323989c1808521b477d2
                      kagl=f314cc88513b7b47059098dcb671d6a300f00683018481d81683ed11b65c7597
logits         DIFF   box1=e24e704bfdd04f10fdec91307e013f238d0d207b421f6e441ac2a6fa65780073
                      kagl=325d49f73056cda45871c61850e6d3a10cf43b3a7cb3e1411e8f295d3d0a3a5f

FIRST_DIVERGING_LABEL: embed
```

## Result

**First diverging LAYER_DIGEST label: `embed`** — every one of the 31 labels
(embed, block_0..block_27, final_norm, logits) differs between box1 and
Kaggle for this 7B run. There is no matching prefix; the divergence is
present at the very first instrumented stage.

## Final digests

| field | box1 (`8326397`) | Kaggle cis3-0k | LLM5B / LLM5c (prior Kaggle) |
|---|---|---|---|
| `weights_sha256` | `13200c88e7482d83ed9a2bb23a01b515e46663ab57dba853389587d4173dcfa3` | `0e218d281ea2c86c281db9cc6491f4a37ef7b931e57cd63b70cde999bce265ee` | matches Kaggle (`0e218d28...`, same value box1's own `KAGGLE_MERGED_SHA` constant anticipates) |
| `tokenizer_sha256` | `f7c9b2dba4a296b1aa76c16a34b8225c0c118978400d4bb66bff0902d702f5b8` | same | same |
| `config_sha256` | `d318b49c4a29771e259d93053084eb752f5bfe69c20c4f2e041bd1017884f810` | same | same |
| `table_digest` | `23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d` | same | same |
| `inv_freq_table_digest` | `02908dae2c15329014dd986fec8033e03427fba0935b04b864ab2bc75fe3bc44` | same | same |
| `prompt_tokens` | `[12522, 5193, 264, 882]` | same | same |
| `run1_tokens`/`run2_tokens` (generated) | `[..., 11, 1052, 572, 264]` | `[..., 1305, 1305, 3811, 3811]` | Kaggle run matches LLM5B/LLM5c's own prior generated tokens |
| `witness_digest` (final) | `a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3` | `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a` | matches LLM5B and LLM5c exactly |
| `argmax_digest` (final) | `a8ed47fb9cca7b6ac1830fc12a18ebb9615b77e29b012f8c036ce7cb0183c265` | `67f771c526de272cdf8bf22b6804edfca820cee2df9d6d9b68712e27cb43d284` | matches LLM5B/LLM5c (`67f771c5...`) |
| `runs_identical` | `true` | `true` | `true` |

- Kaggle's final 7B witness digest, argmax digest, and generated tokens are
  bit-identical to both prior Kaggle runs (LLM5B and LLM5c) — this is the
  **third** same-platform Kaggle reproduction of `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a`.
  Consistent with the standing wording: reproduced twice on Kaggle, box1
  divergent under investigation (now reproduced a third time on Kaggle).
- 1.5B control runs on this kernel (no `--layer-digests`) reproduced the
  known digest `9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8`
  on both the "second run" invocation and a repeat within the same kernel
  (lines 850 and 915 of the parsed log — same digest both times).

## Limitations / honest caveats

- **`weights_sha256` already differs** between box1 (`13200c88...`) and
  Kaggle (`0e218d28...`) before any layer digest is computed. box1's own
  `scripts/run_llm8b_7b.sh` (commit `c0a2c34`) already anticipates and names
  the Kaggle-side value via a `KAGGLE_MERGED_SHA` constant, i.e. this is a
  known, expected difference tied to box1's streamed per-layer bf16->fp32
  widening (`--stream-weights`, used because box1 is RAM-constrained) versus
  Kaggle's whole-buffer merge-then-widen path (the LLM5B/LLM5c recipe, not
  modified for this kernel). **This run does not isolate the weight-loading
  path from the compute path** — box1 and Kaggle differ in both
  simultaneously, so "first diverging layer = embed" should be read as "the
  divergence is already fully present by the time the embedding lookup
  digest is taken," not as evidence that the transformer compute kernels
  themselves diverge from a shared, identical set of weight bytes. This is
  exactly the H3 hypothesis under investigation (stream-weights vs
  non-streamed loading), and this run is consistent with it but does not
  prove it — a same-loading-path-on-both-sides run (e.g. Kaggle built with
  `--stream-weights` too, or box1's own streamed-vs-non-streamed digests on
  the same machine) would be needed to separate the two variables.
- The generated-token difference (box1 `[..., 11, 1052, 572, 264]` vs Kaggle
  `[..., 1305, 1305, 3811, 3811]`) is a downstream consequence of the
  logits-digest divergence already present at `embed`, not a separate
  finding.
- No new pinned EXPECTED digest was modified; this is a diagnostic diff only.
- Environment: no equivalent `free -h`/`lscpu` block exists in box1's H3 log
  for direct side-by-side environment comparison — only Kaggle's environment
  is captured verbatim above.
- Wording for the 7B result stays: "reproduced twice on Kaggle, box1
  divergent under investigation" (now a third Kaggle reproduction, still
  divergent from box1).
