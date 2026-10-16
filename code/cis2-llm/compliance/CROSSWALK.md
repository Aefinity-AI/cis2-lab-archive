# CIS-2 LLM — control crosswalk (leg LLM-2). Published 2026-10-16 as part of the CIS-2 archive.

2026-09-17. Read-only research pass. CIS-2 artifacts referenced below (spec, verifier, receipt
fields) are defined in `~/projects/cis2-spec/docs/CIS2_SPEC_v0.3b.md` and
`~/projects/cis2-spec/README.md`; the receipt-gated gateway and async replay-DENY behavior are
defined in `alice-aegis` safe-1..safe-11 (see
`~/.claude/projects/-home-<user>/memory/safe1-receipt-gateway.md`); TPM attestation
is `~/.claude/projects/-home-<user>/memory/measured-inference-tpm.md`. Server/
gateway/deploy components named in `PROGRAMME.md` (`server/`, `gateway/`, `deploy/`) are v0.1
SCAFFOLD TARGETS per leg LLM-1/LLM-5 and have not been built or re-run by this leg — rows below
that cite a not-yet-built server/gateway feature are marked NOT YET BUILT, distinct from spec/
verifier artifacts that already exist and are re-usable today.

Sourcing method: EU AI Act quotes below were live-fetched 2026-09-17 from euaiact.com, a secondary
mirror/summary site for Regulation (EU) 2024/1689 — not the EUR-Lex Official Journal text itself
(flagged per row; treat as "closely paraphrased/summarized," not verbatim Official Journal text,
unless marked otherwise). SOC 2 quotes are extracted with `pdftotext` from the AICPA 2017 Trust
Services Criteria (with 2022 revised points of focus) PDF, mirrored at arpio.io — this is the
actual document text, not a summary, confirmed by direct extraction. NIST AI RMF quotes are from
NIST's AIRC (AI Resource Center) pages, a NIST-run resource site. ISO/IEC 42001 text is NOT
independently available — the standard is paywalled; the one row below is a compliance vendor's
(ISMS.online) paraphrase of the control's intent, flagged accordingly. No claim below uses the
word "first," per standing wording rule.

---

## EU AI Act (Regulation (EU) 2024/1689)

| # | Control | Requirement (paraphrase/quote + citation) | CIS-2 artifact | Coverage |
|---|---|---|---|---|
| 1 | Art. 12(1) — automatic event logging | "High-risk AI systems shall technically allow for the automatic recording of events (logs) over the lifetime of the system." — live-fetched [euaiact.com/article/12](https://www.euaiact.com/article/12), 2026-09-17 | Receipt log: every inference call appends a hash-chained entry (receipt id, full-logit digest per decode step, chained to prior entry) per `CIS2_SPEC_v0.3b.md` §12. Independently re-verifiable via `verify2`/`verify3`. | COVERED for the model-execution slice only |
| 2 | Art. 12(2) — logs must support risk/incident identification and post-market monitoring | Logging must enable recording of events relevant to identifying risk situations, substantial modification, and post-market monitoring, per euaiact.com/article/12 summary, live-fetched 2026-09-17 | A digest mismatch on replay is a concrete, machine-detectable "risk situation" signal (compute drifted from the recorded run) usable as one input to post-market monitoring. | PARTIAL — receipts log model arithmetic only, not the surrounding data pipeline, deployment context, or downstream decision outcome that Art. 12(2)'s risk-monitoring scope also covers |
| 3 | Art. 12(3) — biometric-system logging minimums (period, reference DB, input data, verifier identity) | Per euaiact.com/article/12, live-fetched 2026-09-17: minimum log fields include usage period with timestamps, reference database used, input data yielding matches, verifier identity per Art. 14(5) | NOT COVERED — needs application-layer logging fields (reference DB identity, verifier identity) added to the receipt schema; CIS-2's current receipt fields (spec §12) are compute-digest-only, not domain-specific metadata | NOT COVERED — needs X: biometric-specific metadata fields in the receipt schema (LLM-1/LLM-5 scope) |
| 4 | Art. 13 — transparency: instructions enabling deployers to interpret output, disclosing characteristics/limitations | "designed and developed...to ensure that their operation is sufficiently transparent to enable deployers to interpret a system's output," plus 6 categories of required instructions-for-use content — live-fetched [euaiact.com/article/13](https://www.euaiact.com/article/13), 2026-09-17 | The public CIS-2 spec (`cis2-spec` README + `CIS2_SPEC_v0.3b.md`) is itself falsifiable, open documentation of exactly how the forward pass computes outputs — independently reproduced by 3+ clean-room implementations (`cis2-verify-cleanroom.md`). | PARTIAL — Art. 13's core ask is behavioral disclosure (accuracy metrics, known risks, performance by subgroup, intended purpose) which the spec does not provide; CIS-2 strengthens the "how the arithmetic works" sliver only |
| 5 | Art. 14(1)/(4)(a) — human oversight, ability to understand capacities/limitations and to override | "designed and developed...that they can be effectively overseen by natural persons," and persons must be enabled "to properly understand the relevant capacities and limitations" — live-fetched [euaiact.com/article/14](https://www.euaiact.com/article/14), 2026-09-17 | A receipt lets an overseer independently re-run the exact recorded inference offline (`verify2` CLI, spec §11) and confirm the system produced the logged output, rather than trusting an unverifiable log line. | WEAK — Art. 14 is fundamentally about interface design and override authority (stop-button, disregard/reverse output), which CIS-2 does not touch at all; it only strengthens confidence in what the record says happened |
| 6 | Art. 15(1) — accuracy, robustness, cybersecurity; consistent performance throughout lifecycle | "designed and developed...to achieve an appropriate level of accuracy, robustness, and cybersecurity" and to "perform consistently" throughout the lifecycle — live-fetched [euaiact.com/article/15](https://www.euaiact.com/article/15), 2026-09-17 | Chained receipt digests prove the inference arithmetic is invariant across ISA/compiler/hardware (bit-identical across AVX2/scalar x86/aarch64/QEMU/Kaggle P100, per E18b/E18c precedent) — any change that alters logit bits changes the digest immediately. | PARTIAL — "accuracy" in Art. 15 is a statistical/task-performance concept (declared metrics on a test set); CIS-2 proves reproducibility of computation, not correctness. Adversarial robustness/cybersecurity (data poisoning, model poisoning) is explicitly out of scope per spec's own "Known gaps" |
| 7 | Art. 53(1)(a) — GPAI technical documentation (Annex XI) | "Draw up and keep up-to-date the technical documentation of the model, including its training and testing process," minimum content per Annex XI — live-fetched [euaiact.com/article/53](https://www.euaiact.com/article/53), 2026-09-17 | A versioned, published spec plus independently-verified reference implementations is a concrete technical-documentation artifact for the inference-engine determinism sub-item. | PARTIAL — Annex XI is primarily about training data, compute, energy use, model architecture at the model level, not numeric determinism of the forward pass; CIS-2 documents one narrow slice |
| 8 | Art. 53(1)(b) — GPAI downstream information (Annex XII) | "Draw up, keep up-to-date and make available information and documentation to providers of AI systems" integrating the model, per Annex XII — live-fetched euaiact.com/article/53, 2026-09-17 | Same spec + verifier artifact, handed downstream, gives integrators a way to independently confirm the model's numeric behavior rather than trusting prose claims. | PARTIAL — same gap as row 7 |
| 9 | Annex IV technical documentation — validation/testing methods and metrics | Annex IV requires description of validation/testing procedures and metrics used (per 2026-09-13 regulatory-evidence pass, sourced from a search summary of artificialintelligenceact.eu/annex/4 — NOT independently re-fetched this session; thinner sourcing, flagged) | A CIS-2 conformance run against the pinned test vector (`EXPECTED_DIGESTS.md`) is a concrete, reproducible validation/testing artifact for the inference-engine sub-item. | PARTIAL (sourcing thinner — Annex IV text not independently re-fetched 2026-09-17) |

---

## SOC 2 Trust Services Criteria (AICPA 2017 TSC, 2022 revised points of focus)

Extracted 2026-09-17 by `pdftotext` from the AICPA TSC PDF (mirrored at arpio.io) — actual document
text, confirmed by direct extraction, not a summary.

| # | Criterion | Requirement (document text) | CIS-2 artifact | Coverage |
|---|---|---|---|---|
| 10 | CC1.1 (governance) | "COSO Principle 1: The entity demonstrates a commitment to integrity and ethical values." | Organizational — no product artifact maps to this; it is about entity culture/tone-at-the-top. | NOT COVERED — organizational, needs a policy/HR control, not a product feature |
| 11 | CC7.1 (detection/monitoring) | "the entity uses detection and monitoring procedures to identify (1) changes to configurations that result in the introduction of new vulnerabilities, and (2) susceptibilities to newly..." | A receipt digest mismatch is a detection signal for one class of "configuration change" — a hardware/toolchain change that alters model arithmetic — but this is a narrow slice of CC7.1's security-configuration-drift scope. | PARTIAL — receipts detect *compute* drift, not the vulnerability-scanning/patch-management scope CC7.1 is written for |
| 12 | CC7.2 (vulnerability scans) | "Conducts Vulnerability Scans — The entity conducts vulnerability scans designed to identify potential vulnerabilities or misconfigurations on a periodic basis..." | NOT COVERED — CIS-2 is not a vulnerability scanner. | NOT COVERED — needs a separate vuln-management tool/process |
| 13 | CC7.3 (detection policies/tools; identify anomalies) | "Implements Detection Policies, Procedures, and Tools — Detection policies and procedures are defined and implemented and detection tools are implemented on infrastructure and software to identify anomalies in the operation or unusual activity" | The verifier (`verify2`/`verify3`) re-executing a receipt and flagging a digest mismatch is exactly a "detection tool...to identify anomalies in the operation" for the inference-computation slice of the system. | PARTIAL — strong fit for compute-level anomaly detection; does not cover infra/network anomaly detection generally |
| 14 | A1.2 (availability — backup/recovery infra) | "The entity authorizes, designs, develops or acquires, implements, operates, approves, maintains, and monitors environmental protections, software, data backup processes, and recovery infrastructure..." | The hash-chained receipt log, if backed up (per `PROGRAMME.md` LLM-7 `backup-drives.sh` to two external drives), is itself a recoverable, tamper-evident audit record. | PARTIAL — backup of the receipt log is one input to A1.2; the criterion covers the whole system's availability posture, which CIS-2 is not |
| 15 | C1.1 (confidentiality) | "The entity identifies and maintains confidential information to meet the entity's objectives related to confidentiality." | Organizational — not a CIS-2 product feature; receipts could themselves contain sensitive prompt/output content requiring separate access controls. | NOT COVERED — needs a data-classification/access-control policy around receipt contents |
| 16 | PI1.3 (processing — records of input activity) | "Creates and Maintains Records of System Inputs — Records of system input activities are created and maintained completely and accurately in a timely manner." | A receipt's recorded input digest (prompt/context hash per spec §11) is a complete, accurate, timely record of what was fed to the model for that call. | COVERED for the model-input slice |
| 17 | PI1.4 (processing — records of processing activity, error detection) | "Records System Processing Activities — System processing activities are recorded completely and accurately in a timely manner." / "Detects and Corrects Production Errors — Errors in the production process are detected and corrected in a timely manner." | The per-decode-step logit digest is exactly a complete, accurate record of processing activity; a chain-verification FAIL is the error-detection half (though "correct" is a downstream human/ops action, not automated by CIS-2). | COVERED (record half); PARTIAL (correction is procedural, outside CIS-2) |
| 18 | PI1.5 (processing — output completeness/accuracy records) | "Creates and Maintains Records of System Output Activities — Records of system output activities are created and maintained completely and accurately in a timely manner." | The receipt's final-output digest and chained log entry is a complete, accurate, timely output record. | COVERED for the model-output slice |
| 19 | CC9.1/CC9.2 (risk mitigation, vendor management) | Not extracted in full this session (page located, text not quoted) — general risk-identification/vendor-risk criteria. | Not assessed this session. | NOT ASSESSED — follow-up needed |

**SOC 2 honest verdict.** Most SOC 2 criteria (CC1–CC5, CC7.2, C-series, A-series beyond the
backup-artifact sliver) are organizational — they describe governance, HR, vendor management, and
infrastructure practices a company must run, not a software feature a product ships. CIS-2's real
SOC 2 relevance is narrow and genuine: it is strong, verifiable evidence for the Processing
Integrity criteria (PI1.3–PI1.5, "complete and accurate records of input/processing/output
activity") and a plausible input to CC7.3 (anomaly detection) for the model-computation slice of a
system. It cannot, by itself, make any company SOC 2 compliant — a real SOC 2 Type II report
requires an independent CPA-firm auditor, a full set of organizational policies (CC1–CC6, CC9,
A1.1, C1.2), and typically a 6–12 month observation period during which the auditor tests
operating effectiveness of ALL applicable controls, not just processing integrity.

---

## ISO/IEC 42001:2023 (AI management systems)

| # | Control | Requirement (paraphrase — standard itself is paywalled, not independently fetched) | CIS-2 artifact | Coverage |
|---|---|---|---|---|
| 20 | Annex A.6.2.8 — AI system recording of event logs | Per ISMS.online's control summary (fetched 2026-09-17, a compliance vendor's paraphrase, not the ISO standard's own text): "The organisation shall determine at which phases of the AI system life cycle event log recording is enabled." | A CIS-2 receipt log is exactly an enabled event-logging mechanism for the inference-execution phase of the AI system lifecycle. | PARTIAL (thin sourcing — ISO standard text itself not available without purchase; paraphrase only) |

**ISO 42001 honest verdict.** ISO/IEC 42001 is a management-system standard (like ISO 27001): an
organization is certified for having a documented AI-management system across the full lifecycle
(roles, resourcing, risk assessment, supplier controls, monitoring), audited by an accredited
certification body. A receipt is useful audit evidence for one control (A.6.2.8, event logging) but
cannot stand in for the certification, which requires the full management-system documentation and
an accredited external audit. No primary ISO clause text was available to quote in this session —
this row rests on a commercial compliance vendor's summary, a real sourcing limitation.

---

## NIST AI Risk Management Framework (AI RMF 1.0) + Generative AI Profile

Quotes below are from NIST's own AIRC (AI Resource Center) pages, live-fetched 2026-09-17.

| # | Subcategory | Requirement (NIST text) | CIS-2 artifact | Coverage |
|---|---|---|---|---|
| 21 | Measure 2.1 | "Test sets, metrics, and details about the tools used during TEVV are documented." | A CIS-2 conformance run's pinned test vector, digest, and verifier tool (`verify2`) is exactly this kind of documented TEVV detail for the inference-engine component. | COVERED for the inference-engine testing sub-item |
| 22 | Measure 2.4 | "The functionality and behavior of the AI system and its components...are monitored when in production." | Receipt issuance + periodic re-verification in production is a concrete monitoring mechanism for the model-component slice. | PARTIAL — covers compute-behavior monitoring only, not the full system (data pipeline, downstream decisions) |
| 23 | Manage 4.1 | "Post-deployment AI system monitoring plans are implemented, including mechanisms for capturing and evaluating input from users..." | A receipt-gated gateway (alice-aegis safe-7 async pattern, ported per PROGRAMME.md LLM-5, NOT YET BUILT in cis2-llm) is a candidate mechanism for capturing verified action records post-deployment. | NOT YET BUILT in cis2-llm (exists as a working prototype in alice-aegis; not yet ported per LLM-5) |
| 24 | Manage 4.3 | "Incidents and errors are communicated to relevant AI actors... Processes for tracking, responding to, and recovering from incidents and errors are followed and documented." | A verifier FAIL (digest mismatch) is a documented, trackable incident signal, but CIS-2 has no built notification/communication workflow. | NOT COVERED — needs an incident-communication procedure/integration, not just a detection signal |

**NIST AI RMF honest verdict.** The RMF is voluntary guidance, not a binding regulation. Its center
of gravity — bias, safety, fairness, most of MAP and GOVERN — is untouched by CIS-2. The narrow,
genuine fit is inside MEASURE (documented TEVV, production monitoring of system behavior): a CIS-2
receipt is a stronger, narrower reproducibility instrument than what MEASURE typically asks for
(bit-exact vs. statistical/aggregate evaluation reproduction).

---

## Meets-or-exceeds verdict and what a real audit still needs

**What CIS-2 genuinely gives a buyer today (verified/sourced above):**
- A verifiable, hash-chained, cryptographically non-repudiable record of exact model-execution
  arithmetic (EU AI Act Art. 12 logging sliver; SOC 2 PI1.3–PI1.5; NIST Measure 2.1/2.4; ISO
  A.6.2.8 event-log mechanism).
- A stronger reproducibility guarantee than typical "statistical replay" — bit-identical across
  AVX2/scalar x86/aarch64/QEMU/Kaggle GPU — which is directly useful evidence for Art. 15's
  "consistent performance" and SOC 2's processing-integrity "complete and accurate" language.
- Optional TPM-rooted attestation (box2 EK/AK chain) giving hardware-anchored provenance beyond a
  software-only log.

**What it does not give, and never will by itself:**
- Proof of correctness, fairness, non-discrimination, or safety of any output (repeated per
  `PROGRAMME.md` line 19; every row above marks this explicitly).
- Any of the organizational scaffolding SOC 2 (CC1–CC6, CC9), ISO 42001 (full management system),
  or an EU AI Act conformity assessment actually require: governance policies, risk-management
  process, vendor/supplier controls, incident-response procedures, human-oversight interface
  design, training-data documentation, or bias/accuracy testing.

**What would still be needed for a real SOC 2 Type II:**
1. An independent, licensed CPA firm as auditor (SOC 2 reports can only be issued by a CPA firm
   under AICPA attestation standards — this is not something CIS-2 or Aefinity can self-certify).
2. A 6–12 month observation period during which the auditor tests operating effectiveness of ALL
   applicable Trust Services Criteria the company selects into scope (not just the Processing
   Integrity criteria CIS-2 supports well).
3. Full organizational policy documentation: access control (CC6), change management (CC8), risk
   assessment (CC3), vendor management (CC9), incident response, HR/background-check procedures
   (CC1) — none of which CIS-2 provides.

**What would still be needed for an EU AI Act conformity assessment (high-risk system):**
1. A conformity assessment body (for most high-risk categories, self-assessment against harmonized
   standards is permitted; Annex III point 1 biometric systems and certain others require a
   notified body) — CIS-2 is evidence submitted *to* that process, not the process itself.
2. The full Annex IV technical documentation package (design, data governance, risk management
   system, human-oversight measures, accuracy/robustness testing results) — CIS-2 covers only the
   inference-determinism sub-item of this package.
3. A registered quality management system (Art. 17) and post-market monitoring plan (Art. 72) —
   organizational requirements CIS-2 does not provide.

---

## Sources (live-fetched or extracted 2026-09-17 unless noted)
- [euaiact.com/article/12](https://www.euaiact.com/article/12)
- [euaiact.com/article/13](https://www.euaiact.com/article/13)
- [euaiact.com/article/14](https://www.euaiact.com/article/14)
- [euaiact.com/article/15](https://www.euaiact.com/article/15)
- [euaiact.com/article/53](https://www.euaiact.com/article/53)
- AICPA 2017 Trust Services Criteria (with 2022 revised points of focus) PDF, mirrored at
  [arpio.io/wp-content/uploads/2020/08/trust-services-criteria.pdf](https://arpio.io/wp-content/uploads/2020/08/trust-services-criteria.pdf)
  — text extracted locally with `pdftotext`, not a summary
- [isms.online — ISO 42001 A.6.2.8](https://www.isms.online/iso-42001/annex-a-controls/a-6-ai-system-life-cycle/a-6-2-8-ai-system-recording-of-event-logs/)
  (compliance-vendor paraphrase, ISO standard itself paywalled)
- [airc.nist.gov/airmf-resources/airmf/5-sec-core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- Annex IV summary (NOT independently re-fetched 2026-09-17 — carried over from
  `<root>/state/reports/2026-09-13-CIS-REGULATORY-EVIDENCE-MAP.md`,
  itself sourced from a search-result summary of artificialintelligenceact.eu/annex/4)
- Internal artifacts: `~/projects/cis2-spec/docs/CIS2_SPEC_v0.3b.md`, `~/projects/cis2-spec/README.md`,
  `~/projects/cis2-spec/EXPECTED_DIGESTS.md`,
  `~/.claude/projects/-home-<user>/memory/safe1-receipt-gateway.md`,
  `~/.claude/projects/-home-<user>/memory/measured-inference-tpm.md`,
  `~/.claude/projects/-home-<user>/memory/moat3-headtohead.md`,
  `~/.claude/projects/-home-<user>/memory/cis2-verify-cleanroom.md`
