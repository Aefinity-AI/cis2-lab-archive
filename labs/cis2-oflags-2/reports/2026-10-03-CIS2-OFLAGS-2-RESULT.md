# CIS2-OFLAGS-2 result (ledger id cis2-oflags-2, job oflags2-box5)

Verdict: MET (scorable now; no box2 cell needed; not yet recorded in the ledger, the Record stage does that)

## Registered bar (verbatim, bar_sha256 acf6f8d160e473237208e17d9e735dce926f65e6fbb47434ca04272f15adef4f)
"Build verify3 sv5_driver on box5 (Pentium T2310, SSSE3) with clang (Debian clang 19, installed at run time) at -O2 and -O3, each with the spec flags in clang spelling (-ffp-contract=off -fno-fast-math -std=c11 -mno-fma; -fexcess-precision=standard is gcc-only and is omitted), and with gcc 14.2.0 -O2 plus the gcc spec flags rebuilt fresh in the same run as an anchor; replay the 100 items of chunks c000+c001 of the 135M guard replay (weights = g2-135 WEIGHTS_SHA256 on box5) with each binary. MET only if all three builds (clang -O2, clang -O3, gcc -O2 anchor) give witness AND argmax digests identical to the recorded box5 reference rows for 100 of 100 items. Positive control clang -O2 -ffast-math (no spec flags) is expected to change at least one digest; if it does not, the result stands but the control is reported as not firing. If clang cannot be installed the job reports SKIP and the bar is neither met nor failed. Reported, no bar: wall time per build, binary sha16 per build, clang and gcc version strings."

## Why it can be scored now
The registered bar names box5 only (reference rows = recorded box5 rows, all three builds on box5). The plan note that box2 was never run and box4 lacked clang_O3 + control concerns the unregistered cross-host replicas (oflags2rep-*), not this bar. box2 is not part of the bar. box4b has finished OK, so the descriptive table is now complete for boxes 1, 3, 4, 5.

## Numbers the bar needs (box5, Intel Pentium T2310, clang Debian 19.1.7 (3+b1), gcc Debian 14.2.0-19, weights a5e9f8ee455511c9734955c97c410b99e35d13a187952afbfccf3d0af2152cc6)
| build | binary sha16 | rows | witness identical | argmax identical | all (ids+witness+argmax) | wall s |
|---|---|---|---|---|---|---|
| gcc -O2 anchor (fresh) | fb7ec824feaca9d3 | 100 | 100/100 | 100/100 | 100/100 | 2207 |
| clang -O2 | c08dfc43f5db71a9 | 100 | 100/100 | 100/100 | 100/100 | 2198 |
| clang -O3 | e34155d26ff93988 | 100 | 100/100 | 100/100 | 100/100 | 2197 |
| CONTROL clang -O2 -ffast-math | 62b6f345700f6bcb | 100 | 0/100 | 100/100 | 0/100 | 1982 |

Control fired: the witness digest changed on 100/100 rows; argmax digests and ids_out stayed identical, so only the witness is sensitive to fast-math here.

## Independent checks (not only the RESULT line)
- job.sh sha256 = 125bf9bcfd9782fe22f0d7836f0f29332f65e563c10a054adf8d728f560a35d9, equal to the plan sha registered in the ledger (both the ~/feed-payload copy and the harvested state/feed/cm-box5/done copy).
- Parsed raw jsonl on penguin (~/guard-data/replay135/out/box5 and box5-<build>, chunks c000+c001, under systemd-run MemoryMax=2500M CPUQuota=60%, each file read once): reference 100 unique idx; gcc anchor, clang O2, clang O3 each 100/100 for ids_out, witness and argmax; fast-math control 0/100 witness, 100/100 argmax.
- Reference jsonl sha256: c000 d5f3caec2d533d5537dee00424483681166a5054567623a07d7f0aa53a1ed2ab, c001 7c821d3425b21c4417155fc980be5071645ffbd9dd0c7dea779a406303bdc71d (same as quoted in the OFLAGS-1 report).
- Run order/time: registered and started 2026-10-03T03:25:11Z, row files written 10:00Z to 11:40Z, harvested 11:44Z (after registration).
- Four distinct binary hashes: clang and gcc builds are different machine code (fb7ec824 vs c08dfc43 vs e34155d2), so equality is not binary reuse.
- RESULT.txt sha256 e75ca5aa9cbff58e7cfb43312dea8b646628a380bb843bea252378d59a9cc3dc; line: "RESULT: OK gcc anchor and both clang spec builds identical to the box5 reference rows (see control line)". No SKIP, no BUILD_FAIL.

## Descriptive only (unregistered replicas oflags2rep-*, ~/feed-payload/oflags2/aggregate.py output)
| build | box1 | box2 | box3 | box4 | box5 |
|---|---|---|---|---|---|
| gcc_O2_anchor | 100/100 fb7ec824 | not run | 100/100 fb7ec824 | 100/100 fb7ec824 | 100/100 fb7ec824 |
| clang_O2 | 100/100 c08dfc43 | not run | 100/100 c08dfc43 | 100/100 c08dfc43 | 100/100 c08dfc43 |
| clang_O3 | 100/100 e34155d2 | not run | 100/100 e34155d2 | 100/100 e34155d2 | 100/100 e34155d2 |
| CTRL fastmath | 0/100 62b6f345 | not run | 0/100 62b6f345 | 0/100 62b6f345 | 0/100 62b6f345 |
Replicas compare to each host's own reference rows; box4 is split across oflags2rep-box4a (gcc, clang_O2) and box4b (clang_O3, control). Binary sha16 is identical across hosts for the same flags, so cross-host equality is the same machine code on different CPUs, not an independent compiler result. box2 was not run; it is not needed for the registered bar. Optional extra cell if wanted later: oflags2rep job on cm-box2 (same script as oflags2rep-box1 with its own 135M reference rows), not required for any verdict.

## Caveats
- Scope: one model (135M guard replay), 100 items, one C driver (verify3 sv5_driver), clang 19.1.7 and gcc 14.2.0 only, x86 SSE without FMA (-mno-fma). This shows the digests did not depend on the compiler vendor or -O2/-O3 level under these flags on this host; it says nothing about other compilers, versions, ISAs or flags.
- The reference is the box5 row set produced by gcc 14.2 earlier; the in-run gcc anchor reproduces it 100/100.
- Wall times are noisy (shared box), reported only.
