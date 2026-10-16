# 9. Reproducibility

Repository: `Aefinity-AI/cis2-spec` (specification, reference `src/`, `verify2/`, `verify3/`, `docs/`, `hardware_logs/`; Apache-2.0
alongside this paper per the publish decision). Branch for this paper's evidence:
`cm/cis2-paper-draft`, merged from `main` at commit range ending `395ebdb`. Spec version: `docs/CIS2_SPEC_v0.2.md` at v0.2.1 (tokenizer §3.1 fully pinned, doc-only over v0.2; digests unchanged, §3). Toolchain pin:
`rust-toolchain.toml` (channel `1.98.0`, targets `x86_64-unknown-linux-gnu` and
`aarch64-unknown-linux-gnu`).

## 9.1 Rust reference (`src/`), primary test vector

```
mkdir -p weights
curl -sSf -L -o weights/config.json     https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/config.json
curl -sSf -L -o weights/tokenizer.json  https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/tokenizer.json
curl -sSf -L -o weights/model.safetensors https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/model.safetensors
echo "80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1  weights/model.safetensors" | sha256sum -c -
cargo test --release
./scripts/no_fma_gate.sh
cargo build --release
./target/release/cis2-fp weights/model.safetensors weights/config.json weights/tokenizer.json
```

Expected output includes:

```
CIS2_REF digest=a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da prompt_idx=0 prompt_toks=4 gen_toks=16 dtype=fp32
table_digest=465d358ccd63721256dbd2abbc77ad5de755adf3230635f95b12b1727dfa1ea3
inv_freq_table_digest=da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12
argmax_digest=0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff
generated_token_ids=[28,665,436,253,1838,8180,3365,14176,30,2306,4161,281,253,2066,2291,351]
```

reproduced on both x86_64 (`ubuntu-latest`) and aarch64 (`ubuntu-24.04-arm`) in CI run
`33171752921` (jobs `98850338683`/`98850338874`), and again after the v0.2 receipt-format change
in the E15i/E15d(a) 20-cell compiler-invariance matrix, CI run `33195649908`.

## 9.2 C11 clean-room (`verify3/`), cross-language check

```
cd verify3
make CC=gcc      # or CC=clang
objdump -d cis2_verify3 | grep -Ei 'vfmadd|vfnmadd|vfmsub|vfnmsub|fmadd|fmsub|fmla|fmls'   # expect no matches
./cis2_verify3 ../weights/model.safetensors ../weights/config.json ../weights/tokenizer.json
```

Expected output (all four {x86_64, aarch64} × {gcc, clang} cells, post-E15k spec fix):

```
CIS2_VERIFY3 digest=a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da prompt_idx=0 prompt_toks=4 gen_toks=16 dtype=fp32
CIS2_VERIFY3 conformance=PASS
```

CI run `33200155942` (workflow `.github/workflows/e15k-divergence-localization.yml`); the
pre-fix, three-of-four-match state is preserved for the record in run `33197817365`
(`.github/workflows/e15j-cleanroom-c.yml`).

## 9.3 Rust clean-room (`verify2/`), independence audit

Built from `CIS2_SPEC_v0.1.md`/`v0.2.md` text alone by a separate implementer, `src/`/`verify/`
never opened; reruns the same reference build/test sequence as §9.1 against `verify2/`'s own
`Cargo.toml`. Expected `CIS2_REF` and `inv_freq_table_digest` identical to §9.1's values on both
ISAs. CI run `33194049057` (v0.2 rerun); independence findings (verbatim-line overlap 18.0%,
attributable to spec-pinned constants, not copying) in
`Appendix B: E15g-audit`.

## 9.4 Scale/breadth/horizon (Qwen2.5-1.5B, 512-token) — reference implementation only

Workflow `.github/workflows/h1-scale-breadth.yml`, CI run `33214545380` (9 jobs, all SUCCESS):
cross-ISA digest equality for Qwen2.5-1.5B at `gen_toks ∈ {16, 128, 512}`, cross-ISA digest
equality for SmolLM2-135M at `gen_toks = 512`, and a 512-token oracle-correctness comparison
against PyTorch fp32 for Qwen2.5-1.5B. This leg exercises the Rust reference implementation only;
neither clean-room (`verify2`, `verify3`) has been run against Qwen2.5-1.5B or at these longer
horizons. `Appendix B: H1-result` reports only pass/fail verdicts; the literal hex digests below
were pulled directly from run `33214545380`'s job logs (`gh api
repos/Aefinity-AI/cis2-fp/actions/jobs/{id}/logs`), not from any summary report, since the run's
artifacts are not expired at the time of this writing:

```
Qwen2.5-1.5B  gen_toks=16   CIS2_REF=5670920223a840d33fcd1dd0154c8f650b09e73a6c5a0066b848a0dd1b347776  argmax_digest=c2c9f68961ac669f888e369fb851ffbb31fb9b359de4204bd8825d955264c5b9
Qwen2.5-1.5B  gen_toks=128  CIS2_REF=7b6f177ca8d2bec21dedb40296386efb9b7fc4a65e582a23df7edbd361138068  argmax_digest=940db72dcc2f48cc83f386214016aea758166d8f26848e984b4e2f5adef24b0d
Qwen2.5-1.5B  gen_toks=512  CIS2_REF=f2f0c8a05da25eb7f2cf4f24b4ed7d9d866d84f8053ee577826e6cde869a3c1d  argmax_digest=270018a12c07641b00e03e39fdefe746229de11cf941800892e8849a878b4def
Qwen2.5-1.5B  table_digest=465d358ccd63721256dbd2abbc77ad5de755adf3230635f95b12b1727dfa1ea3 (unchanged vs. SmolLM2 — shared transcendental table)
Qwen2.5-1.5B  inv_freq_table_digest=02908dae2c15329014dd986fec8033e03427fba0935b04b864ab2bc75fe3bc44 (rope_theta=1000000, distinct from SmolLM2's table)
SmolLM2-135M  gen_toks=512  CIS2_REF=27d319bb77be096e34b34c8bd490b6ed53b56300049a4a92d683e9969c7653a4  argmax_digest=bd54450756235fe4d2e06f0310fcaeaeb1aba3d6a5c19f485f080767be7bc4f6
Qwen2.5-1.5B  512-tok oracle: max_abs_diff=6.473064422607422e-05 at idx=19896 (rust=1.8892077207565308, oracle=1.8891429901123047), relative diff=2.445408220505891e-06 < 0.01, all 512 tokens match
```

All values above matched bit-for-bit between the `ubuntu-latest` (x86_64) and `ubuntu-24.04-arm`
(aarch64) jobs of run `33214545380`; the aggregate jobs (`aggregate-qwen15b`, `aggregate-smollm2-512`)
printed `PASS` for both comparisons.

## 9.5 Transcendental accuracy characterization (no CI run — offline analysis)

`docs/H2_TRANSCENDENTAL_RIGOR.md` documents a Python port of §6's pinned functions
(`numpy.float32`, matching rounding semantics) checked against an `mpmath` 60-digit oracle plus
correctly-rounded-fp32 neighbor search; this is an analysis script, not a CI-gated build, and is
included in the repository for direct re-run.

## 9.6 What this section does not claim

No wall-clock timing, throughput, or performance number is reported for any of the above builds or
runs, per Rule A. Every command above re-derives an identity claim (a digest) or an accuracy claim
(an ULP/relative-error figure against an oracle), not a speed claim.
