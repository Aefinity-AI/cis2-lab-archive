# SV-5 research: bit-exact replay vs tolerance fingerprinting vs stock deterministic rerun

Date: 2026-10-01. Status labels: VERIFIED = I read the text in the full PDF/HTML or an API response this session. REPORTED = taken from a page summary or search snippet, not read in full. UNVERIFIED = not confirmed.
Local text copies of the three PDFs were kept in the session scratch directory only (toploc.txt, difr.txt, cankaya.txt; line numbers below refer to them).

## Sources opened
- TOPLOC, arXiv 2501.16007 ([venue] 2025 PMLR 267), full PDF: https://arxiv.org/pdf/2501.16007 (VERIFIED, full text)
- DiFR, arXiv 2511.20621, full PDF: https://arxiv.org/pdf/2511.20621 (VERIFIED, full text)
- Cankaya, arXiv 2606.00279v2, "Bit-Exact AI Inference Verification Without Performance Tradeoffs", 5 Jun 2026: https://arxiv.org/pdf/2606.00279 (VERIFIED, full text)
- GitHub API for repos, PyPI JSON for toploc, raw READMEs (VERIFIED, see section 6).
- PyTorch reproducibility note: https://docs.pytorch.org/docs/2.14/notes/randomness.html (VERIFIED, partial; see section B2)
- Thinking Machines blog: https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ (VERIFIED, snippets only)

# PART A. What the papers say

## A1. TOPLOC (Ong et al., arXiv 2501.16007)

### 1. Threat model
- No dedicated threat-model section. The scope is stated in Sec 1/3.1 and the abstract. Prover = inference provider; verifier holds the model weights, the prompt and the prover's proofs, and recomputes with a prefill. (VERIFIED, Sec 4 and Fig 1, toploc.txt L176-250.)
- In scope (Sec 3.1, "Inference Modifications"): lower precision (fp8, bf16), KV-cache compression, altered model weights (distill, merge, prune), altered system prompt. (VERIFIED, toploc.txt L97-110.)
- Actually tested (Sec 5.6-5.7): different model, three system-prompt alterations, fp32 vs bf16. Not tested: KV-cache compression ("we also do not test", Sec 6.1); fp8 only "preliminary", result not tabulated.
- Out of scope / stated limits (Sec 6): speculative decoding ("not capable of detecting speculative decoding", 6.2); unstable-prompt mining (6.3); spoofing last-layer activations with a smaller model (6.4); subtle changes ("detecting minor prompt tweaks or slight gradient updates in fine-tuned models is significantly harder", 6.5).

### 2. Mechanism
- Committed: top-k values and indices of the LAST hidden layer (input to the LM head). Sec 4, Alg 1. k = 128 in all reported experiments (Sec 5.6, 5.8).
- Cadence: "top-128 values every 32 new tokens" plus one set for the prompt activations (Sec 5.6). 512 new tokens gives 16 decode proofs plus 1 prompt proof.
- Encoding: a polynomial congruence through the (index mod m, value) points; m is an injective modulus found per proof; 2 bytes per coefficient. Proof = 256 B of coefficients, 258 B quoted in the abstract/Sec 1; "8 bytes per token" amortised, "1024x reduction" vs 8192 B/token raw bf16 for hidden size 4096 (Sec 5.8, toploc.txt L460-470).
- Verification (Alg 2): recompute the hidden state by prefill on the claimed tokens; take its top-k; for each of the k points, decode the polynomial at the index; if exponent bits equal, record the mantissa absolute difference; else count an exponent mismatch.
- Compared: exponent-bit equality count and mantissa difference mean and median. Raw values, not hashes.

### 3. Thresholds (Sec 5.2, toploc.txt L247-252; Alg 2 line 17)
Reject if exp_mismatch > T_exp OR mean(mant_err) > T_mean OR median(mant_err) > T_median.
| precision | T_exp | T_mean | T_median |
|---|---|---|---|
| bf16 | 38 | 10 | 8 |
| fp32 | 8 | 256 | 128 |
- Quote: "thresholds were chosen based on our analysis of the error statistics in Table 2 and Table 5." Chosen post hoc between the honest maximum and the tampered minimum on the same data; no held-out calibration split is described.
- The thresholds are per precision, applied to all models. DiFR describes this as "a single global threshold tuned to work across all models" (difr.txt L136-137). Model-independence is not tested outside the four models below.
- Sec 5.6/5.7 text says mantissa is scaled when fp32 is validated against bf16 (fp32 mantissa shifted to bf16 width; bf16 padded with 16 zero bits).

### 4. Tamper classes, sizes, results
Data: UltraChat prompts. 400 prompts x 512 new tokens for the GPU/attention tests (Sec 5.6). Table 1 and Fig 2 use 2000 queries (Llama-3.1-8B). The number of trials behind Tables 4 and 5 is not stated in the text I read (UNVERIFIED).
- Model swap (Table 4): models Llama-3.1-8B, Llama-3.1-70B, INTELLECT-1 (10B), Gemma-2-9b-it. Honest max exponent mismatch: 8-19 of 128. Substitute min exponent mismatch: 125-128 of 128 (97.7-100%) for every pair shown. Gemma as generator is excluded: "out-of-bound token" (vocabulary mismatch). All substitutes are different architectures or sizes; no same-family fine-tune is tested.
- System-prompt alterations (Table 3, Sec 5.7): Advert (min exp mismatch 95 = 74.22%), Avoid (74 = 57.81%), Taco (67 = 52.34%). All above T_exp = 38. These are system-prompt prepends, not one-token edits.
- Precision (Table 5): fp32 generated, bf16 validator: accepted (max 14 exp mismatches, mean 4.38). bf16 generated, fp32 validator: rejected (min mantissa mean 27892, median 21683). Direction-asymmetric: fp32 passes bf16 validation. Quote: "fp32 is able to pass validations with either precision."
- fp8 vs bf16: "the margin between them is small" (Sec 6.1); distinguishable only if device configuration and attention implementation match.
- Reported rates: abstract "100% accuracy, achieving no false positives or negatives in our empirical evaluations." Table 6 (Sec 5.8) lists FPR 0% / FNR 0% for TOPLOC on its own data. No confidence interval, no trial count per cell.

### 5. Honest-case variation (Sec 5.6, Table 2)
- GPUs: 1xA100, 1xRTX 4090, 2xRTX 4090 (TP 1 and 2), all 3x3 generation/validation pairs. Max exp mismatch 15-20 of 128 (11.7-15.6%), max mantissa mean 4.03-6.30, median 2-4.
- Attention (HF Transformers): Flash Attention 2, PyTorch SDPA, FlexAttention, all 3x3 pairs. Max exp mismatch 12-28 (9.4-21.9%).
- vLLM with a hook for the GPU/TP tests (PagedAttention). Models: Llama-3.1-8B, INTELLECT-1, Gemma-2-9b-it, "aggregated". Batch size sweep: none reported (UNVERIFIED that batch size was varied). Largest honest exponent mismatch seen: 28 vs threshold 38 (margin of 10).
- Fig 2: mantissa error grows with token index (KV-cache error compounding), "moderate".

### 6. Code
- Repo https://github.com/PrimeIntellect-ai/toploc (VERIFIED via API): MIT, Python with C++ extensions (toploc/C/csrc/*.cpp), created 2025-01-28. Latest commit on default branch 2025-04-10 ("Parallelize proof test"); API "pushed_at" 2026-09-04 (some other ref; the default-branch commit list was read, I did not identify what was pushed).
- PyPI: toploc 0.1.6, MIT, python >=3.9, requires setuptools, torch, numpy (https://pypi.org/pypi/toploc/json). No CUDA dependency listed, so the proof build/verify functions take tensors and can be run on CPU tensors (REPORTED from dependency list and README; I did not run it).
- API (README): build_proofs_base64(activations, decode_batching_size, topk, skip_prefill), verify_proofs_base64(...) returns exp_intersections, mant_err_mean, mant_err_median. The README gives NO thresholds; the caller applies Sec 5.2 values. Note exp_intersections is a match count, whereas the paper thresholds an error count: T_exp = 38 means error > 38, so a caller must convert (k - intersections). (UNVERIFIED which convention the code uses.)
- The repo takes hidden-state tensors; it does not ship a Hugging Face generation harness. Experiment code: https://github.com/PrimeIntellect-ai/toploc-experiments (single commit 2025-01-28; contents not read). Hugging Face transformers on a single 16 GB T4: nothing in the repo prevents it, since the user supplies hidden states from `output_hidden_states` (own analysis; not tested).
- Smallest model in the paper: Llama-3.1-8B-Instruct, described as "the smallest model we tested" (Sec 5.8). Nothing below 8B.

### 7. Limitations: see section 1 above (Sec 6.1-6.5, direct quotes there).

## A2. DiFR (Karvonen et al., arXiv 2511.20621)

### 1. Threat model
- Provider claims a specification phi: model/weights, precision, sampling hyperparameters (temperature, top-p, top-k) and PRNG seed (difr.txt L255-268). Verifier holds the open weights, runs a prefill on the provider's (input, output) pairs, and (Token-DiFR) shares the PRNG seed. Hypotheses H0 (spec followed; differences are numerical noise) vs H1 (deviation: "wrong model/weights, incorrect quantization, different temperature or top-p values"), difr.txt L185-195.
- Tested (Sec 5.1): 4-bit model quantisation, FP8 KV cache, temperature 1.1 vs 1.0, wrong seed (42 vs 43), and simulated sampling bug (1% of tokens drawn uniformly from top-k, k in {2,32}). Appendix C also lists FP8 weight quantisation (Table 7-8 rows "model quant fp8").
- Out of scope / unevaluated (Sec 7.4, 7.2): speculative decoding, constrained decoding, closed-weight models, activation-DiFR does not check sampling ("proof of reconstructability rather than generation authenticity", Sec 2.2). Not tested: different model families as substitutes, LoRA/fine-tunes, system-prompt or prompt edits, one-bit weight changes.

### 2. Mechanism
- Token-DiFR: verifier recomputes logits on the claimed sequence, draws the same Gumbel noise from the shared seed, and scores delta = (l[t_hat] + T g[t_hat]) - (l[t*] + T g[t*]), clipped at Delta_max (Eq 1, pseudocode L335-350). Batch statistic = mean over tokens. Zero communication. Requires per-request seed sync, or temperature 0 (then it reduces to an argmax check, Sec 7.2).
- Activation-DiFR: shared-seed random orthogonal projection P of the activation a (D-dim) to k dims; provider sends f = P a at a subset of positions (stride J within 32-token windows); verifier compares L2 distance ||f - f_hat||_2 (Alg 2-3). Which layer exactly is stated as "activations a" from ForwardPassExtractActivations (final hidden state, as in TOPLOC; I did not find an explicit layer index, UNVERIFIED). Cost = k x B bytes per 32 tokens (App G, difr.txt L1336-1342).

### 3. Thresholds
- DiFR publishes NO fixed numeric accept/reject threshold. The test is S > tau with tau "determined empirically" from a calibration set (difr.txt L191-198). The reported metric is AUC at 1% FPR of a one-dimensional (logistic regression) classifier trained on a 50/50 token-level train/test split (Sec 5.2).
- Winsorisation percentiles swept: 99, 99.9, 99.99, 99.999 of the honest training split; "99.9th generally works well for quantization", 99.999th for rare bugs (Sec 5.2). Delta_max is a hyperparameter whose value I did not find in the text (UNVERIFIED).
- Rule: features that are lower in the incorrect set than in the calibration set are dropped (AUC set to 0.5).
- Raw score percentiles per config are in Tables 4-8 (App I), e.g. Qwen3-30B-A3B Table 8 rows. These are the numbers a fixed tau would be built from.

### 4. Tamper classes, results (Sec 6, Tables 1-3)
- ~1M output tokens per configuration, 9 configurations per model, 2,000 UltraChat prompts, up to 512 tokens each (L455-460). Batch (token-count) sweep 1 to 10,000.
- Token-DiFR, Llama 3.1 8B / Qwen3-8B: 4-bit quant and wrong seed detected after 100-500 tokens; FP8 KV cache needs ~1,000-5,000 tokens (Sec 6.1). 4-bit quant "AUC > 0.999 within 300 output tokens" (Sec 1, Table 2).
- Table 2 (Qwen3-30B-A3B, Token-DiFR, batch of 1 token): AUC 0.9911 for 4-bit, 0.9206 for FP8 KV, 0.8475 wrong seed; AUC at <1% FPR for batch 1: 0.67 / 0.51 / 0.51. So per-token detection at 1% FPR is poor.
- Pooled-honest setting: temperature +0.1 and the k=2 bug are "difficult to separate" for Qwen3-30B-A3B; in matched environments they are detected with a few thousand tokens (Sec 6.1).
- Activation-DiFR: "AUC > 0.999 using just 2 output tokens" for 4-bit (Table 3, Qwen3-30B-A3B); FP8 KV cache needs 4-20 tokens, saturating. Table 3 batch 1 AUC<1%FPR: 4-bit 0.6658, FP8 KV 0.5115; batch 4: 4-bit 1.0, FP8 KV 0.6999 (difr.txt L1553-1566).
- Bytes/token (Table 1, FP8 KV cache, AUC>=0.999): Llama 3.1 8B H200: Act-DiFR 0.312, TOPLOC 0.625; Qwen3-30B-A3B A100->H200: Act-DiFR 7.25, TOPLOC 32. These are DiFR's reimplementation of TOPLOC as a score, not the thresholded TOPLOC rule.
- Key honest-case statistic: tokens under a shared seed match exactly "over 98%" (Table 6) and in minor misconfigurations "over 95%" of tokens still match the reference (Sec 6.1). Quote: "over 95% of generated tokens exactly match."

### 5. Honest-case variation
- Models: Llama-3.1-8B-Instruct, Qwen3-8B, Qwen3-30B-A3B (MoE).
- Engines/hardware: vLLM 0.10.0 (paper; repo pins 0.10.1) with H200 TP-4, A100 TP-0, A100 TP-4, plus a HuggingFace H200 run. HF Qwen3-30B-A3B had benign Token-DiFR gaps on the order of the FP8 KV setting (Table 4: p99 3203 vs 172 for FP8 KV on the likelihood score) and was excluded from the default pool (Sec 6.1, App K).
- Batch size of the serving engine: not varied explicitly as a factor (UNVERIFIED); noise from batching is covered implicitly by the pooled configurations.

### 6. Code
- https://github.com/adamkarvonen/difr (VERIFIED via API): MIT, Python, created 2025-11-10, last default-branch commit 2025-12-08 ("Clean up"), pushed_at 2026-02-06. Pins vllm==0.10.1, torch==2.7.1, transformers==4.57.3, bitsandbytes==0.46.1, toploc==0.1.6 (pyproject.toml). Install with uv.
- README (REPORTED): token_difr_vllm.py (vLLM misconfig tests), vllm_verification.py (Token-DiFR, TOPLOC, Activation-DiFR), OpenRouter integration; "This file supports multiple metrics, HuggingFace generation, and simulated bug generation." Also "If you are uncertain about the exact sampling implementation, you must use temperature zero."
- CPU-only: not documented; vLLM path needs a GPU. Single T4 with HF transformers: the HF path exists, but T4 is not among tested GPUs, and vllm==0.10.1 pins are heavy; not tested by me. Smallest model in the paper: 8B (Llama 3.1 8B, Qwen3-8B). The repo README did not name a smaller default (REPORTED; UNVERIFIED for config files).

### 7. Limitations (own words): Sec 7.4 "We have not evaluated our approach on other sampling procedures such as speculative decoding"; Sec 7.2 "cannot verify inference from providers serving closed-weights models" and "Providers must also expose an API parameter allowing clients to specify per-request sampling seeds"; Sec 2.2 activation fingerprints "cannot verify the sampling process itself". DiFR also says (Sec 3.1) that on fixed hardware with batch-invariant kernels "the verifier can re-run the model once and check exact equality", and that in the broader setting "we expect statistical verification to remain necessary".

## A3. Cankaya (arXiv 2606.00279v2): bit-exact verification evidence (relevant to arms a and c)
- Claim (abstract/Sec 1): inference engines are "deterministic but non-invariant"; bitwise-identical activations when hardware SKU, software stack (CUDA, PyTorch, engine, attention backend), quantisation format/kernel and TP rank are fixed. No PyTorch determinism flags were set ("No determinism flags are set in PyTorch or CUDA", Sec 3.1, L170).
- Same-SKU different physical cards (A100 PCIe vs SXM): L2 = 0 (Sec 3.1; App D Table 1). Across architectures (A100/H100/A40/L40S): L2 0.45-0.58 on FP16 Qwen2.5-7B prefill hidden states (App D Table 1). H100-NVL, H100-PCIe, H200 are identical to each other.
- Dependencies that change bits: cuBLAS 12.0 vs 11.8 changed hidden states by 1-5%; cu128 vs cu129 on A100 did not (footnote 10, App). Batch size changes bits for short sequences (equivalence classes, invariant above ~4000 tokens). Atomics in an INT4 GPTQ exllama kernel caused genuine nondeterminism (Kimi-K2-Thinking, Qwen3-8B GPTQ without marlin).
- Detectability (App D Table 2, SNR = mismatch distance / cross-hardware floor, A100<->H100): attention impl (eager/SDPA/FA2) 10.5x prefill, detectable; AWQ vs GPTQ INT4 26.7x detectable; batch size 1.08x NOT detectable across hardware; TP 0.90x NOT detectable across hardware. Same-hardware replay would detect them (floor 0).
- Emulator: software-only CPU emulation of tensor-core arithmetic predicts every bit of Qwen3-4B FFN/attention blocks on A100, L40, L40S, H100 (0 BF16 diffs; 71M elements for the attention block at 4,000 tokens). Not T4/Turing. Dense models only; MoE and non-NVIDIA are listed limits (Sec 5).
- Not in this paper: tolerance thresholds, tamper tests of weights/prompts. Its framing is bitwise pass/fail given recorded configuration.

# PART B. OWN ANALYSIS (not from the papers; labelled judgement)

## B1. Tamper classes that change tokens yet may stay under a tolerance threshold
| class | tested by TOPLOC? | tested by DiFR? | note (own analysis) |
|---|---|---|---|
| single weight bit flip (e.g. low mantissa bit of one element) | no | no | Output change may be zero or near zero; top-128 final-layer mantissa deltas well below T_mean = 10 (mantissa units, 7 bits in bf16) are likely. Bit-exact replay detects any change that alters the hidden state. UNVERIFIED by experiment: must be measured. |
| LoRA / fine-tune with tiny norm | no (Sec 6.5 says "significantly harder") | no | Candidate where replay wins and tolerance may fail. |
| one-token prompt edit | partial: 3 system-prompt prepends of 3-word to multi-sentence length, min mismatch 52-74% | no | One-token edit not tested. Edit near the end shifts final-layer values less than a prepend. |
| fp16 vs bf16 | only fp32 vs bf16 | no | TOPLOC thresholds exist for bf16 and fp32 only; fp16 has no published threshold. |
| int8 vs fp32/bf16 weights | no | FP8 weights and 4-bit only (bitsandbytes / w4a16) | DiFR 4-bit is easy at 2-300 tokens; int8 is smaller noise and untested. |
| FP8 KV cache | "preliminary", margin "small" (Sec 6.1) | yes, hardest tested class: 1,000-5,000 tokens Token-DiFR; 4-20 tokens Act-DiFR | Tolerance methods need aggregation over many tokens. |
| attention/KV implementation (SDPA/FA2/eager) | honest case only: treated as noise, must pass | not a tamper class | Cankaya treats it as detectable (10.5x prefill SNR) under bit-exact replay on the same stack. A tolerance method accepts it as noise by design. |
| wrong seed / temp +0.1 / sampling bug | out of scope (no sampling check) | yes (Token-DiFR) | Sampling-layer tampering is invisible to final-hidden-state tolerance schemes (TOPLOC Sec 6.2, DiFR Sec 2.2). For CIS-2, replay of the sampler is part of the claimed spec. |

## B2. Fair "stock deterministic rerun" (arm c)
- Settings to fix (PyTorch 2.14 note, VERIFIED text: the note states that completely reproducible results are not promised across PyTorch releases, individual commits, or different platforms, and that results may not be reproducible between CPU and GPU executions, even with identical seeds). torch.use_deterministic_algorithms(True) (note says it also sets fill_uninitialized_memory True by default and costs performance); cudnn.deterministic / benchmark=False; SDPA backend pinned (the note says SDPA backends differ in determinism). CUBLAS_WORKSPACE_CONFIG (:4096:8 or :16:8): the string did NOT appear in the fetched 2.14 page text, so I cannot cite it; UNVERIFIED here (our repo's fm-5 runs set it, see below).
- Also pin: batch size and padding (left-pad vs none), sequence length, library versions (torch, CUDA, cuBLAS, transformers, tokenizers; Cankaya: cuBLAS major version changes bits), attention backend, dtype, GPU SKU, and a pre-tokenised input hash. Cankaya's results show these factors, not the determinism flags, decide bit equality; batch size matters below ~4000 tokens.
- Published evidence: same-SKU same-stack bit identity incl. across physical cards (Cankaya Sec 3.1, App D Table 1; VERIFIED). Cross-GPU-type identity: seen only within one architecture (H100-NVL = H100-PCIe = H200); across architectures not identical (0.45-0.58 L2). Thinking Machines: 1000 temperature-0 completions of Qwen3-235B-A22B gave 80 unique outputs, most common 78 times, earliest divergence at token 103, with standard kernels; batch-invariant kernels gave identical outputs (blog, "Experiments"; VERIFIED snippet).
- Local evidence (our own reports, not independent): Kaggle T4 and Lightning T4 bit-identical for a 135M-class student training run with pinned torch 2.10.0+cu128 + transformers 5.0.0 + tokenizers 0.22.2, raw-param sha256 167074c4...; without pinning, tokenizer version differed (<home>/.claude/projects/-home-<user>/memory/frontier1-directive-2026-09-25.md, 09-25 10:50Z and fm-5c entries). Different-host identity was achieved only after pinning. This is training, not inference, and one GPU type.
- T4 is Turing (sm75). Whether bf16 inference is meaningful there is a hardware question I did not source; use fp32 or fp16 on T4 and say so in the protocol. UNVERIFIED.

## B3. Smallest like-for-like models on free hardware
- Both papers' smallest model is 8B. At fp16 an 8B model (~16 GB) does not fit one 16 GB T4 with activations; Kaggle 2xT4 would need device_map sharding, which changes the reduction topology (pipeline-style; Cankaya says PP rank invariant). Single-T4 runs require a model of about 3B or smaller (own arithmetic, not sourced).
- SmolLM2 135M/360M/1.7B fit one T4 in fp32/fp16 and run on Kaggle CPU.
- TOPLOC as published: algorithm applies to any model with a final hidden state; hidden size differs (SmolLM2-135M is much smaller than 4096, so k = 128 is a larger fraction of the vector; UNVERIFIED hidden sizes: not looked up). Published thresholds were calibrated on 8B-70B bf16 and fp32 on A100/4090; no statement that they transfer to other sizes. Treat them as unvalidated for SmolLM2 and for T4; recalibrate on honest runs (A100/4090 are not in free tier). Report both published and recalibrated values.
- DiFR as published: no fixed tau, so calibration on honest SmolLM2 runs is part of the method; Token-DiFR needs a Gumbel seed protocol (use temperature 0 for a seed-free argmax check) and, per README, vLLM (GPU). HF-generation support exists in the repo (REPORTED). CPU-only unsupported as documented.
- CIS-2 arm (a) already pins SmolLM2 on CPU; arm (c) can run SmolLM2 with HF/PyTorch on T4 (Kaggle, Lightning) and Kaggle CPU.

## B4. Gaps for the SV-5 freeze
1. No paper tests single-bit weight flips, tiny LoRA, one-token prompt edits, fp16-vs-bf16 or int8; these are the discriminating cases for replay vs tolerance.
2. TOPLOC trial counts per cell for Tables 4/5 not located; get them from toploc-experiments if the protocol cites detection rates.
3. TOPLOC code convention for exp_intersections vs error count; check before applying T_exp.
4. DiFR Delta_max value and layer index of Activation-DiFR; check difr/ source.
5. CUBLAS_WORKSPACE_CONFIG citation: re-fetch PyTorch note section "CUDA convolution/ cuBLAS" or NVIDIA cuBLAS docs.

# Sources
- https://arxiv.org/pdf/2501.16007 (Sec 3.1, 4 Alg 1-2, 5.2, 5.6-5.8, Tables 2-6, Sec 6)
- https://arxiv.org/pdf/2511.20621 (Sec 2.2, 3.1, 4, 5.1-5.2, 6, 7.2, 7.4, Tables 1-8, App C, G, I)
- https://arxiv.org/pdf/2606.00279 (Sec 1, 3.1-3.2, 4, 5, 6, App D Tables 1-2)
- https://github.com/PrimeIntellect-ai/toploc ; https://pypi.org/pypi/toploc/json ; https://github.com/PrimeIntellect-ai/toploc-experiments
- https://github.com/adamkarvonen/difr (README, pyproject.toml, GitHub API)
- https://docs.pytorch.org/docs/2.14/notes/randomness.html
- https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
- <home>/.claude/projects/-home-<user>/memory/frontier1-directive-2026-09-25.md
