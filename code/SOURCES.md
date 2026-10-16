# Code sources

All snapshots are working trees exported with `git archive` (no history). Nothing here was fetched from the network during assembly.

| directory | repo | ref | commit | licence at that commit |
|---|---|---|---|---|
| code/cis2-fp | Aefinity-AI/cis2-fp | origin/main | 70d3a834322a607aeaa6de60e4ca0f56696798b2 | none (no LICENSE file); no licence is granted |
| code/cis2-llm | Aefinity-AI/cis2-llm | origin/main | 64a6c851859c5552da67ed447f075bd17121ad38 | none (no LICENSE file); no licence is granted |
| code/cis2-llm-conformance | cis2-llm, branch `cis3-2b` (unmerged) | `conformance/` only | db31cc18c42354a758adbe443e9b91586e978e70 | none; no licence is granted. This is the corporate-LLM conformance suite; the public spec has its own op-level conformance tests. |
| code/cis2-wasm | local-only repo cis2-wasm | main | 5cbb603662322eca718ea209a524690cd1b25784 | none; no licence is granted; the built `.wasm` is left out |
| paper/cis2-fp-paper-draft | cis2-fp, branch `cm/cis2-paper-draft` (unmerged), `docs/paper` only | | 9f2a0dde324aec4e11f59892b9f6cdef1254fa59 | documents: root LICENSE (Apache-2.0) |
| code/patches/*.patch | unmerged branches, as `git diff main...<branch>` (cis2-fp) or against main (others) | see below | see below | follows the parent repo |

Patches (commit at the tip of each branch):

- cis2-fp:cm/gpu3-batched-full: 1c6f592b761354cbd0615bbc81608ffd8e6199be
- cis2-fp:cm/gpu2-batch-int8: d2ead25678b0aae59f307c95017e9aca1cc1ad7b
- cis2-fp:cm/e18b-cuda-portable: a3321fd7e08c261f66efd7ce53385672a01b7d21
- cis2-fp:cm/e23-pinned-sampling: fe80ee85d4eec04c2a738ec051857ab89af4d5ef
- cis2-fp:origin/cm/moat2-sampling-tamper: 2c504bb06c5848d246a751b10ccbdb635f14d0e6
- cis2-fp:origin/cm/e18c-pinned-tree-reduction: 2dc6ba5a2ceb6c890a681c6154970e7bf8f3d4aa
- cis2-llm:cis3-2b: db31cc18c42354a758adbe443e9b91586e978e70
- cis2-spec:cm/seeded-sampling: 57f157de336419198d067210a2abffffcdf9a4d4

Seeded sampling draft: `code/patches/cis2-spec__seeded-sampling.patch` is `git format-patch main..HEAD` from the local `cm/seeded-sampling` branch of cis2-spec (draft section 14, informative, five-build candidate rows).

Not snapshotted, by design:

- `cis2_check` (local path ~/projects/cis2_check): its remote is the public cis2-spec repo, commit a76a579; it is a clone of the public spec, so it is not duplicated. Public spec: https://github.com/Aefinity-AI/cis2-spec (licence: Apache-2.0, matched by `LICENSE` in this archive for docs).
- The public op-level conformance tests (`tests/conformance`, `vectors/coverage-v1`) are in cis2-spec.
- `cis2-llm/licensing/` (EULA, licence tool, internal pricing), `docs/USE-CASES.md` and `server/licensing.py` were removed as internal business material; `server/` will not run unmodified without the licensing module.
- Model weights: none included. Pinned upstream: HuggingFaceTB/SmolLM2-135M on Hugging Face, `model.safetensors` sha256 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1 (from the public EXPECTED_DIGESTS.md). Other models named in the lab folders (SmolLM2-360M, Qwen2.5-0.5B, Qwen3-0.6B, llama-160m, Qwen2-7B) are fetched from their upstream Hugging Face repos; digests are in the lab records.

## Licence note

Code under code/ is published for reference; no licence is granted for it at this time. Documentation and results are under the root LICENSE (Apache-2.0).

Also removed from code/cis2-llm on 2026-10-16: `PROGRAMME.md`, `docs/CLAIMS.md` and `deploy/` (programme and deployment material, not CIS-2 lab record). The conformance suite and source stay.
