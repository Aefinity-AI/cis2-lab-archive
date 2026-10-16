# W6 Part A on three hosts (supplementary, dated 2026-10-16; not a bar item)

Part A (exhaustive float32 sweep of expf against CORE-MATH, per range) was run unchanged on three hosts; the result files are beside this note.

| host | CPU class | glibc expf variant chosen by the loader (VARIANT line) | glibc max ULP (every range) | pinned implementation lines |
|---|---|---|---|---|
| box7 (lab host) | i7-7700HQ, AVX2+FMA | __expf_fma | 1 | identical to the other hosts |
| box1 | i5-5200U, AVX2+FMA | __expf_fma | 1 | identical |
| box2 | Celeron N4020, no FMA, no AVX2 | __expf_sse2 | 1 | identical |

Observations (RESULT lines compared with the host field removed):
- The pinned implementation (cis2_exp_pinned) gives byte-identical RESULT lines on all three hosts, including the negative-range subnormal-flush rows (max 8,388,582 ULP under default MXCSR) and the (88.0, 88.72] band rows (+Inf on all 94,743 inputs). That is the property the pinned path exists for.
- glibc's own expf differs between its __expf_fma and __expf_sse2 code paths on exactly one input per range per direction: count_ulp_ge1 is 97,017 vs 97,016 (neg, first pass), 73,537 vs 73,536 (pos), 96,992 vs 96,991 (neg, second pass); max ULP stays 1 on both paths. So a model that calls libm expf can produce a different float32 on an FMA host than on a non-FMA host for roughly one input in 1.1e9 per range. This is the host-dependence hazard W6 measures in Part B (top-1 flips); Part A on the two glibc variants gives the per-input rate directly.
- The box1 lines are byte-identical to box7's (same variant), as expected.

Sources: RESULT-partA-box2.txt, RESULT-partA-box1.txt (this directory), ~/legs/w6/RESULT-partA.txt on box7 (copied to state/reports/w6/ at result time). Numbers here are per-run counts from those files; aggregate claims go through NUMBERS.md.
