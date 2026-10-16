# W8: denormal/FTZ count on rust-2b checkpoints (box1)

2026-10-16, filler item (QUEUE.md line 21), no EV card, no ledger entry.

rust-2b (Rust/Burn vs PyTorch training-port comparison lab) is DONE and
merged (cis2-spec PR #42, commit e8056630). This item characterizes the
numerical content of the final checkpointed params/grads from the
CHECK-PASS run on box1, not a new lab.

## Checkpoint files used

Final, verified (`CHECK PASS`, see `~/legs/rust2b-run-box1/check/check_equal.log`)
params/grads from the box1 run (`~/legs/rust2b-run-box1/`, harvested,
RESULT: OK, rows=20, failed=0). Format: raw flat little-endian float32,
no header (Burn's own param-dump convention for this harness, matched
byte-for-byte in param count by the PyTorch reference dump). n_params =
1841280 per arm (confirmed in `B.json`/`T.json` and by file size
7365120 bytes = 1841280 * 4).

| file | sha256 |
|---|---|
| B_params1.bin (Burn, trained params) | 71845c0704a0b41cc46272855639e0cb276d2feef4c612763ee6cf3b6f556b5c |
| T_params1.bin (PyTorch, trained params) | 70c2269fafeb0c91a7c4236eed42f5b6616a4426347c5d248dc575de9ac7279f |
| B_grads1.bin (Burn, grads) | 167fe93f129536fd80b322493424ae5486f8996c8cc6c10906def0a1611d4115 |
| T_grads1.bin (PyTorch, grads) | 0d0a9f6d9ca656e5c10ce9967f243702a614deab4fe0c613a8911ef86323c7ff |

Path: `~/legs/rust2b-run-box1/check/{B,T}_{params,grads}1.bin` on box1
(this box).

## Method

Loaded each file as a flat `<f4` numpy array (1,841,280 elements each).
Counted exact zeros and subnormals (`0 < |x| < FLT_MIN`, FLT_MIN =
1.1754943508222875e-38 for f32). A value counted as subnormal/denormal
is exactly the set that would be truncated to 0.0 if flush-to-zero (FTZ)
were enabled on denormal results, so "denormal count" and "FTZ-affected
count" coincide here (no separate DAZ-on-input case needed since these
are read as plain arrays, not fed through an FTZ-enabled FPU op).

Script: `~/rust2b_denormal_count.py` (self-contained, numpy only).

Command to reproduce:
```
python3 ~/rust2b_denormal_count.py \
  ~/legs/rust2b-run-box1/check/B_params1.bin \
  ~/legs/rust2b-run-box1/check/T_params1.bin \
  ~/legs/rust2b-run-box1/check/B_grads1.bin \
  ~/legs/rust2b-run-box1/check/T_grads1.bin
```

## Result

| file | n_params | zeros | denormals | frac denormal |
|---|---|---|---|---|
| B_params1.bin | 1,841,280 | 2 | 0 | 0.0 |
| T_params1.bin | 1,841,280 | 0 | 0 | 0.0 |
| B_grads1.bin | 1,841,280 | 2 | 0 | 0.0 |
| T_grads1.bin | 1,841,280 | 0 | 0 | 0.0 |
| **TOTAL (4 tensors)** | **7,365,120** | 4 | **0** | **0.0** |

**Zero denormal/FTZ-affected values** across all four checked
params/grads dumps (both arms, trained weights and their gradients).
The 4 exact zeros in the Burn arm (2 in params, 2 in grads, none in the
PyTorch arm) are ordinary exact-zero entries (e.g. a bias or masked
position), not denormals, and are already untouched by FTZ.

This is consistent with `OURS.md` row M01 (FTZ/DAZ spec-mutation did NOT
change the digest on the current vector) — the model's working range for
this lab (small transformer-ish MLP/attention block, 200 steps, loss
~4.7-5.5) never produces subnormal magnitudes in trained params or
gradients, so FTZ/DAZ hardware flags are a non-issue for rust-2b's
numerical conformance claims. No further action needed; nothing to tune
or flag.

## Note on scope

Only the final CHECK-PASS checkpoint pair was inspected (the one that
fed the merged PR #42 result). Earlier/smoke/intermediate dumps under
`~/scratch-rust2b/*` and other `~/legs/rust2b-*-box1/` dirs are
byte-identical in `n_params` and structure (same harness) but were not
exhaustively swept — not needed since the result (0 denormals) is
already a clean negative and the lab's own spec-mutation test (M01)
independently corroborates FTZ/DAZ has no effect on this vector.
