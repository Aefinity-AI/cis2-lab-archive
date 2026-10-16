# E15d(a): compiler-invariance of the CIS-2 fp32 reference

Rule A applies (no timing numbers). Published 2026-10-16 as part of the CIS-2 archive.

## Claim

The CIS-2 fp32 reference's normative outputs (`CIS2_REF digest` and
`inv_freq table_digest`) are invariant to compiler settings — opt-level and
`target-cpu` — on both x86_64 and aarch64, despite the machine code
demonstrably differing across those settings. This extends E15c (cross-ISA
invariance at a single opt-level/target-cpu) to a full 2 (ISA) x 5
(opt-level) x 2 (target-cpu) = 20-cell matrix, mirroring the shape of
`alice-aegis` ledger row A42 (CIS-1 op-level digest, 9 build configs).

## Method

- `.github/workflows/e15d-compiler-invariance.yml`, `workflow_dispatch`
  (+ a `push` trigger on this branch only, needed so GitHub registers
  the workflow at all — `workflow_dispatch` alone isn't dispatchable via
  API until GitHub has seen a run of the file).
- Matrix: `runner {ubuntu-latest=x86_64, ubuntu-24.04-arm=aarch64} x
  opt-level {0,1,2,3,s} x target-cpu {generic,native}` = 20 build jobs.
- Per job: `RUSTFLAGS="-C target-cpu=$CPU"`, `CARGO_PROFILE_RELEASE_OPT_LEVEL=$OPT`
  (overrides Cargo.toml's pinned `opt-level = 3`, verified locally to
  produce an "unoptimized" build at opt=0), `cargo build --release`, then
  runs the unchanged reference (`Once upon a time`, gen_toks=16 — same
  prompt/model/gen length as E15c) and asserts both digests against the
  E15b m1.5 pre-registered targets.
- Toolchain: `rust-toolchain.toml` pins `channel = "1.98.0"` (added mid-task
  — cis2-fp had no toolchain pin before this; both E15c and the first E15d
  run merely happened to land on 1.98.0 because that's what "stable"
  resolved to on 2026-08-28). `rustup-init --default-toolchain none` so the
  pinned 1.98.0 is what actually installs/runs.
- Evidence per job: `objdump -d` of the release binary -> sha256 + byte
  count of the disassembly (proxy for `.text` divergence across opt-levels)
  + a combined FMA-instruction grep (`vfmadd*|vfnmadd*|vfmsub*|vfnmsub*|
  fmadd|fmsub|fnmadd|fnmsub|fmla|fmls`, covers both x86 AVX and aarch64
  NEON/scalar FMA mnemonics) that must be exactly 0 or the job fails.
- Weights fetched exactly once per run (`fetch-weights` job resolves the
  current HF revision sha, `actions/cache` keyed on that sha, distributed
  to the 20 build jobs via `actions/upload-artifact` /
  `actions/download-artifact`) rather than 20x from huggingface.co.
- `aggregate` job (needs: all 20 build jobs) collects each job's evidence
  artifact, renders a markdown table into the job summary, and fails
  unless exactly 20/20 artifacts are present, all digests match the
  pre-registered target, and all FMA counts are 0.

## Result

Two full runs, both `conclusion: success`, both aggregate: `jobs
collected: 20 / 20`, `mismatches: 0`:

- Run 1 (pre-toolchain-pin): https://github.com/Aefinity-AI/cis2-fp/actions/runs/33189498641
- Run 2 (with `rust-toolchain.toml` pin): https://github.com/Aefinity-AI/cis2-fp/actions/runs/33190058353

**20/20 cells** reproduce `CIS2_REF digest=ba88708bf4159a4057d4eef727820ebc5ce1744ae334bfe0cc0776e03509dd0f`
and `inv_freq table_digest=da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12`
exactly, matching the pre-registered E15b m1.5 target — across both ISAs,
all 5 opt-levels, and both target-cpu settings.

**FMA count is 0 in all 20 jobs** (both the grep-source gate via
`no_fma_gate.sh` and the fresh per-job objdump grep against
`vfmadd*/vfnmadd*/vfmsub*/vfnmsub*/fmadd/fmsub/fnmadd/fnmsub/fmla/fmls`).

**Machine code genuinely differs across opt-levels** — disassembly byte
count and sha256 diverge within each arch as opt-level changes (Run 2,
x86_64): opt0 5535785/5369683 bytes -> opt1 2447401/2439875 -> opt2
2274777/2304355 -> opt3 2336553/2371091 -> opts 1838361/1824803 (generic
vs native columns respectively; full table below and in the hardware
log). This is the non-triviality evidence required by the claim shape (cf.
alice-aegis A42): the digest invariance is not because the compiler
produced identical code, it's because the reduction order and absence of
FMA contraction are pinned at the source level (CIS-2 sec3.1/sec3.2,
`src/math.rs`) regardless of what the optimizer does structurally.

### Full 20-row table (Run 2, pinned toolchain)

| job | arch | opt | cpu | cis2_ref_digest | inv_freq_digest | text_size(bytes, disasm proxy) | disasm_sha256 (truncated) | fma_count | match |
|---|---|---|---|---|---|---|---|---|---|
| aarch64-opt0-generic | aarch64 | 0 | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 4259908 | 8431df1c30d2b4cf... | 0 | yes |
| aarch64-opt0-native | aarch64 | 0 | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 4436020 | 1a3eee3619c4e919... | 0 | yes |
| aarch64-opt1-generic | aarch64 | 1 | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2068516 | 734aaf7b217eac76... | 0 | yes |
| aarch64-opt1-native | aarch64 | 1 | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2125780 | 2ed30de49b8892cd... | 0 | yes |
| aarch64-opt2-generic | aarch64 | 2 | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 1945924 | 4203f72912f465dd... | 0 | yes |
| aarch64-opt2-native | aarch64 | 2 | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 1998932 | 68ce8c41682c26e2... | 0 | yes |
| aarch64-opt3-generic | aarch64 | 3 | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2021172 | ded8014bd9671624... | 0 | yes |
| aarch64-opt3-native | aarch64 | 3 | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2075636 | 2ccfddc538d6195b... | 0 | yes |
| aarch64-opts-generic | aarch64 | s | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 1696580 | c77c1f5a60472679... | 0 | yes |
| aarch64-opts-native | aarch64 | s | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 1682996 | 224c75fa3c323d91... | 0 | yes |
| x86_64-opt0-generic | x86_64 | 0 | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 5535785 | a94025ff72008847... | 0 | yes |
| x86_64-opt0-native | x86_64 | 0 | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 5369683 | fa226bf682a1ffaa... | 0 | yes |
| x86_64-opt1-generic | x86_64 | 1 | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2447401 | a04849ce34460abc... | 0 | yes |
| x86_64-opt1-native | x86_64 | 1 | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2439875 | 5e1aa3c39a066d35... | 0 | yes |
| x86_64-opt2-generic | x86_64 | 2 | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2274777 | f01d3a4374714121... | 0 | yes |
| x86_64-opt2-native | x86_64 | 2 | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2304355 | b55a7a69b5880889... | 0 | yes |
| x86_64-opt3-generic | x86_64 | 3 | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2336553 | e5bf771c570cb4f6... | 0 | yes |
| x86_64-opt3-native | x86_64 | 3 | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 2371091 | 48ebb09e0d4f73fc... | 0 | yes |
| x86_64-opts-generic | x86_64 | s | generic | ba88708b...9dd0f | da9f6dcf...bf6f12 | 1838361 | 3a54719d34e609d8... | 0 | yes |
| x86_64-opts-native | x86_64 | s | native | ba88708b...9dd0f | da9f6dcf...bf6f12 | 1824803 | 5a0369912d68d064... | 0 | yes |

Full digests, per-job evidence text, and both runs' job lists are in
`hardware_logs/e15d_a_2026-08-28.log`.

## Toolchain / commits

- rustc 1.98.0 (`88d9e12ae`, 2026-08-18) — now pinned via `rust-toolchain.toml`
- Workflow commit (pre-pin, Run 1): `d1cfa7f334545a406f4bfe3cdee6ebf52e82d814`
- Toolchain-pin commit (Run 2): `c2660d760ec34c4c58ea178451d8ac16c52ab07c`
- Branch: `cm/e15d-compiler-invariance` (base: `cm/e15c-cross-isa`)

## Findings, not fixes

- No mismatch observed anywhere in the 40 total job-runs (20 x 2 runs).
  Nothing to report as a discrepancy.
- The repo had no `rust-toolchain.toml` before this task (E15b/E15c/first
  E15d run all rode on whatever "stable" resolved to). Added one here;
  documented as a gap found, not silently patched into prior results.
