# `gpu/EXPECTED_DIGESTS.md` — pinned CIS2_REF digests, C++ port vs Rust reference

Published 2026-10-16 as part of the CIS-2 archive. One table, all model families this
port has been run against, all on CIS-2 **v0.3b** (the spec this branch
targets — see `docs/CIS2_SPEC_v0.3b.md` / `docs/E15m_RESULT.md`). Do not
compare these against the v0.2 digests recorded in
`docs/E15d_v0.2_DIGESTS.md` — the v0.2 → v0.3b RoPE / `reduce_pi_2` fix
(README §4.10) changes every digest.

| model | params | prompt | gen_toks | `CIS2_REF` digest | runners |
|---|---|---|---|---|---|
| SmolLM2-135M | 135M | "Once upon a time" | 16 | `d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` | x86_64, aarch64 (`e18b-cpp-cross-isa.yml`) |
| SmolLM2-135M | 135M | "Once upon a time" | 128 | `22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6` | x86_64 (host, this box) |
| Qwen2.5-0.5B | 0.5B | "Once upon a time" | 16 | `c9dff099d927a6dda91514c260c7207de7aca4b361291e57fae390a352392e62` | x86_64, aarch64 (`e18b-cpp-qwen.yml`) |
| Qwen2-7B | 7B | token ids [12522, 5193, 264, 882] | 4 | `a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3` | box1 CPU + Kaggle CPU `cis3-0n-bytemerge` v3; merge recipe `scripts/merge_shards.py` @ c0a2c34 (re-pinned 2026-10-16, `ERRATA.md` E-1; 1501ed47... retired) |

Qwen2.5-0.5B config (from `weights_qwen/config.json`, sha256 pinned in the
workflow): `hidden_size=896`, `num_attention_heads=14`,
`num_key_value_heads=2` (GQA group=7 — SmolLM2's group=3 never exercises
this ratio), `num_hidden_layers=24`, `intermediate_size=4864`,
`vocab_size=151936`, `rope_theta=1000000.0`, `rms_norm_eps=1e-06`,
`tie_word_embeddings=true` (so `lm_head` is `nullptr`, tied to
`embed_tokens` — same code path as SmolLM2, but this is data-driven from
config, not hardcoded), and the checkpoint carries `self_attn.{q,k,v}_proj.bias`
tensors (SmolLM2's do not) — also data-driven (`Cis2SafeTensors::has`),
exercising `k_add_bias` for the first time on real weights.

Weight fetch (sha256-pinned, matches `.github/workflows/e18b-cpp-qwen.yml`):

| file | sha256 |
|---|---|
| `config.json` | `479dcf0c5286339e41ad3992cd08ae88a467c4187587936248e2b7c96283484b` |
| `tokenizer.json` | `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539` |
| `model.safetensors` | `88c142557820ccad55bb59756bfcfcf891de9cc6202816bd346445188a0ed342` |

No C++ source changes were needed to run Qwen2.5-0.5B through this port —
the untied-lm_head, GQA (`kv_head = qh / group`), and QKV-bias paths were
already present and generic (coded on `cm/e18b-cuda-portable` but, per the
old §1 status line, never exercised on real Qwen weights until this run).
One build-infra fix was needed: `gpu/Makefile`'s `gate`/`gate-128` targets
passed `--weights-dir $(WEIGHTS)` to the C++ binary but not to the Rust
reference, which silently defaulted to `./weights` (SmolLM2) — fixed to
pass `--weights-dir` to both. No arithmetic changed.

Result: x86_64 and aarch64 both produced `CIS2_REF digest=c9dff099...` for
Qwen2.5-0.5B, gen_toks=16, C++==Rust on each runner and the two runners'
digests and 16-token traces byte-identical to each other. See
`gpu/README.md` "Second model" section for the CI run URL.
