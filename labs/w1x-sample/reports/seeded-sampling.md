# Prior art: deterministic seeded sampling in production LLM inference (for a CIS-2 normative clause)

Accessed: 2026-10-16. Method: raw files fetched with curl (docs source, GitHub raw, OpenAPI YAML) and grepped; quotes are verbatim from those bytes unless marked [summarizer]. "verified" = I read the primary bytes; "reported" = only seen through a search/summary snippet. Source files saved under the session scratchpad (not repo).
Scope note: main-branch code was read on 2026-10-16; it moves. Pin commits before citing in the spec.

## Bottom line (for the clause)
- KNOWN: no mainstream stack pins a PRNG algorithm + float conversion as a portable contract. Every API says "best effort" or "same hardware/version only".
- KNOWN: the one implementation that is counter-based and kernel-defined is SGLang (`murmur_hash32(seed, position, vocab_index)` -> fp64 uniform -> Gumbel-max). That is the closest thing to a spec-able design, but it is code, not a spec, and it is not pinned across versions.
- OPEN: no public spec/paper found that pins PRNG + seeding + uniform->float + tie-break so two independent implementations match bit-for-bit.

---
## Q1. vLLM

### KNOWN (verified): seed is a per-request torch.Generator on the model-runner device
- Claim: when a request has a seed, vLLM creates a `torch.Generator` on the runner's device and seeds it.
  Src: https://raw.githubusercontent.com/vllm-project/vllm/main/vllm/v1/worker/gpu_model_runner.py (lines ~1255-1257)
  Quote: `generator = torch.Generator(device=self.device)` / `generator.manual_seed(sampling_params.seed)`
- Claim: sampling draws exponential noise from that generator (Gumbel/exponential-race), so the PRNG is torch's CUDA Philox, device-dependent.
  Src: https://raw.githubusercontent.com/vllm-project/vllm/main/vllm/v1/sample/ops/topk_topp_sampler.py (line ~366-367)
  Quote: `q[i].exponential_(generator=generator)`
- Claim: per-request generators disable some fast paths.
  Same file, line ~194: "device's default generator, so per-request generators aren't supported." and ~168 "callers must additionally ensure no request needs a per-request seed".
- Claim: `seed` field docstring is minimal.
  Src: https://raw.githubusercontent.com/vllm-project/vllm/main/vllm/sampling_params.py (line 322-323)
  Quote: `seed: int | None = None` / "Random seed to use for the generation."
- Claim: newer GPU model-runner path stores per-request seeds in int64 tensors (a different sampler implementation from the torch.Generator path). Src: https://raw.githubusercontent.com/vllm-project/vllm/main/vllm/v1/worker/gpu/sample/states.py (`self.seeds = UvaBackedTensor(max_num_reqs, dtype=torch.int64)`); https://raw.githubusercontent.com/vllm-project/vllm/main/vllm/v1/worker/gpu/sample/gumbel.py exists (I did not audit its hash/PRNG). => two sampler paths inside one project; PRNG is not a stable contract. (verified existence; PRNG of the new path OPEN)

### KNOWN (verified): docs disclaim default reproducibility; same-hardware-and-version only
Src: https://raw.githubusercontent.com/vllm-project/vllm/main/docs/usage/reproducibility.md
- "vLLM does not guarantee the reproducibility of the results by default, for the sake of performance."
- "Even with the above settings, vLLM only provides reproducibility when it runs on the same hardware and the same vLLM version."
- "The `seed` parameter in vLLM is used to control the random states for various random number generators."
- "In V1, the `seed` parameter defaults to `0` which sets the random state for each worker, so the results will remain consistent for each vLLM run even if `temperature > 0`."
- Docs do not state batch-composition or TP-size behaviour for the global seed (OPEN for those two axes on that page).

### KNOWN (verified): batch-invariance feature
Src: https://raw.githubusercontent.com/vllm-project/vllm/main/docs/features/batch_invariance.md (also https://docs.vllm.ai/en/latest/features/batch_invariance.html)
- Guarantee [summarizer, wording lightly paraphrased; re-read the raw .md before quoting]: it "ensures that the output of a model is deterministic and independent of the batch size".
- Limit (summarizer): "Batch invariance under tensor parallelism is not yet supported for all-reduces whose size isn't a multiple of 16 bytes."
- Hardware (summarizer): NVIDIA compute capability 8.0+, AMD Instinct gfx90a/gfx942/gfx950, Intel XPU with Triton.
- The page's examples pass `seed=42` but do not explain how seed composes with batch invariance (PARTIAL: no stated guarantee for seeded temperature>0 across batches in vLLM docs).

### KNOWN (verified): Thinking Machines blog
Src: https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ (Horace He, Sep 10, 2025)
- Definition/claim: "the reduction order for each element must be fixed regardless of the batch-size of the kernel." [summarizer; the underlying idea is stated in the page]
- Result: "Surprisingly, we generate 80 unique completions, with the most common of these occuring 78 times." (1000 samples, temp 0, Qwen3-235B-A22B-Instruct-2507)
- Result: "On the other hand, when we enable our batch-invariant kernels, all of our 1000 completions are identical."
- Stated limit: "It is not “hardware/software version invariant” — your GPU/PyTorch version may return a different value, but it should deterministically return the same value."
- Scope: greedy (temp 0). The post does not specify a seeded sampler, PRNG, or TP-size behaviour (page's sampling text refers only to the sampler being mathematically deterministic: "This is what we would mathematically expect from our sampler"). => for seeded temp>0: OPEN in this source.
- Kernel library: https://github.com/thinking-machines-lab/batch-invariant-ops (linked from the post; not audited).

PARTIAL summary Q1: guarantee = batch-size invariance, same HW/software, greedy-proved; seeded-sampling cross-hardware = no claim. TP-size: no guarantee that results match across different TP sizes (only a fixed-order all-reduce within a config).

---
## Q2. SGLang

### KNOWN (verified): explicit seeded counter-based sampler in deterministic mode
Src: https://raw.githubusercontent.com/sgl-project/sglang/main/python/sglang/srt/layers/sampler.py, `multinomial_with_seed` (lines ~933-969)
- Docstring: "Samples n elements from an input tensor `inputs` of shape (n, m) using a unique random seed for each row. This is a deterministic batched alternative to `torch.multinomial`."
- "positions: The positions of the tokens in the sequence. Used for deterministic sampling to get the unique seed for each position."
- Code: `hashed = murmur_hash32(seed, positions, col_indices)`; `x = hashed.to(torch.float64) / torch.iinfo(torch.uint32).max`; Gumbel noise `-log(-log(x))` added to `logprobs.to(torch.float64)`; `torch.argmax`.
- Comment: "it is critical to keep gumbel noise calculation in float64 to avoid numerical instability."
- Hash implementation (MurmurHash3 mix/fmix32, constants 0xCC9E2D51, 0x1B873593, 0x85EBCA6B, 0xC2B2AE35): https://raw.githubusercontent.com/sgl-project/sglang/main/python/sglang/kernels/ops/sampling/murmur_hash.py
- => PRNG = stateless hash of (seed, token position, vocab column); uniform = u32/(2^32-1) in float64. Not batch/draw-order dependent by construction. Note u in [0,1] closed; code clamps `x.log_().clamp_(..., max=-(2.0**-32))` for the x==1 case (shows edge-case handling is ad hoc).
- Also: top-k/top-p seeded path keeps full sort ("The seeded path keeps the full sort because the order of tied" ...), and `assert sampling_info.sampling_seed is None, f"Sampling seed is not supported for {backend} backend"` (some backends unsupported).

### KNOWN (verified): docs/blog statements
Src: https://lmsys.org/blog/2025-09-22-sglang-deterministic/
- "As a result, the same (inputs, seed) pair always yields the same sample, even when temperature > 0."
- "We acknowledge that deterministic inference is significantly slower than normal mode."
- "Support for MoE models : Currently we only support deterministic inference for dense models like QWen3-8B or LLaMa-3.1-8B."
- "Tensor Parallelism : TP1 and TP2 are deterministic due to consistent floating-point addition order; larger TP setups require modifications to reduce kernels for determinism."
- Hardware: H100/H200 benchmarks; says AMD possible via Triton. Does not claim cross-hardware bit equality.
Src: https://docs.sglang.io/advanced_features/deterministic_inference.html [summarizer; re-verify]
- "By default, SGLang uses a sampling seed of `42` for reproducible sampling"; only FlashInfer, FA3, Triton attention backends supported; "Expected result: All tests should show `Unique samples: 1`".
PARTIAL: strongest seeded-sampling determinism statement among serving stacks, scoped to one machine type, dense models, TP<=2.
Not fetched: the SGLang PR(s) introducing it. OPEN for PR text.

---
## Q3. llama.cpp

### KNOWN (verified): PRNG = std::mt19937, `std::uniform_real_distribution<double>`, `std::discrete_distribution<int>`
Src: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/src/llama-sampler.cpp
- `std::mt19937 rng;` (struct llama_sampler_dist, line ~1128); `ctx->rng.seed(ctx->seed_cur);`
- CPU path: `std::discrete_distribution<int> dist(probs_iterator{cur_p->data}, probs_iterator{cur_p->data + cur_p->size}); return dist(rng);` (probabilities are `float`, `typedef float value_type`) (llama_sample_dist, line ~217-246)
- Backend path: "We sample in double precision and cast to float to match rnd numbers of llama_sampler_dist which uses double precision (sampling from std::uniform_real_distribution<double> and std::uniform_real_distribution<float> with same rng will produce different sequences)." (line ~1349-1353) -- direct admission that float-vs-double distribution choice changes the draw sequence.
- Seed CLI: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/common/arg.cpp line 1998-1999: `{"-s", "--seed"}, "SEED", "RNG seed (default: %d, use random seed for %d)"`.
- Not bit-reproducible by spec: mt19937 raw output is standardised (C++ standard), but `std::uniform_real_distribution` and `std::discrete_distribution` are implementation-defined in the C++ standard (libstdc++/libc++/MSVC may differ). I did NOT find a primary llama.cpp or libstdc++ source in this session that demonstrates a cross-stdlib divergence => the "may differ" claim is from the C++ standard's design, not verified here: mark OPEN for a quoted source. (Do not cite as KNOWN.)
- Sampling dtype: probabilities and logits are float32 in the sampler chain (`typedef float value_type` above; `llama_token_data.p` is float). Top-k/top-p/temperature arithmetic is float32 on the CPU backend; backend (GPU) samplers exist and are a separate path (PR https://github.com/ggml-org/llama.cpp/pull/25532 "Backend sampling multi output", closed/merged status: closed).
- Cross-machine bit reproducibility of the sampling chain: OPEN. I found no llama.cpp statement guaranteeing it, and no issue in the searches I ran that asserts it fails. Related open issues, none about seeds across machines:
  - https://github.com/ggml-org/llama.cpp/issues/28974 (feature request, 2026-09-16): "The values must be a deterministic function of (seed, flat index) for reproducibility. There's no GGML OP for randomness" and "CPU implementation can just use mt19937 as usual. On-device we could use something like Xoroshiro128+ or Philox." (shows on-device RNG op does not exist upstream)
  - https://github.com/ggml-org/llama.cpp/pull/19409 (blue-noise RNG option replacing "the (white noise) mt19937 RNG").
  - https://github.com/ggml-org/llama.cpp/issues/28963 "CPU backend: llama_batch.embd ... decoding is non-deterministic, while the token path is bitwise deterministic" (title; body not read).
  - https://github.com/ggml-org/llama.cpp/issues/28527 "Quantized K cache makes deterministic prefix-cache repeats produce different output" (title only).

---
## Q4. Hugging Face transformers `generate` + torch seed

### KNOWN (verified)
- `generate` multinomial sampling is `torch.multinomial(probs, num_samples=1)` on the global torch RNG: https://raw.githubusercontent.com/huggingface/transformers/main/src/transformers/generation/utils.py (lines 3258, 4100: `next_tokens = torch.multinomial(probs, num_samples=1).squeeze(1)`). There is no per-call seed; the user must seed the global RNG.
- HF helper: https://raw.githubusercontent.com/huggingface/transformers/main/src/transformers/trainer_utils.py `set_seed(seed, deterministic=False)`: "Helper function for reproducible behavior to set the seed in `random`, `numpy`, `torch` (if installed)." and `deterministic`: "Whether to use deterministic algorithms where available. Can slow down training."
- PyTorch: https://docs.pytorch.org/docs/1.11/_sources/notes/randomness.rst.txt (the 'stable' copy returned 404 at the raw path I tried; version 1.11 shown)
  - "Completely reproducible results are not guaranteed across PyTorch releases," (first lines; the sentence continues to individual commits and platforms)
  - "...reproducible between CPU and GPU executions, even when using identical seeds."
  - `torch.use_deterministic_algorithms`: https://docs.pytorch.org/docs/stable/generated/torch.use_deterministic_algorithms.html (page was JS-light, I did not capture the RuntimeError wording; OPEN for exact quote).
- PARTIAL: `generate` has no determinism statement of its own; HF delegates to torch. I did not find a determinism caveat in the generation_strategies doc (grep returned nothing).

---
## Q5. API vendors

### OpenAI -- KNOWN (verified)
Src: https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml (seed field, line ~45301-45313) and https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter
- "If specified, our system will make a best effort to sample deterministically, such that repeated requests with the same `seed` and parameters should return the same result."
- "Determinism is not guaranteed, and you should refer to the `system_fingerprint` response parameter to monitor changes in the backend."
- `system_fingerprint` is now flagged `deprecated: true` in the OpenAPI spec; description: "This fingerprint represents the backend configuration that the model runs with. Can be used in conjunction with the `seed` request parameter to ..." (cut at 3 lines; verified start).
- Cookbook: "It changes whenever you change request parameters, or OpenAI updates numerical configuration of the infrastructure serving our models (which may happen a few times a year)."
- Fine-tuning seed (different field): "Passing in the same seed and job parameters should produce the same results, but may differ in rare cases."
- Docs page https://platform.openai.com/docs/advanced-usage/reproducible-outputs now 301s to developers.openai.com and the new URL I tried 404'd; use the OpenAPI/cookbook above.

### Mistral -- KNOWN (verified)
Src: https://raw.githubusercontent.com/mistralai/platform-docs-public/main/openapi.yaml (chat completion request `random_seed`, type integer, minimum 0)
- "The seed to use for random sampling. If set, different calls will generate deterministic results."
- No best-effort caveat, no fingerprint field in what I read. (PARTIAL: strong wording, no stated scope.)

### Google Gemini -- KNOWN (verified)
Src: https://raw.githubusercontent.com/googleapis/googleapis/master/google/ai/generativelanguage/v1beta/generative_service.proto line 402-404
- "Optional. Seed used in decoding. If not set, the request uses a randomly generated seed." (`optional int32 seed = 8;`)
- Same text on https://ai.google.dev/api/generate-content ("Seed used in decoding. If not set, the request uses a randomly generated seed.").
- No determinism guarantee statement found in that field's text. Note int32 width.

### Anthropic -- OPEN
- Messages API Python SDK params file has no `seed` field: grep of https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/src/anthropic/types/message_create_params.py for "seed" returned nothing (verified). I could not retrieve a quotable sentence about determinism from Anthropic docs in this session (docs.anthropic.com / platform.claude.com fetches gave no match for "deterministic"/"seed"). => OPEN: no seed parameter and no quoted determinism claim.

---
## Q6. Specs/papers that PIN a PRNG for sampling

### OPEN (as a bit-exact cross-implementation contract)
I found no public spec or paper that pins algorithm + seeding + uniform->float conversion + tie-breaking for token sampling.

Partial hits (verified):
- EigenAI, arXiv 2602.00182 (https://arxiv.org/html/2602.00182v1), raw HTML grepped:
  - "EigenAI enforces deterministic decoding by employing a fixed-seed pseudorandom number generator (PRNG) and canonical iteration order."
  - "Seed PRNGs deterministically and record seeds in receipts."
  - "Users seeking nondeterministic sampling may simply vary the seed but can still verify that any output matches the declared seed and policy recorded in the operator’s receipt."
  - Limit: "Determinism currently holds only within fixed GPU families." and "cross-architecture tests (A100 versus H100) do not match bitwise due to differences in floating-point rounding behavior, underscoring the need for per-architecture verifier sets."
  - The PRNG algorithm is NOT named in the text I extracted (OPEN). Closest analogue to CIS-2, but weaker: per-architecture, PRNG unnamed.
- Gensyn Verde, arXiv 2502.19405 (PDF text via pdftotext): "RepOps use built-in support for deterministic pseudorandomness generation in PyTorch and CUDA." => relies on torch/CUDA Philox, not a pinned portable algorithm. Scope: "RepOps currently ensures reproducibility between setups when programs are run on a single GPU in each setup."
- Gensyn REE docs https://docs.gensyn.ai/tech [summarizer]: modes `reproducible`: "Bitwise-identical results across any supported hardware."; `deterministic`: "Reproducible on the same hardware across runs."; no sampling/seed/RNG text found. REE is "not open source" per search snippet (reported, not verified).
- SGLang murmur-hash sampler (Q2) is the only concrete counter-based pinned-looking design, but is implementation code, fp64 on GPU, not versioned as a contract.
- llama.cpp: mt19937 (Q3) is a standard-defined engine but surrounding distributions are not.
- Rust `rand` explicitly refuses portability for StdRng (Q7).
Searches NOT done / OPEN: any IETF/NIST/MLCommons/ONNX "deterministic sampling" RFC; MLCommons Inference rules; ONNX RandomUniform seed semantics.

---
## Q7. Candidate spec PRNGs

| PRNG | Spec | Output | Canonical test vector |
|---|---|---|---|
| PCG32 (PCG-XSH-RR 64/32) | O'Neill, https://www.pcg-random.org/paper.html ; reference C https://raw.githubusercontent.com/imneme/pcg-c-basic/master/pcg_basic.c | 32-bit; 64-bit state, 64-bit stream increment | PARTIAL: reference repo pcg-c-basic has demo programs but no stored expected-output file (checked listing). pcg-cpp has expected outputs: https://raw.githubusercontent.com/imneme/pcg-cpp/master/test-high/expected/check-pcg32.out ("pcg32: result: 32-bit unsigned int ... Round 1: 32bit: 0xa15c02b7 0x7b47f409 0xba1d3330 0x83d2f293 0xbfa4784b 0xcbed606e") -- seeding for that check is in check-pcg32.cpp (not read) |
| xoshiro128** | Blackman/Vigna, https://prng.di.unimi.it/xoshiro128starstar.c (public domain/CC0 per header line 4) | 32-bit; 128-bit state ("The state must be seeded so that it is not everywhere zero.") | OPEN: no test vector in the reference .c; authors recommend seeding via SplitMix64 |
| SplitMix64 | Vigna, https://prng.di.unimi.it/splitmix64.c ; `z = (x += 0x9e3779b97f4a7c15)` | 64-bit; 64-bit state, "The state can be seeded with any value." | OPEN: no vector in reference file. Also Java's SplittableRandom heritage (not fetched) |
| ChaCha20 (IETF) | RFC 8439, https://www.rfc-editor.org/rfc/rfc8439.txt | 512-bit blocks (16 x u32); 256-bit key, 96-bit nonce, 32-bit counter | KNOWN: sec 2.1.1 quarter-round vector, 2.3.2 block-function vector, 2.4.2 cipher vector, Appendix A.1 additional block vectors (headings verified in the TOC) |
| Rust rand StdRng (ChaCha12) | https://raw.githubusercontent.com/rust-random/rand/master/src/rngs/std.rs | n/a | Explicitly NOT a stable contract. Quote: "Non-portable: any future library version may replace the algorithm (For a portable version, use the chacha20 crate directly.)" and "The current algorithm used is the ChaCha block cipher with 12 rounds ... This may change". Also "even with a fixed seed, output is not portable" => do NOT cite StdRng; cite ChaCha12/20 itself |
| Philox4x32-10 | Salmon et al., "Parallel random numbers: as easy as 1, 2, 3" (SC11); reference https://raw.githubusercontent.com/DEShawResearch/random123/main/include/Random123/philox.h (multipliers 0xD2511F53, 0xCD9E8D57; Weyl 0x9E3779B9, 0xBB67AE85; default rounds 10) | 4 x u32 per 128-bit counter, 64-bit key | KNOWN (verified): https://raw.githubusercontent.com/DEShawResearch/random123/main/tests/kat_vectors, e.g. `philox4x32 10 00000000 00000000 00000000 00000000 00000000 00000000   6627e8d5 e169c58d bc57ac4c 9b00dbd8`; ctr=ffffffff x4 key=ffffffff x2 -> `408f276d 41c83b0e a20bc7c6 6d5451fd`; pi vector -> `d16cfe09 94fdcceb 5001e420 24126ea1` |

Philox in PyTorch: ATen has a Philox engine header (https://raw.githubusercontent.com/pytorch/pytorch/main/aten/src/ATen/core/PhiloxRNGEngine.h) with `seed`, `subsequence`, `offset`; its own note says "currently this implementation of the philox engine is not used" in place of curandStatePhilox4_32_10_t (note text at line ~38, partially read). The torch CUDA path (`curandStatePhilox4_32_10_t`) is what vLLM's `torch.Generator(device=cuda)` uses (reported by that header's note, not independently verified in cuRAND source). Counter-based = parallel-friendly and order-independent, which matches the SGLang design principle; offset accounting (`offset` increments per kernel launch in torch) is torch-internal and would not be portable.

Float conversion: no PRNG spec above defines token-sampling uniform->float; that is an implementation choice (SGLang: u32/(2^32-1) in fp64; llama.cpp: libstdc++-style `uniform_real_distribution<double>`). Needs to be pinned by the clause itself. OPEN as prior art.

## Suggested NEEDS/BLOCKERS entries
None. Follow-ups worth a leg if wanted: (a) read EigenAI full text for the PRNG name; (b) read vLLM `gumbel.py` for the new sampler's hash; (c) quote Anthropic docs on temperature-0 non-determinism; (d) find a primary demonstration of libstdc++ vs libc++ `uniform_real_distribution` divergence; (e) PCG32 seeding used by check-pcg32.cpp to make a vector citable.

## Sources
- https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
- https://raw.githubusercontent.com/vllm-project/vllm/main/docs/usage/reproducibility.md
- https://raw.githubusercontent.com/vllm-project/vllm/main/docs/features/batch_invariance.md
- https://raw.githubusercontent.com/vllm-project/vllm/main/vllm/v1/worker/gpu_model_runner.py
- https://raw.githubusercontent.com/vllm-project/vllm/main/vllm/v1/sample/ops/topk_topp_sampler.py
- https://raw.githubusercontent.com/vllm-project/vllm/main/vllm/sampling_params.py
- https://lmsys.org/blog/2025-09-22-sglang-deterministic/
- https://docs.sglang.io/advanced_features/deterministic_inference.html
- https://raw.githubusercontent.com/sgl-project/sglang/main/python/sglang/srt/layers/sampler.py
- https://raw.githubusercontent.com/sgl-project/sglang/main/python/sglang/kernels/ops/sampling/murmur_hash.py
- https://raw.githubusercontent.com/ggml-org/llama.cpp/master/src/llama-sampler.cpp
- https://raw.githubusercontent.com/ggml-org/llama.cpp/master/common/arg.cpp
- https://github.com/ggml-org/llama.cpp/issues/28974 ; /pull/19409 ; /issues/28963 ; /issues/28527
- https://raw.githubusercontent.com/huggingface/transformers/main/src/transformers/generation/utils.py
- https://raw.githubusercontent.com/huggingface/transformers/main/src/transformers/trainer_utils.py
- https://docs.pytorch.org/docs/1.11/_sources/notes/randomness.rst.txt
- https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml
- https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter
- https://raw.githubusercontent.com/mistralai/platform-docs-public/main/openapi.yaml
- https://raw.githubusercontent.com/googleapis/googleapis/master/google/ai/generativelanguage/v1beta/generative_service.proto
- https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/src/anthropic/types/message_create_params.py
- https://arxiv.org/html/2602.00182v1 ; https://arxiv.org/pdf/2502.19405 ; https://docs.gensyn.ai/tech
- https://raw.githubusercontent.com/imneme/pcg-c-basic/master/pcg_basic.c ; https://raw.githubusercontent.com/imneme/pcg-cpp/master/test-high/expected/check-pcg32.out
- https://prng.di.unimi.it/xoshiro128starstar.c ; https://prng.di.unimi.it/splitmix64.c
- https://www.rfc-editor.org/rfc/rfc8439.txt
- https://raw.githubusercontent.com/rust-random/rand/master/src/rngs/std.rs
- https://raw.githubusercontent.com/DEShawResearch/random123/main/include/Random123/philox.h ; https://raw.githubusercontent.com/DEShawResearch/random123/main/tests/kat_vectors
- https://raw.githubusercontent.com/pytorch/pytorch/main/aten/src/ATen/core/PhiloxRNGEngine.h
