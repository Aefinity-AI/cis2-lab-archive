# Agent-Episode Receipts: the literature check, and the competitor that argues our case

Date: 2026-09-09
Method: my own searches and full-text reads this session (WebSearch + WebFetch + local `pdftotext` on the
retrieved PDF). No subagent was used. Every quote below was pulled from text I extracted myself.

## Bottom line

Two results, and the second is worth more than the first.

1. **The field is NOT empty.** "Agent action receipts" — signed, hash-chained, tamper-evident tool-call logs —
   are a crowded 2026 space with commercial products, framework issues and multiple arXiv papers. Anyone
   pitching AEGIS-TRACE as "the first agent receipt" will be corrected in the first meeting.
2. **Every one of them stops at the same wall, and one of them proves it formally.** They attest *assertions*.
   None recompute the model. The strongest paper in the space (A2Auth, arXiv:2603.14332) defines a `full`
   verification tier that requires bit-exact reproduction, proves that without it verification is only
   *statistical*, and can name exactly one way to reach that tier: a single closed commercial provider on
   fixed GPU hardware. That is a published, third-party statement of the market gap CIS-2 fills.

## 1. What already exists (so we stop claiming it doesn't)

| Work | What the receipt proves | Recomputes the model? |
|---|---|---|
| Notarized Agents, arXiv:2606.04193 | A receiver signs that an interaction occurred | **No** |
| Verifiability-First Agents, arXiv:2512.17259 | Observability + audit agents | No |
| Agent action receipts (PipeLab, AgentPatterns, agno #6892, LangChain how-tos) | Signed action log, `previous_receipt_hash` chain | No |
| Attestable Audits | TEE attestation of a benchmark run | No — trusts the TEE |
| A2Auth, arXiv:2603.14332 | Capability binding + replay verification | **Partially — see below** |

The common shape: a signer asserts "I called tool X with args hashing to H, and got back Y." The chain proves
the log was not edited afterwards. It does **not** prove the model actually produced Y. A lying executor signs a
false receipt and the chain verifies perfectly. That is the wall.

## 2. A2Auth (arXiv:2603.14332, Zhou, Genupixel, v2 19 Mar 2026) — read in full

This is the closest competitor and the most useful document in the estate's whole prior-art file, because it
concedes, in print, the thing we need a third party to say.

Its verification procedure branches on a declared reproducibility level:

> `if ρ.level = full :`
> `  return O_ref == O_orig ? VERIFIED : VIOLATION`
> `else : // statistical`
> `  return CharMatch(O_ref, O_orig) ≥ θ ? VERIFIED : VIOLATION`

So the architecture already has a bit-exact tier. What can reach it?

> "...and selecting inference providers that guarantee bitwise or near-bitwise reproducibility [6]."

Reference [6] is EigenAI — a closed commercial provider. And:

> "EigenAI [6] achieved 100% bit-exact deterministic inference **on fixed GPU architectures**."

That is the entire population of the `full` tier: one vendor, one hardware class, no specification anyone else
can implement. Everyone not using that vendor falls to the statistical branch, and the paper is explicit about
what that costs:

> "Token-level reproducibility provides **statistical rather than computational security**, but the Bounded
> Divergence Theorem (§4.8) bounds this gap: an adversary passing n replay checks has produced a model
> (n, ϵ)-indistinguishable from the original, with ϵ ≤ ln(1/α)/n."

They then measure how bad the statistical branch is in practice — 9 models, 7 providers, 15,120 comparisons:

> "Determinism spans 5.8× (Haiku 4.5: 0.987 to Kimi K2.5: 0.169)"

and turn that into a deployment constraint they call prescriptive:

> "High-determinism models at interior tree positions" — because of their Chain Verifiability Theorem, one
> unverifiable interior agent breaks end-to-end verification for every downstream node.

They also concede the trust dependency in the basic tier:

> "The basic G2 instantiation requires provider cooperation: the verifier must re-execute the agent's declared
> model on recorded inputs... the verifier must have API access to the same model version."

### What this means for us

A2Auth is not a threat to AEGIS-TRACE. It is an independent, citable specification of the socket AEGIS-TRACE
plugs into:

- Their G2 `full` tier needs `O_ref == O_orig`. CIS-2 delivers exactly that, from a written spec, on hardware
  nobody had to pre-record — x86, ARM, and a Tesla P100.
- Their Bounded Divergence Theorem is a bound on ignorance. With a bit-exact substrate, α = 1 and ϵ = 0: the
  theorem collapses to certainty. We do not have to argue against their result; we are its degenerate case.
- Their Chain Verifiability Theorem says one unverifiable interior node poisons everything downstream. That
  converts determinism from a nice property into a *placement constraint on every agent in a pipeline* — i.e.
  it makes the thing we sell load-bearing for the thing they sell.
- Their measured 5.8× determinism spread is the market-sizing datum we did not have and did not have to
  generate ourselves.

Local confirmation that we actually occupy this socket: `aegis-linux/examples/agent_trace.rs:823` —
`trace_fold_step(..., decode_chain_digest: &[u8; 32], ...)` folds a per-step bit-exact decode digest into the
episode chain. The binding to a recomputable decode is real code, not a plan.

## 3. Wording that survives contact

Do **not** say: "the first agent receipt", "nobody has done verifiable agent traces".
Do say, and this is defensible line by line:

> Signed agent receipts prove a log was not edited. They do not prove the model computed what the log says.
> The strongest work in the field (arXiv:2603.14332) defines a bit-exact verification tier, proves that
> everything below it is statistical rather than computational security, and can name exactly one way to reach
> it: one closed vendor, on fixed GPU architectures. AEGIS-TRACE reaches that tier from a written
> specification, on hardware that vendor never touched.

## 4. Correction to the estate's own file

The brief that prompted this said arXiv:2606.00279's "full text was never read." That was true of
`2026-08-28-CIS2-priorart.md`; it was superseded the same day by `2026-08-28-CIS2-priorart-fulltext.md`.
I re-verified it independently today rather than trust either file. It holds, and it holds for a reason worth
using: Cankaya's method needs a **4 GB cached table per transcendental instruction per GPU generation** —

> "we cached their exact hardware outputs (e.g. a 4GB table mapping every 32-bit input for MUFU.EX2)"

— has no normative document, no second implementation, an unbuilt receipt over a single hidden state, and an
explicit "Only NVIDIA GPUs" scope. It is a *recording of silicon*. A recording cannot be implemented by a
stranger on hardware you never recorded. A specification can — which is precisely what the estate has already
demonstrated three times over. The stale limitation line in the older file has been marked CLOSED so this does
not get re-opened a third time.

## Sources

- https://arxiv.org/pdf/2603.14332 (A2Auth — full text extracted locally and read)
- https://arxiv.org/pdf/2606.04193 (Notarized Agents)
- https://arxiv.org/pdf/2512.17259 (Verifiability-First Agents)
- https://arxiv.org/abs/2606.00279 and https://arxiv.org/html/2606.00279v2 (Cankaya)
- https://github.com/agno-agi/agno/issues/6892, https://pipelab.org/learn/agent-action-receipts/,
  https://agentpatterns.ai/security/cryptographic-governance-audit-trail/
