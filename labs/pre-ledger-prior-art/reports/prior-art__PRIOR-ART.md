# PRIOR-ART register (created 2026-10-16 from the two sweeps; one line per source; V = opened this session by the sweep agent, R = reported only)

| id / source | what it shows | tag | our labs it touches |
|---|---|---|---|
| 2609.25624 ReproFuse | fused-upcast GEMM, bitwise-identical linear layers across Ampere/Ada/Hopper; 1.17-3.1x faster than prior | V | W1, A4, standards memo |
| 2601.07239 Stochastic CHAOS | argues against deterministic inference (hides uncertainty) | V | framing: determinism for audit/replay, not for serving |
| 2601.17768 LLM-42 | decode-verify-rollback; batch-invariant GEMM 63 % slower at peak; det. mode 24-36 % slower | V | P1, rust-5 |
| 2605.30218 MarginGate | batch-induced flips 0.3-1.3 % of steps (GPU BF16), risk at low top-2 margin; verifier fires 15-19 % | V | W3, sv-5d |
| 2506.09501 | BF16 decision flips with batch size | V | sv-5c/d, H1 |
| 2606.03019 | reproducibility as copyleft (licensing) | V | standards memo only |
| 2606.29581 | AWQ INT4 within ~1.6pp FP16 for 7/8 models; SmolLM3-3B ASR 34.5->44.1; flip 41.9 % at T=1 | V | qsafe-1, W7, H2 |
| 2606.10154 | 51-row GGUF/AWQ/GPTQ matrix: quality stable, refusal down 12-68pp in 9 rows | V | qsafe-1, qs-03, tm-6 |
| 2606.09864 | KV-cache quant: Mistral-7B loses 15.2 % refusals | V | W7 |
| 2405.18137 | benign in FP, malicious once quantized (supply chain) | R | H8, qs-03 |
| 2202.06539 Kandpal, 2107.06499 Lee | dedup reduces memorisation super-linearly | V/R | priv-1/1b DUPLICATE, H3 |
| 2012.07805 | training-data extraction | R | S2 |
| 2606.19544, 2609.08236, 2306.05685 | judge noise, wrapper attacks on judges, MT-Bench judge | V/R | tm-5, H4, judge gate |
| 2602.07150, 2609.17394, 2507.02825, 2609.33812 | SWE-bench run-to-run noise and gold-test audits | V/R | g4-1, W5 |
| 2501.16007 TOPLOC, 2511.20621 DiFR | detect quant / model swaps from activations or scores | V | sv-5, dormant-1/2 CONTRADICTED; W4 |
| 2603.14332, 2606.04193, RFC 9943 | tool-call replay/tamper defences; receipts field crowded | V | gw-1 |
| 2409.03992, 2404.16109 zkLLM, 2509.18886 | TEE overhead PCIe-bound; zk proofs < 15 min for 13B; TDX/SGX < 10 % | V | A5, P3 |
| 2502.11880 bitnet.cpp, 2407.00088 T-MAC, 2504.12285 BitNet 2B4T | ternary CPU kernels (AVX2/NEON), 2B4T 29 ms CPU TPOT | R/V | W2, W10 |
| 2407.12327 Spectra/TriLM, 2502.02631 ParetoQ, 2510.13998 | sub-1B ternary loss gap; 1.58-bit scaling | V/R | Z1, mx-s1 framing |
| 2502.19405 Verde, 2106.11872 Zhuang, 2609.17380 OPEN-1B | fixed-order training tax 30-60 % matmul, T4 218/374 %; up to 746 % | V | W9, Z6, rust-3 |
| 2603.20421 Hawkeye, 2606.00279, 2605.19537 | GPU-vendor numeric portability of quantised weights | V | W1, Z3 |
| 2411.13757 GenBFA, 2509.21843, 2412.07192, 2511.02866 LM-Fix | bit-flip attacks and detection (> 94 % at TVL 200) | V | Z4, bit-flip page |
| 2202.05262 ROME, 2210.07229 MEMIT, 2405.02765 | model editing and edit detection | V/R | W4 |
| 2104.04043 RLIBM-32, CORE-MATH | correctly-rounded libm ~1.1x glibc | R/V | W6, L2 tolerance |
| 2402.14905 MobileLLM-LS | layer sharing in small models | R | tm-8 PARTIAL DUPLICATE |
| 2510.14276, 2511.22047, 2502.12143 | guard models vs big guards; OOD gap; CoT distillation for small students | R/V | mx-g1*, mx-g3*, tm-4 |
| NIST AI 100-1 / 600-1 | read: no determinism requirement found | V | standards memo (only allowed absence statement) |
| Thinking Machines blog 2025; SGLang blog 2025-09-22 | deterministic inference cost 26->42/55 s; +34 % avg | V | P1 |
