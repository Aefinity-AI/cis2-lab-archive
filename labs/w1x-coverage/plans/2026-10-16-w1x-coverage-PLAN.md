# w1x-coverage: constructed CIS-2 coverage vector (argmax tie + subnormal logit)

Registered 2026-10-16 (EV card state/reports/ev-cards/w1x-coverage.md, GO 10.53). Builder payload
~/feed-payload/cis2-coverage (RESULTS.md records the hq build-host run).

## Why
The W3 mutant matrix (docs/results E22) left two mutants SAME on every real-model vector: M01 (no FTZ/DAZ
pin) and M15 (argmax `>=` instead of strict `>`). SAME meant the real vectors never exercised those clauses,
not that the clauses are inert. A constructed tiny model exercises both on purpose:
- Llama-arch bf16, hidden 64, 2 heads (head_dim 32 -> inexact rsqrt), 2 layers, inter 128, vocab 32,
  tie_word_embeddings false, seed 20261016.
- lm_head rows TIE_A=5 and TIE_B=17 are exactly equal (+-2.0 rows with sign from a float64 pass), so the
  step-0 logits tie exactly: strict-first argmax picks 5, M15 picks 17.
- lm_head row SUB=29 is built so its logit is a non-zero subnormal; the pinned FTZ/DAZ path flushes it to
  0x00000000, M01 keeps the subnormal bits. Only CIS2_REF moves (ids and argmax digest are unchanged).

## Bar (frozen at start)
Via cm-feed legs cis2-coverage-<host> on hq, w2, w3, w4 (template jobs/cis2-coverage.template.sh,
CPU-only host g++ builds of the payload sources): every host reports RESULT: OK with the same ref8 digest
(expected 4660d6c33b6c0d51529b4be43687c004c8b7c0d8804439999b5af32683528734 from the build host of record),
m01=MOVED and m15=MOVED on every host, ids0=5 (TIE_A) on every host, repeat=SAME on every host, and the
weights/config/ids sha prefixes 677a5a25 / af88fb25 / aa1bb87d confirmed. Any host FAIL, any SAME, any
ids0 != 5, any repeat=DIFF or any ref8 disagreement between hosts = NOT MET.

## Stretch (informative, not in the bar)
From-text numpy float32 forward (fromtext_forward.py) agreeing bit for bit with the C++ trace on hq:
done by the builder (MATCH on all 8 logit vectors; `--noftz` reproduces M01). Same author, so it is a
second implementation, not an independent party; it is reported as such.

## Publish plan
On MET: cis2-spec PR adding the tiny model (public, 175 KB) + ids as an informative coverage vector under
EXPECTED_DIGESTS / docs/results, and an E22 matrix addendum (M01, M15 MOVED on the coverage vector).
Publish score first (bin/cm-publish-score). No timing numbers.
