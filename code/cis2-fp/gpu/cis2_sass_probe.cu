// gpu/cis2_sass_probe.cu — E18c: a minimal, self-contained CUDA
// translation unit whose only purpose is to put the pinned reduction
// kernels (§5.1/§5.3 sequential, and the v0.4 CANDIDATE tree variants)
// through nvcc for real, so their SASS can be inspected for fused
// multiply-add instructions. It depends on nothing but cis2_math.h — no
// weights, no JSON, no safetensors, no host driver — specifically so
// `nofma-cuda` stays cheap to compile and its SASS stays small enough to
// read function-by-function.
//
// This file is NEVER LINKED into an executable and NEVER RUN: `make
// nofma-cuda` compiles it to a relocatable device object (`nvcc -c`) and
// disassembles that object directly with `cuobjdump`/`nvdisasm`. No
// physical GPU is required for either step — only the offline compiler
// and disassembler, both part of the CUDA toolkit. See gpu/README.md §8b.
//
// Six kernels, one per reduction primitive this leg cares about:
//   k_dot_seq / k_sum_seq       — v0.3b's untouched sequential reduction
//   k_dot_tree / k_sum_tree     — v0.4 CANDIDATE's pinned tree reduction
//   k_softmax_seq / k_softmax_tree
//     — softmax contains one genuine division (`logits[i] / denom`);
//       -prec-div=true division on Turing (no hardware DIV instruction)
//       is a MUFU.RCP + Newton-Raphson-refinement sequence that legally
//       contains FFMA — the documented exception (see gpu/README.md §1,
//       "-prec-div/-prec-sqrt internal FFMA"). The other four kernels
//       contain NO division and NO sqrt, so they are held to a strict
//       zero.

#include "cis2_math.h"

#define N 200  // > 6*CIS2_TREE_BLOCK: exercises multiple full blocks plus
                // a ragged tail in every tree kernel below.

extern "C" __global__ void k_dot_seq(const float *a, const float *b, float *out) {
  *out = cis2_dot_seq(a, b, N);
}

extern "C" __global__ void k_sum_seq(const float *a, float *out) {
  *out = cis2_sum_seq(a, N);
}

extern "C" __global__ void k_dot_tree(const float *a, const float *b, float *out) {
  *out = cis2_tree_dot(a, b, N);
}

extern "C" __global__ void k_sum_tree(const float *a, float *out) {
  *out = cis2_tree_sum(a, N);
}

extern "C" __global__ void k_softmax_seq(float *scores) {
  cis2_softmax_seq(scores, N);
}

extern "C" __global__ void k_softmax_tree(float *scores) {
  cis2_softmax_tree(scores, N);
}
