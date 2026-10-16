# CIS-2 real-weight tamper leg: the header-only control, resolved (2026-10-16, Fable)

Published 2026-10-16 as part of the CIS-2 archive.

## What happened
w1x-tamper (E-0093, registered 08:53Z, started 08:59Z) mutates the pinned SmolLM2-135M safetensors
(sha256 80521b40…) one change at a time and decodes 16 tokens with the C++ port under the pinned flags.
The registered bar said the header-only control (one padding space in the safetensors JSON header turned
into a tab; byte count and data offsets unchanged) must move sha256 but must NOT move the witness.

w3 (seed 20261016) and w4 (seed 20261017) both reported the control moving the witness
(digest 1593e09e608d4f7c… instead of the pinned d82743059d1db929…).

## Cause (verified on hq, 09:1xZ)
`cis2_host.cpp` lines 179-186 (§12.1 witness header): the witness SHA-256 is seeded with the RAW 32-byte
sha256 of the weights file, the tokenizer file and config.json, then the table digests, then the prompt ids,
and only then the per-step full fp32 logits and argmax ids. Any byte change in model.safetensors therefore
moves the witness by construction. Run on hq with the mutated file:

- prompt + 16 generated tokens: identical to the pinned run ([6403, 1980, 253, 655, 28, 665, 436, 253, 1838,
  8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351])
- run1_argmax_digest: identical (0b9c8f3ac90d0b9c…)
- weights_sha256: e7c6661b2f773c1a… (moved), run1_witness_digest: 1593e09e608d4f7c… (moved)

So the C++ port is correct and the spec behaves as designed: the receipt binds the exact artifact bytes.
The control was mis-specified at registration (my error: the bar assumed the witness covers only the
computation). The lesson for the spec text: §12.1 should state explicitly that the witness binds the
artifact hashes, so a reader does not expect header-only edits to be invisible.

## Protocol handling
- `cm-exp amend-bar` REFUSED (bar frozen after start) — correct. w1x-tamper will be scored against its
  registered bar: all data-mutation clauses MET (54/54 witness + sha on each of w3, w4; sign/exponent flips
  11/11 and 13/13), control clause NOT MET, with this note as the explanation.
- Corrected design registered as **w1x-tamper2** (E-0095, bar sha 4c146db39d2f52c7, ledger batch 35
  line 258) BEFORE any v2 result is read. Template v2 adds: a base trial (unmutated copy must reproduce
  CIS2_REF), a witness BODY digest (per-step full fp32 logits + argmax ids, header excluded; one printed line
  added to a patched copy of the port, patched-sources sha 732c2a36d38b8933 vs payload 10e08ea20584151f),
  and the argmax digest per trial. Control PASS = sha + witness move, body + argmax do not.
- Same seeds as v1 (hq 20261018, w3-r2 20261016, w4-r2 20261017) so the mutant sets are identical.

## Data already in hand (v1 outputs post-processed for the greedy-token digest)
| class | mutants | greedy tokens changed (w3) | (w4) |
|---|---|---|---|
| ulp1 (one element +1 bf16 ULP) | 24 | 0 | 0 |
| int8 (one tensor round-tripped) | 6 | 3 | 3 |
| bitflip (one random bit) | 24 | 1 | 2 |

Every one of these 54 mutants per host moved the witness; only 4 of 54 (w3) and 5 of 54 (w4) changed the
generated text. A token-level or text-level receipt would have missed roughly 92% of them. v2's body digest
will show how many are caught at the logits level WITHOUT the artifact-hash binding (smoke on hq: ulp1 on a
layernorm weight, an int8 round-trip and an exponent-bit flip all moved the body digest; the control did not).

## Smoke (hq, template v2, N=1 per class, 09:21-09:24Z)
RESULT: OK base=MATCH mutants=3 sha_detect=4/4 witness_detect=4/4 body_detect=3/3 argmax_detect=1/3
meta: sha=yes witness=yes body=no argmax=no meta_control=PASS

## Next
w3-r2 running (09:3xZ), w4-r2 queued after v1, hq after cis2-horizon-hq -> cm-exp result w1x-tamper
(partial) + w1x-tamper2 -> NUMBERS -> publish score -> cis2-spec results note (counts only, no mutant
descriptions) + a §12.1 clarifying sentence (spec erratum, numbered).
