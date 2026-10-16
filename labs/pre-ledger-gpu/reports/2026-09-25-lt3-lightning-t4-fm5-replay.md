# lt-3: Lightning AI T4 replay of the fm-5 deterministic-KD run (second GPU host)

Leg: lt-3 (FRONTIER-1). Published 2026-10-16 as part of the CIS-2 archive. Date: 2026-09-25. Source files (read,
not modified): `~/projects/alice-model-cm-fm5/experiments/{fm5_kd_determinism.py,
run_fm5_twice.sh, fm5_corpus_smoke.txt}`, branch `cm/fm5-deterministic-kd`,
commit `0730db41c66e6b199aa6080894a12520202149cb`. Runner:
`~/projects/claudius-maximus/bin/cm-lightning-run.py` (read for credentials/
Studio-connection convention; a small standalone script using the same
`lightning_sdk` API plus `Studio.upload_file`/`download_file` was used for
this leg so file transfer and start/run/stop could be wrapped in one
try/finally). Studio: `scratch-studio-devbox`, teamspace/org from
`<private-config-path>` (not printed).

Full raw run log (upload progress bars, host facts, install output, full
`run_fm5_twice.sh --full` stdout, download confirmations, stop
confirmation): `state/reports/fm5-logs/2026-09-25-lt3-lightning-t4.log`.
Manifests fetched from the Studio:
`state/reports/fm5-logs/2026-09-25-lightning-cache_manifest.json`,
`2026-09-25-lightning-run1-train_manifest.json`,
`2026-09-25-lightning-run2-train_manifest.json`. Kaggle-side manifests
(already in repo from the prior leg) used for comparison:
`state/reports/fm5-logs/2026-09-25-kaggle-cache_manifest.json`,
`2026-09-25-kaggle-run1-train_manifest.json`,
`2026-09-25-kaggle-run2-train_manifest.json`.

## Procedure

1. Connected to `scratch-studio-devbox` (status `Stopped`), started it on
   `Machine.T4` (116s to reach `Running`).
2. Uploaded `fm5_kd_determinism.py`, `run_fm5_twice.sh`,
   `fm5_corpus_smoke.txt` via `Studio.upload_file` to `~/fm5/experiments/`
   on the Studio (files not modified from the source branch).
3. Recorded host facts (`nvidia-smi -L`, `nvcc --version`, driver version).
4. Installed `torch` from `https://download.pytorch.org/whl/cu128` and
   `transformers`/`numpy` via pip (Kaggle used its stock pre-installed
   image; Lightning required an explicit install — versions differ, see
   table below, recorded as a known deviation).
5. Downloaded the corpus (`curl -sSL
   https://www.gutenberg.org/cache/epub/1661/pg1661.txt`) directly on the
   Studio and verified its sha256 against the expected
   `922e2a12ccb43a4c9544c260b2166c6ad2097aeb5957faeee113f173bb857cd0`
   before proceeding — **matched**.
6. Ran `bash run_fm5_twice.sh --full` with `FM5_CORPUS`, `FM5_TEACHER=
   HuggingFaceTB/SmolLM2-360M`, `FM5_OUT_ROOT=$HOME/fm5/artifacts`,
   `PYTHON_BIN=python3` — this runs `--phase cache` once, `--phase train`
   twice (run1, run2), then the script's own built-in `--phase compare`.
7. Downloaded the three manifests (`cache_manifest.json`,
   `run1/train_manifest.json`, `run2/train_manifest.json`) back to
   penguin via `Studio.download_file`.
8. Stopped the Studio in a `finally` block (runs on both success and
   exception paths). Independently re-checked `st.status` afterward from
   a fresh script: `Stopped`.

## Args (identical to the Kaggle run, from its manifests)

k=64, seq_len=256, steps=200, batch=8, teacher=`HuggingFaceTB/SmolLM2-360M`,
seed=20260925, data_order_seed=20260925, student_init_seed=20260925,
lr=0.0003, weight_decay=0.01, temperature=2.0, ce_weight=0.0,
loss_fn_id=`forward_kl_T2.0`, shuffle=false, smoke=false, corpus=
`pg1661.txt` (sha256 `922e2a12ccb43a4c9544c260b2166c6ad2097aeb5957faeee113f173bb857cd0`).

## Host / version facts

| | Kaggle T4 (2026-09-25, prior leg) | Lightning AI T4 (this leg, lt-3) |
|---|---|---|
| GPU | Tesla T4 (`gpu_name` in manifest env) | Tesla T4 (`nvidia-smi -L`) |
| Driver | not captured in Kaggle log | 580.178.04 |
| nvcc | not captured in Kaggle log | release 13.0, V13.0.88 |
| torch | 2.10.0+cu128 | 2.8.0+cu128 |
| CUDA (torch.version.cuda) | 12.8 | 12.8 |
| cuDNN | 91002 | 91002 |
| transformers | 5.0.0 (student_config.transformers_version) | 5.17.0 |
| OS/image | Kaggle stock GPU image | Lightning Studio (AWS-backed Ubuntu) |

torch/CUDA-toolkit-minor and transformers versions differ between hosts
(Kaggle's stock image vs an explicit pip install on Lightning); this is
an expected deviation, not something pinned to match, and is the leading
candidate explanation for the cross-host digest mismatches below.

## Digest table

| field | Kaggle T4 | Lightning T4 | cross-host |
|---|---|---|---|
| corpus_sha256 | 922e2a12ccb43a4c9544c260b2166c6ad2097aeb5957faeee113f173bb857cd0 | 922e2a12ccb43a4c9544c260b2166c6ad2097aeb5957faeee113f173bb857cd0 | MATCH |
| tokens_sha256 | 140e9dac6ad6380dd9cee667ec6e9beffec1297ec2e5cc344fcd33efc31b72a9 | cdafa568231b2c821af5bc6b0847670f7b630e05472f382e94778d52aee5a1b8 | MISMATCH |
| teacher_logit_cache_sha256 (cache_artifact_sha256) | 493f042d59535cc7b68baeadd4d3f81d4112aa3341260af682ae3bc0a4ea4d23 | 762950c88abd96905b7a7949bdbbae1d52030266029143438ad203f63b119662 | MISMATCH |
| tokenizer_hash | 33b7dd0ab4327c920591a9b8d479821d62d9585690dabe107eff2c8b8892cf23 | 33b7dd0ab4327c920591a9b8d479821d62d9585690dabe107eff2c8b8892cf23 | MATCH |
| student_arch_config_hash | 32c99a43036a750b10ffd5e6cdd4fd83398bd531e089b0b97d24737ab9ff20f3 | a5b93db618e1488d4a26145f4ce47f6d7ee98060b5910f38020065cb60ecad7c | MISMATCH |
| checkpoint_raw_param_sha256 | 167074c43f0efdc6afe406982162ab93ab95b5e831e1ff26898a438aee2041ca | cc4b951ae93c2b1528c5c1df30914254ec2e61b043eb36c4f458a0dd42c59b12 | MISMATCH |
| checkpoint_file_sha256 | c022c8a3773e7c01a05daebab81fec908071f3645920fd2560ee43c57f51ca18 | a1cbab044bcd220b1860f002a2d4fd4f1d9327690b6f01f4d6a5232c1d61d31c | MISMATCH |

`student_arch_config_hash` differs even though every architecture
hyperparameter in `student_config` (hidden_size=576, num_hidden_layers=30,
num_attention_heads=9, num_key_value_heads=3, intermediate_size=1536,
vocab_size=49152, etc.) is identical between the two hosts — the only
differing field inside `student_config` is `transformers_version`
(`5.0.0` vs `5.17.0`), which is included in the hashed struct. So this
particular MISMATCH is explained by the transformers-version string
itself, not by an architecture difference.

`tokenizer_hash` (a hash of the tokenizer's own files/config) MATCHES
across hosts, yet `tokens_sha256` (the hash of the actual tokenized
corpus, `(616, 256)` int64 ids both sides — `n_blocks=616`, `seq_len=256`
on both) does NOT match. Same tokenizer identity, different tokenized
output bytes on this host pair — not diagnosed further in this leg (would
require diffing the actual token arrays, not done here).

## Same-host determinism (Lightning run1 vs run2)

| field | run1 | run2 | verdict |
|---|---|---|---|
| checkpoint_file_sha256 | a1cbab044bcd220b1860f002a2d4fd4f1d9327690b6f01f4d6a5232c1d61d31c | a1cbab044bcd220b1860f002a2d4fd4f1d9327690b6f01f4d6a5232c1d61d31c | MATCH |
| checkpoint_raw_param_sha256 | cc4b951ae93c2b1528c5c1df30914254ec2e61b043eb36c4f458a0dd42c59b12 | cc4b951ae93c2b1528c5c1df30914254ec2e61b043eb36c4f458a0dd42c59b12 | MATCH |
| teacher_logit_cache_sha256 | 762950c88abd96905b7a7949bdbbae1d52030266029143438ad203f63b119662 | 762950c88abd96905b7a7949bdbbae1d52030266029143438ad203f63b119662 | MATCH |

`run_fm5_twice.sh`'s own `--phase compare` step printed
`OVERALL: MATCH` (all three fields MATCH), reproduced verbatim in the log.

## Overall verdict

- **Same-host (Lightning run1 vs run2): MATCH** on all three digest
  fields — the deterministic-KD recipe reproduces bit-for-bit on this
  second GPU host, same as it did on Kaggle in the prior leg.
- **Cross-host (Lightning vs Kaggle): MISMATCH** on every digest that
  depends on tokenization, the teacher-logit cache, or the trained
  checkpoint. Corpus bytes and tokenizer identity match; everything
  downstream of tokenization does not. This is an expected possible
  outcome given the torch (2.10.0+cu128 vs 2.8.0+cu128) and transformers
  (5.0.0 vs 5.17.0) version differences between the two hosts — not a
  finding about the recipe's correctness, and not re-run or re-pinned to
  try to force a match.

## Not verified

- No independent check of *why* `tokens_sha256` differs (e.g. whether
  transformers 5.0.0 vs 5.17.0 changed default tokenizer normalization or
  special-token handling for this model) — would need a targeted diff of
  the token arrays themselves, not attempted here.
- Lightning credit balance was not queryable via the SDK (`--balance`
  returned a 403 from the billing endpoint, and the standalone script
  used here doesn't call it either); wall time with the Studio in a
  `Running` state was approximately 5 minutes (T4 start ~116s + upload/
  install/run/download/stop), well under the 30-minute internal budget
  bound used for prior Lightning legs.
- No throughput/timing numbers are reported in prose per Rule A; the wall
  time figure above is session-accounting only, not a benchmark claim.


## Root cause (penguin diagnostic, 2026-09-25 10:50Z, Fable)
Tokenized the identical corpus bytes (pg1661.txt, sha256 922e2a12…, 12,310 CRLF line endings, no lone LF) on
penguin with the two transformers versions the hosts used. Same HF tokenizer files, same vocab hash.

| transformers | tokenizer class | token count | occurrences of token 2738 ("\r\n") |
|---|---|---|---|
| 5.0.0 (Kaggle image) | TokenizersBackend (fast) | 157795 | 30 |
| 5.17.0 (Lightning pip) | GPT2Tokenizer (fast) | 157822 | 23 |

Token counts equal the two hosts' own counts (157795 on Kaggle, 157822 on Lightning), so the penguin
diagnostic reproduces the divergence. The delta is 27 tokens. Only 7 of them are explained by the merged "\r\n" token 2738 (30 occurrences under 5.0.0 vs
23 under 5.17.0); the remaining 20 come from other CRLF-adjacent merges that were not itemized (e.g. punctuation+CRLF
or double-CRLF merges). The short probe string "a\r\nb" splits in BOTH versions, so the difference is context-dependent
pre-tokenization/merge behaviour between the two tokenizer backends, not a vocab change. First divergence at token index 73705. Both counts floor to 616 blocks of 256,
which is why n_blocks matched while tokens_sha256 did not.

Consequence: the cross-host comparison of GPU training math is UNTESTED by lt-3 — the inputs differed before the
first matmul. Fix (fm-5c): the fixture becomes the token-id tensor (shipped + hashed), and the transformers
version is pinned and recorded in the cache manifest as a first-class field. Design lesson for CIS-2 training
receipts: hash the token tensor AND pin the tokenizer *implementation* version, not only the vocab.
