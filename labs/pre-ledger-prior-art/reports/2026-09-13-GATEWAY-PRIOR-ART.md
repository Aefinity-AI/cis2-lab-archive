# SAFE-1 gateway: prior-art map and honest positioning

Scope: SAFE-1 "no receipt, no action" tool gateway
(`2026-09-13-SAFE1-RECEIPT-GATEWAY-DESIGN.md`, critic `-DESIGN-CRITIC.md`,
e2e `2026-09-13-safe1c-e2e-box1.md`): verify-execute-bound receipts,
weight-digest allowlist, nonce/counter freshness, externally anchored
hash-chained decision log, independent second-verifier replay. Extends
`2026-09-09-AGENT-RECEIPT-PRIOR-ART-AND-A2AUTH.md` (full A2Auth treatment
there, not repeated here).

## 1. Tool-use policy enforcement / agent guardrails

**NVIDIA NeMo Guardrails**: runtime layer intercepting requests, running
Colang policies + safety-classifier NIMs, "33% improvement in policy
violation detection" ([NVIDIA blog](https://developer.nvidia.com/blog/measuring-the-effectiveness-and-performance-of-ai-guardrails-in-generative-ai-applications/)).
Enforces content/topic/PII policy on text. Does not verify a tool call
corresponds to any specific model computation — it classifies text, does
not replay inference.

**Meta LlamaFirewall**: PromptGuard 2 (jailbreak/injection), Agent
Alignment Checks (chain-of-thought misalignment auditor), CodeShield
(static analysis); ships a tool-output injection benchmark
([arXiv:2505.03574](https://arxiv.org/pdf/2505.03574)). Detects adversarial
content/goal drift; does not bind a tool call to a verified inference —
inspects text/reasoning, not token-level reproducibility.

**Anthropic MCP guidance / OWASP MCP cheat sheet**: names the confused
deputy explicitly — "the confused deputy is the model itself" since
tool-result content has no attestable provenance and `ToolAnnotations`
are advisory ([OWASP](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)).
Mitigation is OAuth+PKCE, session IDs bound to `<user_id>:<session_id>`,
least privilege — authorization/identity, not inference integrity or
bit-exact replay. **MCP-38** (arXiv:2603.18063) is a 38-category STRIDE-
mapped threat taxonomy; abstract does not name confused-deputy/TOCTOU and
is taxonomy, not mitigation ([arXiv:2603.18063](https://arxiv.org/pdf/2603.18063)).

**Agent sandboxing**: AGENTSAFE (arXiv:2512.03180) formalizes per-tool
"Capability Profiles" enforced via containerization/syscall filtering —
closest existing work to the SAFE-1 design's "rogue process bypasses the
gateway" gap (§3 of the design memo), and it is OS isolation, complementary
to receipt verification, not overlapping ([arXiv:2512.03180](https://arxiv.org/pdf/2512.03180)).
**INFERENCE**: no paper found combines sandboxing with inference-receipt
verification; every source treats them as separate layers.

## 2. Provenance and attestation for AI outputs

**C2PA / Content Credentials**: signed, tamper-evident metadata on media
files describing origin/edits ([c2pa.org](https://c2pa.org/faqs/)). Proves
a signed claim about media production, not its truth; strippable by
re-encoding; one 2026 paper finds the spec "fails to achieve their claimed
security goals" ([arXiv:2604.24890](https://arxiv.org/html/2604.24890v1)).
No relation to tool-call gating or inference replay.

**in-toto / SLSA**: in-toto is the attestation-statement format
(Statement/Predicate/Subject); SLSA specifies what a supply-chain
attestation must contain ([slsa.dev](https://slsa.dev/blog/2023/05/in-toto-and-slsa)).
Proves a signed build step ran over named artifacts — build/CI-time,
orthogonal to a request-time gateway. Two close-in-spirit 2026 papers:
**Sovereign Execution Broker** (arXiv:2606.20520) enforces
certificate-bound execution contracts (validity windows, revocation,
signed outcomes) via certificates, not bit-exact replay ([arXiv:2606.20520](https://arxiv.org/pdf/2606.20520));
**Right to History**/PunkGo (arXiv:2602.20214) uses RFC 6962 Merkle audit
logs + capability isolation for sub-1.3ms logging, but its abstract does
not address bit-exact verification, weight allowlisting, or nonce
freshness ([arXiv:2602.20214](https://arxiv.org/pdf/2602.20214)).

**TEE-attested inference** (Phala, Marlin/Oyster, Azure confidential GPU
VMs): enclave-signed attestation over inference sessions, e.g. Phala's
"Attested Confidential Inference" gateway ([Phala docs](https://docs.phala.com/phala-cloud/confidential-ai/overview)).
Proves genuine enclave/firmware at attestation time; does not give a
portable, independently replayable digest on a *different* machine — a
hardware-root trust claim, not a spec anyone can rederive. Same
distinction the SAFE-1 memo draws for its own optional TPM check (§2c:
box2 `ehEnable=0`, no vendor EK root, continuity evidence only, per
`2026-09-13-trust2-ek-chain-box2.md`).

## 3. Verifiable inference (zkML / opML / TOPLOC / A2Auth)

**TOPLOC** (arXiv:2501.16007, Prime Intellect): locality-sensitive hashing
over activations, "100x faster validation than generation," detects
tampering with statistical confidence from hash proximity — explicitly
not bit-exact; designed to *tolerate* legitimate hardware/kernel variance,
the opposite of CIS exact-digest replay ([arXiv:2501.16007](https://arxiv.org/abs/2501.16007)).

**zkML (EZKL, Modulus)/opML/zk-OPML**: zkML gives cryptographic soundness
via SNARK circuits but "80 minutes proving time" for a 1M-param model and
TB-PB memory at 7B ([Kudelski](https://kudelskisecurity.com/modern-ciso-blog/zkml-verifiable-machine-learning-using-zero-knowledge-proof)).
opML uses fraud-proof/challenge-period economics instead, 7B model in
32GB RAM ([arXiv:2401.17555](https://arxiv.org/pdf/2401.17555)). Neither
gives an unconditional, standalone bit-exact replay the way
`agent_trace verify` does — zkML is infeasible at CIS scale today, opML's
soundness needs an honest-challenger assumption.

**A2Auth** (arXiv:2603.14332, full treatment in 2026-09-09 report):
defines a `full` bit-exact tier, proves everything below it is
"statistical rather than computational security," names one vendor
(EigenAI, fixed GPU hardware, no public spec) as the sole way to reach it.

**"Tool Receipts, Not Zero-Knowledge Proofs"/NabaOS** (arXiv:2603.10060):
HMAC-signed tool-execution receipts cross-checked against LLM claims,
"94.2% hallucination detection coverage at <15ms" vs zkLLM's "180,000ms"
([arXiv:2603.10060](https://arxiv.org/html/2603.10060)). Proves the tool
returned what was claimed, not that the model's computation was
bit-exact — receipt-of-tool-output, not receipt-of-inference; authors
position it as a cheaper zkML alternative, not an inference-replay
competitor.

## 4. Tamper-evident logs (CT / Trillian / Sigsum) and third-party receipts

**Certificate Transparency + Trillian**: Merkle append-only logs,
O(log n) inclusion/consistency proofs that a log has not forked, reused
for "AI model transparency" ([transparency.dev](https://transparency.dev/)).
**Sigsum** makes signer key-usage transparent, for publishing
reproducibility statements/config/tree heads
([Sigsum summit page](https://transparency.dev/summit2024/sigsum.html)).
Proves inclusion and non-rewriting of a log — exactly the property
SAFE-1's decision-log chain (§2d) and second-verifier log-head check (§4)
need, and exactly what the design memo flags as *missing an external
anchor* today. Says nothing about what the logged entry *means*; adopt
this for anchoring (publish the decision-log head externally, Sigsum-
style or via the ledger as already done), not a competitor.

**"Notarized Agents"** (arXiv:2606.04193): the *receiver* of a tool call
signs a receipt of what it observed (not the agent), encrypted to the
owner, published to a Merkle log with witness cosignatures
([arXiv:2606.04193](https://arxiv.org/abs/2606.04193)). Addresses "agent
lies about its own trace" — a real gap in SAFE-1's current single-machine
log (still a single point of failure per design memo §4). Does not verify
inference; authors concede it cannot stop a receiver that refuses to sign
or colludes with the operator.

## 5. Confused-deputy/TOCTOU/freshness — adjacent 2026 work

Beyond A2Auth and MCP-38, two papers name the exact freshness/binding gap
the SAFE-1 critic flagged: **"Zero-Trust Runtime Verification for Agentic
Payment Protocols"** (arXiv:2602.06345) targets "replay and context-
binding failures" in AP2 — same failure class as SAFE-1's nonce/freshness
and verify-execute-binding gaps, different (payments) domain
([Papers with Code](https://paperswithcode.co/paper/2602.06345)). **"AIP:
Agent Identity Protocol"** (arXiv:2603.24775) targets verifiable
delegation across MCP/A2A — identity/authorization-chain, distinct from
inference-content verification ([arXiv:2603.24775](https://arxiv.org/abs/2603.24775v1)).
**INFERENCE**: no paper found combines (a) bit-exact replay, (b) verify-
execute byte binding, (c) nonce/freshness in one mechanism; each does at
most one.

## 6. Positioning

**Honest claim sentence:** SAFE-1 combines three things that each exist
separately and, per this search, have not been combined into one
request-time tool gate: (1) bit-exact, independently replayable inference
verification (most "verifiable inference" work explicitly trades this away
for speed/cost — TOPLOC and opML both do, A2Auth names it a `full` tier
one closed vendor reaches); (2) byte-for-byte binding of the *forwarded*
tool-call bytes to the receipt's own final-step hash, closing the
verify-then-execute TOCTOU/confused-deputy gap MCP guidance names but does
not cryptographically close ("advisory, not a security boundary" — OWASP);
and (3) a tamper-evident, externally-anchorable decision log in the
Certificate-Transparency tradition, logging *gateway decisions bound to
inference receipts* rather than certificates or generic actions.

**Three closest works:**

1. **A2Auth (2603.14332)** — closest on verification depth; same `full`
   bit-exact tier, but names one closed vendor, no verify-execute binding,
   no weight allowlist, no gateway architecture. We reach `full` from a
   public spec on commodity hardware and add the binding+allowlist+gate.
2. **Notarized Agents (2606.04193)** — closest on log-integrity; solves
   "agent lies about its own trace" via receiver-signed third-party
   receipts where we use independent second-verifier replay (§4 design
   memo); neither combines receiver-notarization with bit-exact replay.
3. **MCP security guidance / OWASP cheat sheet** — closest on naming the
   vulnerability (confused deputy, provenance gaps), but its mitigation is
   authorization/session-scoping, not cryptographic binding of forwarded
   bytes to a verified inference receipt.

**Two claims we must NOT make:**

1. Not "first receipt-gated agent tool gateway" — signed/hash-chained
   agent receipts are a crowded 2026 space (PipeLab, agno #6892,
   AgentPatterns, LangChain, Notarized Agents, NabaOS — full list in the
   09-09 report). Say instead: uncommon is gating on a receipt requiring
   *bit-exact* replay rather than a signed assertion or fuzzy check.
2. Not "proves the tool call was a good idea" or "the model is
   trustworthy." SAFE-1's checks (design memo §5) prove history is
   checkable and tied to an approved weight triple; they cannot prove a
   legitimately-reached decision was correct, safe, or non-malicious
   (design memo threat table row 1: cannot stop a model "tricked into
   legitimately deciding to call a dangerous tool"). Verified != safe.

## Sources

- https://developer.nvidia.com/blog/measuring-the-effectiveness-and-performance-of-ai-guardrails-in-generative-ai-applications/
- https://arxiv.org/pdf/2505.03574 (LlamaFirewall)
- https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html
- https://arxiv.org/pdf/2603.18063 (MCP-38)
- https://arxiv.org/pdf/2512.03180 (AGENTSAFE)
- https://c2pa.org/faqs/
- https://arxiv.org/html/2604.24890v1 (C2PA critique)
- https://slsa.dev/blog/2023/05/in-toto-and-slsa
- https://arxiv.org/pdf/2606.20520 (Sovereign Execution Broker)
- https://arxiv.org/pdf/2602.20214 (Right to History / PunkGo)
- https://docs.phala.com/phala-cloud/confidential-ai/overview
- https://arxiv.org/abs/2501.16007 (TOPLOC)
- https://kudelskisecurity.com/modern-ciso-blog/zkml-verifiable-machine-learning-using-zero-knowledge-proof
- https://arxiv.org/pdf/2401.17555 (opML)
- https://arxiv.org/html/2603.14332v1 (A2Auth)
- https://arxiv.org/html/2603.10060 (Tool Receipts / NabaOS)
- https://transparency.dev/
- https://transparency.dev/summit2024/sigsum.html
- https://arxiv.org/abs/2606.04193 (Notarized Agents)
- https://paperswithcode.co/paper/2602.06345 (Zero-Trust Runtime Verification, AP2)
- https://arxiv.org/abs/2603.24775v1 (AIP: Agent Identity Protocol)
- state/reports/2026-09-13-SAFE1-RECEIPT-GATEWAY-DESIGN.md
- state/reports/2026-09-13-SAFE1-DESIGN-CRITIC.md
- state/reports/2026-09-13-safe1c-e2e-box1.md
- state/reports/2026-09-09-AGENT-RECEIPT-PRIOR-ART-AND-A2AUTH.md
