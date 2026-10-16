# Where stock PyTorch stops on the Celeron N4020 (diagnostic, 2026-10-04)

Status: DIAGNOSTIC after the rust-5 record. No pass mark, no timing, one host (box2), one run. It narrows the
FRAMEWORK finding in RESULT.md ("the full K2+K5 process ended with Illegal instruction"); it does not change the
rust-5 label. Published 2026-10-16 as part of the CIS-2 archive.

Host: box2, Intel Celeron N4020 (SSSE3, SSE4.1, SSE4.2; no AVX). Wheel: torch 2.14.0+cpu (stock), Python 3.13.
Job: feeder job `torch-sigill-diag-box2`, script `~/feed-payload/jobs/torch-sigill-diag.sh`; each step in its own
process under `python -X faulthandler`. Raw outputs: `torch-sigill-diag-box2/` next to this file.

| Step | What ran | Exit |
|---|---|---|
| s1 | import torch, print build settings and quantized engines | 0 |
| s2 | fp32 `Linear` forward, 256x256, 576x1536, 2048x2048 | 0, 0, 0 |
| s3 | `quantize_dynamic` of a `Linear` (build, no forward) | 0 |
| s4 default | dynamic-int8 `Linear` forward, default engine (`onednn`) | 132 (Illegal instruction) |
| s4 onednn | the same with the engine set to `onednn` | 132 (Illegal instruction) |
| s4 qnnpack | the same with the engine set to `qnnpack` | 0 |
| s4 x86, fbgemm | engines not offered by this wheel (`supported_engines = ['qnnpack', 'onednn']`) | not run |
| s5 | plain int8 to int32 matmul | 0 |

Fault location (faulthandler): `torch/ao/nn/quantized/dynamic/modules/linear.py`, line 58 in `forward`, under
`torch/_ops.py` `__call__`.

Reading, limited to what ran:
- fp32 inference with the stock wheel works on this CPU. The crash is not "PyTorch does not run on the N4020".
- The dynamic-int8 linear forward ends with an illegal instruction when the quantized engine is `onednn`, which
  is the default engine of this wheel on this machine. With `qnnpack` selected the same forward completes.
- So in rust-5 the K2 fp32 arm was lost on box2 and box3 because it shared a process with the K5 int8 arm.
  A harness that runs K2 alone, or sets the engine to `qnnpack`, would have produced K2 numbers there.
- Not shown: which instruction faults (no debugger on the box), whether other torch versions behave the same,
  whether box3 behaves the same (same CPU model, not run), and nothing about speed.

For a client on old or low-power x86 without AVX: a stock PyTorch install can pass an fp32 smoke test and still
stop on the int8 path. Our C and Rust kernels in rust-5 ran on all five machines with bit-equal outputs.
