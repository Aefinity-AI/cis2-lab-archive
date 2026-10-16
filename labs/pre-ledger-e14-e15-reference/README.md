# pre-ledger-e14-e15-reference

- Scope: E14/E15 series: CIS-2 fp32 reference, cross-ISA, compiler invariance, clean-room verify; H1-H4 follow-ups; first results and critic pass
- Verdict: **no ledger rows exist for these (they predate the experiment ledger, or were run as plain legs).** What each report says about itself is quoted below; this archive does not restate it as MET / NOT MET.

## Reports

- `reports/2026-08-28-CIS2-RESULT.md`: CIS-2 — fp32 transformer inference, bit-identical across ISAs, from a spec (2026-08-28)
  - report states: Status: ALL LEGS COMPLETE incl. independence audit. Fable calls this DEFINITIVE on axis 3 (safe/deterministic AI) as of 2026-08-28 12:10 CT.
- `reports/2026-08-28-CIS2-critic-pass.md`: CIS-2 critic pass (Fable, 2026-08-28 evening) — paper cm/cis2-paper-draft @0be2402 + staged ~/projects/cis2-spec @44633fd
  - report states: Verdict: NOT READY (close). Top issue: paper implies human "different authors / different day" independence; truth = isolated AI agents, one operator, one day — must be disclosed, read-logs carry the independence claim.
- `reports/2026-08-28-E14a-cis2-fp-design.md`: E14a — CIS-2 design memo: extending receipt discipline to floating-point inference
  - report states: invariance* — a kernel's numerical result depends on the batch size it is
- `reports/2026-08-28-E15c-verify.md`: E15c adversarial verification — cis2-fp cm/e15c-cross-isa
- `reports/2026-08-28-E15d-a-result.md`: E15d(a): CIS-2 compiler-invariance CI matrix — RESULT
- `reports/2026-08-28-E15d-bc-result.md`: E15d(b,c) result — cis2-fp (private repo)
  - report states: Torch oracle: 16/16 token match, logit rel diff 3.9e-6 (bar 1e-2). Cross-ISA
- `reports/2026-08-28-E15e-result.md`: E15e — clean-room cis2-verify result (PARTIAL: MISMATCH on full digest, MATCH on argmax)
  - report states: `cis2-verify`), built reading only the E14a memo + E15b/E15c result docs
- `reports/2026-08-28-E15g-audit.md`: E15g clean-room v2 audit — cis2-verify2 vs CIS2_SPEC_v0.1.md
  - report states: status "added" (A), no rename/copy detected by git:
- `reports/2026-08-28-E15g-result.md`: E15g: clean-room attempt #2, CIS-2 v0.1 — MATCH (first try)
  - report states: Result: ALL FOUR pinned digests MATCH bit-for-bit on both x86_64 and
- `reports/2026-08-28-E15h-verify2-result.md`: E15h — verify2 vs CIS-2 v0.2: MATCH
  - report states: `inv_freq_table_digest` all match the reference's v0.2 values bit-for-bit.
- `reports/2026-08-28-E15i-result.md`: E15i — CIS-2 v0.2 spec doc + E15d rerun on v0.2 reference
- `reports/2026-08-28-E15j-result.md`: E15j — clean-room C11 (cis2-fp verify3/) — PARTIAL conformance
  - report states: | digest | x86_64 gcc/clang, aarch64 gcc/clang | v0.2 expected | match |
- `reports/2026-08-28-E15k-result.md`: E15k — divergence RESOLVED: full 4/4 cross-language MATCH (was partial)
  - report states: **Fix applied**: reordered §12.1 items 1-5 in the spec to match
- `reports/2026-08-28-H1-result.md`: H1 — CIS-2 scale + breadth + 512-token horizon (CI 33214545380, all 9 jobs SUCCESS)
  - report states: | Leg | Model | What | Result |
- `reports/2026-08-28-H2-result.md`: H2 result — transcendental accuracy characterization (cis2-fp, private)
- `reports/2026-08-28-H3-result.md`: H3 — CIS-2 v0.2 spec completeness audit — 2026-08-28
- `reports/2026-08-28-H4-result.md`: H4 result — pin tokenizer in CIS-2 spec (closes H3 BLOCKER-2)
