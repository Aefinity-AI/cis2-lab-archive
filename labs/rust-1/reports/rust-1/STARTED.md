# rust-1 STARTED 2026-10-04T09:25:49Z
Ref: cm/rust-lab@84ecf1308bf5275fc0beb480a1f09ba39e11a952 (private alice-model, dir rust-lab/rust1/; push confirmed with git ls-remote)
freeze-arm-l=5d4af11cd2ce6de64a5cd07a085466aece50bdb89c81e3a09e5d5ae1c8db4262  (state/reports/rust-lab/rust-1/FREEZE-ARM-L.md; not edited after this sha was taken; one text correction was made before it: tick timer period 1 h, not 2 h)
amended bar_sha256 a4f1a43eadcd8a9ab2e62c0e0e924d6fba865944418ae337a8bc68513dec6467 (registered c20822c4f835...)
PAYLOAD_SHA256 sha256 dc446d789027f1a61edf399d68f4601644890d896ca9c2919924a2dc7cce8ac9, run.py sha256 300a10b736c99342129d06afb3a3f9e465f4d5af1f8b1ff162f016a94cdcd13c (in every wrapper and in every RESULT line)
Start record: anchored in the public ledger (route A): amended bar is ledger line 170, public since 2026-10-04 09:23:31Z (cis2-spec PR #5).
Scope: arm L alone (IMPLEMENTATION). Stage 2 (FRAMEWORK, KERNELS) is rust-1b, registered 2026-10-04 (ledger line 171), not started.
Jobs: rust1-box1 (labelled host), rust1-box2, rust1-box4, rust1-box5 queued at the start. rust1-box3 is held: box3 is reserved for dormant-2 training and its rust-1 job is queued afterwards (unlabelled host, no effect on the label).
After each job the operator copies <home>/legs/<job>/ from the box (rows.jsonl, run.log, checks/, timed/) into state/reports/rust-lab/rust-1/<host>/ before any scoring.
Known low items left as they are (confirmation read): the box1 wrapper records PAUSED after the systemctl stop returns (a TERM in that window leaves the timers off until the failsafe at cap + 30 min); Rust binaries were not rebuilt by the confirming reader (source hashes and the two C rebuilds matched).
Disclosures: CPUQuota is the non-binding 100 percent x logical CPUs because cm-feed cannot omit it (R5); box2 is an unlabelled host.
Note 2026-10-04 10:00 UTC (operator): the rust-4 fix round removed cargo's closing line (a penguin build time) from four rust-1 build logs in the code repo (cm/rust-lab commit 43e2573f, logs alone). rust-1's pinned commit 84ecf130 and its payload on the boxes are unchanged; build time is not a quantity of rust-1.
