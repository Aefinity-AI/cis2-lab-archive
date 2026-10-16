# box4 — CIS-2 v0.3b self-check on an SSE3-only x86-64 CPU: PASS

Date: 2026-10-01, run 16:11:59Z–16:25:55Z (about 14 min). Host `aefinity-box-0042` (<lan-ip>), AMD Sempron SI-42
(family 17, model 3), 1 core, 3.6 GB RAM, Debian 13, kernel 6.12.94, gcc 14.2.0. CPU flags relevant here: sse, sse2,
pni (SSE3). None of ssse3, sse4_1, sse4_2, avx, avx2, fma is present.
Raw log: `state/reports/box4-selfcheck/RESULT.txt` (sha256 7d409d22069c8a4c…, 24 lines). Leg: `box4-selfcheck`
pushed from penguin with `bin/cm leg push`; script kept in the leg directory `state/legs/box4/box4-selfcheck/`.

## What was run

Public `Aefinity-AI/cis2-spec` at main a76a579, cloned on the box, built with the box's own gcc, then the repository's
`self_check` (verify3: selftest, artifact hashes, determinism, conformance on the pinned v0.3b test vector).

## Result

| check | value | pinned | equal |
|---|---|---|---|
| FMA gate (objdump of the built binary) | 0 FMA instructions | 0 | yes |
| witness digest | d82743059d1db929…7c3cc9df | same | yes |
| argmax digest | 0b9c8f3ac90d0b9c…3d56f67aff | same | yes |
| table digest | 23c7bfaf5cef0095…0a06b35d | same | yes |
| inv_freq table digest | da9f6dcfde042558…7bbf6f12 | same | yes |
| generated token ids (16) | 28,665,436,253,1838,8180,3365,14176,30,2306,4161,281,253,2066,2291,351 | same | yes |

`self_check_rc=0`, verifier line `conformance=PASS`.

## Reading

- This is the oldest and smallest x86 class in the fleet so far. Earlier hosts were AVX2 (penguin, box1), scalar
  x86-64 without AVX2/FMA (box2), aarch64 phones, and QEMU. The SSE3-only Sempron gives the same four digests.
- One prompt, one model (the pinned v0.3b vector), one run plus the verifier's own determinism check. It is a
  conformance pass on a new host class, nothing more. No timing claim: the box is slow (14 min for the whole leg,
  build included) and timing was not measured separately.
- Claude Code itself does not start on this CPU (illegal instruction), so box4 works without ticks: jobs arrive from
  penguin (`cm leg push` now, `cm-legd` after `gh auth login`).

Publication: the row is a candidate for the public host table. It goes out with the next public PR after the
PUBLISH? list in NEEDS §00b is answered (the public repository is locked until then).

## Addendum 2026-10-01 17:26Z — box5, SSSE3-only Intel: PASS

Host `aefinity-box-1605` (<lan-ip>), Intel Pentium Dual T2310 1.46 GHz (family 6, model 15), 2 cores, 1.9 GB RAM,
Debian 13, kernel 6.12.94, gcc 14.2.0. CPU flags relevant here: sse, sse2, pni, ssse3; no sse4_1, sse4_2, popcnt, avx,
avx2, fma. Same leg as box4 (`box5-selfcheck`), run 17:19:16Z–17:25:32Z (about 6 min, build included).
Raw log: `state/reports/box5-selfcheck/RESULT.txt` (sha256 ba8da21500b685cf…).

Result: FMA gate 0 matches; witness, argmax, table and inv_freq digests and the 16 generated token ids all equal the
pinned v0.3b values (the same values as in the box4 table above); `self_check_rc=0`, `conformance=PASS`.

Reading: a second pre-SSE4 x86-64 class, from the other CPU vendor (AMD family 17 and Intel family 6 model 15), gives
the same digests. Same limits as above: one pinned vector, one run per host, no timing claim.
