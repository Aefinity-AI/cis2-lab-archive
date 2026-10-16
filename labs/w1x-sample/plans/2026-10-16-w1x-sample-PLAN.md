# w1x-sample plan (2026-10-16)
Payload ~/feed-payload/cis2-sample (gpu/cis2_sample.h sha 4f2e1c88cad66517, patched cis2_host.cpp, ref/sample_ref.py, jobs/cis2-sample.template.sh; builder RESULTS.md records 12 clause ambiguities and the choices made).
Legs: cis2-sample-w3, cis2-sample-w4, cis2-sample-w2 via cm-feed (SM=none); hq row = cis2-sample-hq (host + CUDA sm_61) queued after the tamper leg. cm-compare across hosts.
On MET: publish score card, then cis2-spec PR with section 14 as a v0.4-draft INFORMATIVE section, KATs, toy vector and the model vector marked CANDIDATE until a second independent implementation agrees. Clause draft: state/reports/2026-10-16-CIS2-SEEDED-SAMPLING-CLAUSE-DRAFT.md; prior art: state/reports/prior-art/seeded-sampling.md.
