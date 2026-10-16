/* model.h — CIS-2 v0.2 model load + forward pass + witness/argmax digests. */
#ifndef CIS2_V3_MODEL_H
#define CIS2_V3_MODEL_H

#include <stdint.h>
#include <stddef.h>

typedef struct {
    size_t hidden_size;
    size_t intermediate_size;
    size_t num_hidden_layers;
    size_t num_attention_heads;
    size_t num_key_value_heads;
    float rms_norm_eps;
    float rope_theta;
    int tie_word_embeddings;
    size_t vocab_size;
} cis2_config;

typedef struct {
    float *input_layernorm;      /* [hidden] */
    float *post_attention_layernorm; /* [hidden] */
    float *q_proj;   /* [hidden, hidden] */
    float *k_proj;   /* [n_kv*head_dim, hidden] */
    float *v_proj;   /* [n_kv*head_dim, hidden] */
    float *o_proj;   /* [hidden, hidden] */
    float *gate_proj; /* [inter, hidden] */
    float *up_proj;   /* [inter, hidden] */
    float *down_proj; /* [hidden, inter] */
    float *q_bias; /* optional, NULL if absent */
    float *k_bias;
    float *v_bias;
} cis2_layer;

typedef struct {
    cis2_config cfg;
    float *embed_tokens; /* [vocab, hidden] */
    cis2_layer *layers;
    float *norm_weight; /* [hidden] */
    float *lm_head; /* optional separate tensor; NULL if tied */
    float *inv_freq; /* [head_dim/2] */
    size_t head_dim;
    size_t half;
    size_t group;
} cis2_model;

int cis2_sha256_file(const char *path, uint8_t out[32]);

/* E15k debug-only: enable/disable the CIS2_DUMP per-layer state
 * side-channel (see model.c dump_line()). Not part of any normative
 * digest; gated on env var CIS2_DUMP_LAYERS in main.c. */
void cis2_set_dump_layers(int enabled);

/* config_json_text and safetensors_path: config is parsed from text,
 * weights loaded (and bf16->f32 widened) from the safetensors file. */
cis2_model *cis2_model_load(const char *safetensors_path, const char *config_json_text);
void cis2_model_free(cis2_model *m);

typedef struct {
    uint32_t *generated_ids; /* [n_gen] */
    size_t n_gen;
    uint8_t witness_digest[32];
    uint8_t argmax_digest[32];
    uint8_t table_digest[32];
    uint8_t inv_freq_table_digest[32];
} cis2_run_result;

/* Runs the full greedy decode (spec §3.4/§11/§12) once. weights_sha256,
 * tokenizer_sha256, config_sha256 are the raw 32-byte artifact hashes fed
 * into the witness chain (§12.1 items 3-5). */
void cis2_run_decode(const cis2_model *m,
                       const uint32_t *prompt_ids, size_t n_prompt, size_t n_gen,
                       const uint8_t weights_sha256[32],
                       const uint8_t tokenizer_sha256[32],
                       const uint8_t config_sha256[32],
                       cis2_run_result *out);

/* ---- faster-2 (QUEUE item, cm/faster2-verify-fastpath) ------------------
 *
 * cis2_run_decode() above is the spec-exact, unmodified verifier: it
 * self-drives greedy decode and computes+hashes the FULL fp32 logit vector
 * (vocab_size entries) into the witness chain at every step. That is the
 * only mode that reproduces the normative CIS2_REF witness_digest (§12.1)
 * bit-for-bit and is the sole source of truth for conformance.
 *
 * cis2_verify_receipt_fast() below is a PROTOTYPE, non-normative fast
 * verification path for an already-produced receipt (a claimed
 * generated_token_ids sequence, teacher-forced). For a random subset of
 * steps ("audited" steps, ~audit_fraction of them, chosen by a seeded PRNG
 * so runs are reproducible) it does the exact same full-logit recompute +
 * argmax check as the full verifier: if the receipt's claimed token is not
 * the true recomputed argmax on an audited step, this is tamper and
 * verification FAILs immediately. For steps NOT selected for audit, it
 * skips the full vocab_size-wide logit computation and instead does a
 * cheap O(1) plausibility check: compute the logit at just the claimed
 * token's index plus a handful of fixed/deterministic reference indices,
 * and fail if the claimed token is beaten by any of them. This cheap
 * check is *not* a proof the claimed token is the true argmax — see
 * cis2_fast_verify_result.audited[] and the CLEANROOM_LOG / QUEUE report
 * for the exact, honest detection-probability statement. Never used to
 * claim conformance; only cis2_run_decode()'s output is CIS2_REF. */
typedef struct {
    int ok;                 /* 1 = no tamper detected, 0 = FAIL */
    long fail_step;         /* -1 if ok, else index of first failing step */
    const char *fail_reason;/* static string, non-NULL iff !ok */
    size_t n_gen;
    size_t n_audited;        /* how many steps got the full recompute+hash */
    uint8_t *audited;        /* [n_gen], 1 if that step was full-audited */
    uint8_t argmax_digest_self[32]; /* recomputed over prompt+claimed tokens */
} cis2_fast_verify_result;

void cis2_verify_receipt_fast(const cis2_model *m,
                                const uint32_t *prompt_ids, size_t n_prompt,
                                const uint32_t *claimed_tokens, size_t n_gen,
                                uint64_t audit_seed, double audit_fraction,
                                cis2_fast_verify_result *out);

void cis2_fast_verify_result_free(cis2_fast_verify_result *r);

/* ---- faster-2c (QUEUE item, cm/faster2c-prefill-verify) -----------------
 *
 * cis2_run_decode() calls forward_full(tokens, ntok) once per generated
 * step with ntok growing by 1 each time (no KV cache carried between
 * calls): step p redoes the ENTIRE prefix 0..p from scratch, so total
 * work is O(n_gen^2) matvec/attention, and every layer's weight matrices
 * are re-streamed from RAM n_gen times.
 *
 * cis2_verify_receipt_prefill() below does ONE forward pass over the
 * whole prompt+claimed sequence (teacher-forced) and, at the end of the
 * shared layer loop, runs the SAME final-rmsnorm + SAME lm_head matvec
 * (byte-for-byte the same per-position code as forward_full) at every
 * claimed position instead of only the last. Because every intermediate
 * quantity h[p] at a given layer is a pure function of tokens[0..p] under
 * the causal mask (attention only sums j<=p; RoPE/rmsnorm/MLP are
 * per-position), and the per-position ops are computed with identical
 * loop nesting/accumulation order regardless of ntok, this is expected
 * to reproduce cis2_run_decode's per-step logits bit-for-bit -- that is
 * exactly the hypothesis prefilltest.c's bitident check measures, not an
 * assumption to take on faith. */
typedef struct {
    uint8_t witness_digest[32];
    uint8_t argmax_digest[32];
    uint8_t table_digest[32];          /* same construction as cis2_run_result's */
    uint8_t inv_freq_table_digest[32]; /* same construction as cis2_run_result's */
    uint32_t *generated_ids;   /* [n_gen], argmax at each claimed position */
    float *all_logits;         /* [n_gen * vocab_size], row-major by step */
    size_t n_gen;
    size_t vocab_size;
} cis2_prefill_result;

void cis2_verify_receipt_prefill(const cis2_model *m,
                                   const uint32_t *prompt_ids, size_t n_prompt,
                                   const uint32_t *claimed_tokens, size_t n_gen,
                                   const uint8_t weights_sha256[32],
                                   const uint8_t tokenizer_sha256[32],
                                   const uint8_t config_sha256[32],
                                   cis2_prefill_result *out);

void cis2_prefill_result_free(cis2_prefill_result *r);

#endif
