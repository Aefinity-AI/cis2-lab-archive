# Bit-identical fp32 inference on a shipped corporate checkpoint, two ISAs — 2026-09-08

**Result.** Alibaba's shipped **Qwen2.5-0.5B-Instruct** checkpoint replays **bit-identically** on two x86
machines with different instruction sets, using the CIS-2 fp32 reference engine with **no code changes**.
5 prompts x 32 generated tokens, all 5 CIS2_REF digests identical, rollup digest identical, and
`runs_identical=true` 5/5 on each box (the engine's own run1-vs-run2 self-check).

| | box1 | box2 |
|---|---|---|
| CPU | Intel i5-5200U (Broadwell) | Intel Celeron N4020 (Gemini Lake) |
| ISA | AVX2 + FMA | SSE4.2 only — **no AVX2, no FMA** |
| rc | 0 | 0 |
| rollup of the 5 digests | `6dd161a99f3f946b89a4e537162c3eafe007c19b9c275d2a163950173d7f7874` | **same** |
| peak RSS | 2,899,136 kB | 2,897,656 kB |

Per-prompt CIS2_REF digests (identical on both boxes):

| prompt_idx | prompt_toks | gen_toks | digest |
|---|---|---|---|
| 0 | 4 | 32 | `00b21701cd1f2f9dacfe4111adc73085818f8cc9c9d57651bf816870a504434b` |
| 1 | 11 | 32 | `3c1a6985452d81c2d236727ece6d99116e6b16e02dbb982c6477d904112b087f` |
| 2 | 11 | 32 | `785d538014569ef1c4a1cdf12ea4821297f4352652386bfdc008b91051a22352` |
| 3 | 18 | 32 | `2f57851c1f9fb8d9f3d6b39aa3248313c15e84c4e069f2b7e7042938740f3420` |
| 4 | 221 | 32 | `d7130fbd609deedfc17dce57c5b1a3744d2220a9590e57364e75acf8b784a792` |

**Why this one matters.** Prior CIS-2 cross-ISA results were on SmolLM2 and on a 2-token Qwen probe. This is a
real vendor-shipped instruct checkpoint, a 221-token prompt, and 32 generated tokens per prompt — long enough
that any reduction-order or FMA-contraction difference between the two ISAs would have diverged. It did not.

## Measured blocker (this run)

Peak RSS **2.90 GB for a 988 MB bf16 file — a 3.0x blow-up**. The loader does `std::fs::read` of the whole
file (`src/main.rs:569`) and widens every tensor into a separate fp32 `Vec` before dropping the raw buffer.
Computed from staged file sizes: Qwen2.5-1.5B-Instruct (2.9 GB file) needs ~8.7 GB peak and
Falcon3-1B-Instruct (3.2 GB) needs ~9.6 GB — **neither fits box1 (5.7 GB) or box2 (3.7 GB)**. Anything above
~1B parameters is blocked until the loader mmaps or streams. This is the single gating engineering item for
scaling to larger corporate models.

## Provenance (Rule B)

- Engine: `cis2-fp` main `0f27277`, cargo release build on each box independently.
- Weights: `model.safetensors` sha256 `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`,
  byte-identical file on both boxes (staged to box1 from HF, transferred box1 -> box2 over LAN).
- Prompts: `prompts/e15d_prompt_set.json` sha256 `e55452a60a09a29918db8df72fd4727fdbbd111f4f2d63d462f0dd0c0e332653`, in-repo, identical both boxes.
- Invocation: `cis2_ref --weights-dir <model> --prompt-set prompts/e15d_prompt_set.json --gen-toks 32`.
- Scripts: `~/leg-crossisa-full.sh` on each box; logs `~/crossisa-full.log`, raw `~/crossisa-full-<host>.out`.
- **Rule A**: no timing number from this run is recorded or quoted. Both boxes had concurrent background work.
- VERIFIED (measured this session). The engine gaps below are VERIFIED by direct source read at `0f27277`.

## Known engine gaps (not exercised by this run)

- `head_dim` hardcoded `hidden/n_heads` (`src/main.rs:534`); an explicit config `head_dim` is ignored. Qwen3-0.6B
  therefore panics at the q_proj shape assert — loud failure, not a wrong answer.
- Untied LM head is coded (`src/main.rs:616-621`) but has zero runtime coverage; `docs/E15d_bc_RESULT.md` says so.
- Sharded checkpoints unsupported: single `root.join("model.safetensors")` at `src/main.rs:314`, no index.json.
- No chat-template handling; tokenization is raw with `add_special_tokens=false`. So this is a base
  forward-pass match, not an instruct-mode conversation claim — same caveat as the earlier Qwen2.5 result.
