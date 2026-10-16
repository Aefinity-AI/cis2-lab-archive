# E18b/E18c GPU run — CIS-2 receipt reproduced bit-for-bit on a Tesla P100 (2026-09-06)

**Headline.** The CIS-2 v0.3b fp32 reference, built with nvcc for a Kaggle P100 (sm_60,
CUDA 12.8, `-fmad=false -ftz=true -prec-div=true -prec-sqrt=true`), reproduced the CPU
receipt digests at 16 and 128 generated tokens and a byte-identical 16-token trace. The
same run rebuilt the host reference with Kaggle's g++ as a control (PASS) and passed the
SASS gate (0 FFMA in the dot/sum kernels). The v0.4 CANDIDATE tree reduction also matched
its CPU-tree digests on the GPU.

| check | verdict |
|---|---|
| host-gcc control, Kaggle CPU, 16 / 128 tok | PASS / PASS (16-tok trace byte-identical) |
| nvcc P100 sequential, 16 / 128 tok | PASS / PASS (16-tok trace byte-identical) |
| nvcc P100 tree CANDIDATE, 16 / 128 tok | PASS / PASS (16-tok trace byte-identical) |
| SASS no-FMA gate (dot/sum kernels) | PASS, 0 FFMA; softmax 47 FFMA = `-prec-div` division refinement, reported not gated |

Digests: sequential d82743059d1db929… (16) / 22f69ad87a615d66… (128); tree
3f3b1ffceca02e8e… (16) / 112661fbfcb11440… (128). These are the same expected values the
CPU work established on 2026-09-03.

**Scope.** One GPU generation (Pascal), one compiler version, one model, correctness only.
No timing, no Ampere/Hopper, no tensor cores. Identity spans now: x86-64 AVX2, x86-64
scalar (box2), aarch64, QEMU, and a CUDA GPU, all from the same spec.

**Why it matters for the edge product.** The certification story ("we can tell you whether
your accelerator reproduces the reference receipt") now has a worked GPU example, which is
what a customer with a GPU box would ask for first.

**Provenance.** cis2-fp branch `cm/e18c-kaggle-both-kernels`, `docs/E18B_GPU_RESULT.md`,
log + JSON under `hardware_logs/e18b-gpu-kaggle/`. Kaggle kernel `aefinityaiinc/e18b-gpu`
v5 (v1–v4 were harness failures: new `/kaggle/input/datasets/<owner>/<slug>` mount path,
overlay packaging; v2 already showed the sequential GPU PASS).

**Open.** PUBLISH? filed in NEEDS: the result is a spec/results item (public by default)
but it touches the v0.4 tree order and the private kernel port; needs adversarial review
(cm-verifier re-deriving the expected digests from the CPU trace files) before anything
leaves the private repo.
