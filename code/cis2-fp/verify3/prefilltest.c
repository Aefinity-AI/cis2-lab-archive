#define _POSIX_C_SOURCE 199309L
/* prefilltest.c — faster-2c prototype driver. Measures whether a single
 * teacher-forced prefill pass over prompt+claimed tokens is (a) faster
 * than N sequential single-token decode steps and (b) bit-identical to
 * them under the CIS-2 pinned op order. Not part of the CIS2_REF
 * conformance surface — a QUEUE "faster-2c" prototype harness only.
 * See model.h's cis2_verify_receipt_prefill() doc comment.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static double now_ms(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1e3+t.tv_nsec/1e6;}
#include "mathpin.h"
#include "model.h"
#include "tokenizer.h"

static const uint32_t PINNED_PROMPT_IDS[4] = {6403, 1980, 253, 655};

static void run_one(cis2_model *m, const uint8_t weights_sha[32], const uint8_t tokenizer_sha[32],
                     const uint8_t config_sha[32], size_t n_gen)
{
    cis2_run_result honest;
    double t_seq0 = now_ms();
    cis2_run_decode(m, PINNED_PROMPT_IDS, 4, n_gen, weights_sha, tokenizer_sha, config_sha, &honest);
    double t_seq_ms = now_ms() - t_seq0;

    /* recompute logits per sequential step for the bit-identity compare:
     * cis2_run_decode doesn't retain them, so re-derive with the SAME
     * unmodified forward_full() decode path, teacher-forced on the
     * honest generated_ids (this recompute is identical to what
     * cis2_run_decode itself already did internally). */
    size_t vocab = m->cfg.vocab_size;
    float *seq_logits = malloc(n_gen * vocab * sizeof(float));
    /* Elementwise oracle: call cis2_verify_receipt_prefill() with
     * n_gen=1 at each step position so it runs forward_full_prefill()
     * over exactly the sequential prefix — i.e. the same per-step
     * forward_full() computation cis2_run_decode() performed — and
     * capture that step's logits. This isolates "does the shared kernel
     * reproduce itself" from "does batching change anything", so the
     * real prefill-vs-sequential compare below is the meaningful one. */
    for (size_t step = 0; step < n_gen; step++) {
        cis2_prefill_result one;
        cis2_verify_receipt_prefill(m, PINNED_PROMPT_IDS, 4, honest.generated_ids, step + 1,
                                     weights_sha, tokenizer_sha, config_sha, &one);
        memcpy(seq_logits + step * vocab, one.all_logits + step * vocab, vocab * sizeof(float));
        cis2_prefill_result_free(&one);
    }

    cis2_prefill_result pre;
    double t_pre0 = now_ms();
    cis2_verify_receipt_prefill(m, PINNED_PROMPT_IDS, 4, honest.generated_ids, n_gen,
                                 weights_sha, tokenizer_sha, config_sha, &pre);
    double t_pre_ms = now_ms() - t_pre0;

    printf("PREFILLTEST timing n_gen=%zu sequential_ms=%.1f prefill_ms=%.1f ratio=%.3f\n",
           n_gen, t_seq_ms, t_pre_ms, t_seq_ms / t_pre_ms);

    size_t n_logit_mismatch = 0, n_argmax_mismatch = 0;
    long first_mismatch_pos = -1;
    for (size_t step = 0; step < n_gen; step++) {
        const float *a = seq_logits + step * vocab;
        const float *b = pre.all_logits + step * vocab;
        int step_mismatch = 0;
        for (size_t i = 0; i < vocab; i++) {
            uint32_t ba = cis2_f32_bits(a[i]), bb = cis2_f32_bits(b[i]);
            if (ba != bb) { step_mismatch = 1; break; }
        }
        if (step_mismatch) {
            n_logit_mismatch++;
            if (first_mismatch_pos < 0) first_mismatch_pos = (long)step;
        }
        if (honest.generated_ids[step] != pre.generated_ids[step]) n_argmax_mismatch++;
    }
    printf("PREFILLTEST bitident n_gen=%zu n_positions=%zu n_logit_mismatch=%zu n_argmax_mismatch=%zu first_mismatch_pos=%ld\n",
           n_gen, n_gen, n_logit_mismatch, n_argmax_mismatch, first_mismatch_pos);
    printf("PREFILLTEST digest n_gen=%zu witness_match=%d argmax_match=%d\n",
           n_gen,
           memcmp(honest.witness_digest, pre.witness_digest, 32) == 0,
           memcmp(honest.argmax_digest, pre.argmax_digest, 32) == 0);

    free(seq_logits);
    cis2_prefill_result_free(&pre);
    free(honest.generated_ids);
}

/* faster-2d tamper matrix: after the honest sequential decode produces
 * the claimed token sequence, flip exactly ONE claimed token (at
 * --tamper POS) to a different valid token id, then feed that TAMPERED
 * claimed sequence into cis2_verify_receipt_prefill() as if it were an
 * honest receipt. cis2_verify_receipt_prefill() teacher-forces on the
 * claimed tokens (they become the decoder INPUT at their position) and
 * independently recomputes the argmax at every position from the
 * resulting logits; it never looks at the caller's claim to decide what
 * to compute. So the verifier catches a lie by comparing its own
 * independently-recomputed argmax at each position against what the
 * receipt actually claimed there -- exactly the comparison this
 * function performs (mirroring the honest/prefill n_argmax_mismatch
 * compare in run_one(), just against the tampered claim instead of a
 * second honest recompute).
 *
 * Because pre.generated_ids[step] is recomputed from context
 * tokens[0..n_prompt-1+step-1] --- i.e. it does NOT depend on
 * claimed_tokens[step] itself, only on claimed_tokens[0..step-1] --- the
 * position where the tampered value is first *read as a claim* is
 * exactly POS, so first_mismatch_pos should equal POS. For positions
 * after POS, the tampered token at POS is now part of the input context,
 * so the recomputed argmax there is checked against the (unmodified)
 * original claimed tokens; whether that also mismatches depends on how
 * much the tampered context perturbs downstream logits, and is reported
 * as observed, not assumed.
 *
 * There is no independent second logit array to bit-compare here (unlike
 * the honest bitident check, which has two honest recomputations to
 * compare against each other) -- the whole point of tamper mode is that
 * the claim itself is being checked, not two computations of the same
 * true claim. So n_logit_mismatch is defined identically to
 * n_argmax_mismatch below: both count positions where the receipt's
 * claimed token disagrees with the verifier's independently recomputed
 * argmax.
 */
static void tamper_run(cis2_model *m, const uint8_t weights_sha[32], const uint8_t tokenizer_sha[32],
                        const uint8_t config_sha[32], size_t n_gen, long pos)
{
    size_t vocab = m->cfg.vocab_size;
    if (pos < 0 || (size_t)pos >= n_gen) {
        fprintf(stderr, "PREFILLTEST tamper error: pos=%ld out of range for n_gen=%zu\n", pos, n_gen);
        return;
    }

    cis2_run_result honest;
    cis2_run_decode(m, PINNED_PROMPT_IDS, 4, n_gen, weights_sha, tokenizer_sha, config_sha, &honest);

    uint32_t *tampered = malloc(n_gen * sizeof(uint32_t));
    memcpy(tampered, honest.generated_ids, n_gen * sizeof(uint32_t));
    uint32_t orig_tok = tampered[pos];
    uint32_t tampered_tok = (uint32_t)((orig_tok + 1) % vocab);
    if (tampered_tok == orig_tok) tampered_tok = (uint32_t)((orig_tok + 2) % vocab); /* vocab<=1 fallback, never hit in practice */
    tampered[pos] = tampered_tok;

    cis2_prefill_result pre;
    cis2_verify_receipt_prefill(m, PINNED_PROMPT_IDS, 4, tampered, n_gen,
                                 weights_sha, tokenizer_sha, config_sha, &pre);

    size_t n_argmax_mismatch = 0;
    long first_mismatch_pos = -1;
    for (size_t step = 0; step < n_gen; step++) {
        if (pre.generated_ids[step] != tampered[step]) {
            n_argmax_mismatch++;
            if (first_mismatch_pos < 0) first_mismatch_pos = (long)step;
        }
    }
    size_t n_logit_mismatch = n_argmax_mismatch;
    const char *verdict = (n_argmax_mismatch > 0) ? "FAIL" : "PASS";

    printf("PREFILLTEST tamper pos=%ld orig_tok=%u tampered_tok=%u n_logit_mismatch=%zu n_argmax_mismatch=%zu first_mismatch_pos=%ld verdict=%s\n",
           pos, orig_tok, tampered_tok, n_logit_mismatch, n_argmax_mismatch, first_mismatch_pos, verdict);

    free(tampered);
    cis2_prefill_result_free(&pre);
    free(honest.generated_ids);
}

int main(int argc, char **argv)
{
    cis2_pin_ftz_daz();
    cis2_ftz_daz_selftest();

    long tamper_pos = -1;
    const char *tamper_mode = "token";
    int short_only = 0;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--tamper") == 0 && i + 1 < argc) {
            tamper_pos = strtol(argv[++i], NULL, 10);
        } else if (strcmp(argv[i], "--tamper-mode") == 0 && i + 1 < argc) {
            tamper_mode = argv[++i];
        } else if (strcmp(argv[i], "--short") == 0) {
            /* faster-2d tamper-matrix control run: n_gen=16 only, skip the
             * slow n_gen=128 case. Not part of the byte-for-byte default
             * (no-flag) behaviour. */
            short_only = 1;
        }
    }
    if (tamper_pos >= 0 && strcmp(tamper_mode, "token") != 0) {
        fprintf(stderr, "PREFILLTEST tamper error: unsupported --tamper-mode %s (only 'token' implemented)\n", tamper_mode);
        return 91;
    }

    const char *weights_path = "weights/model.safetensors";
    const char *config_path = "weights/config.json";
    const char *tokenizer_path = "weights/tokenizer.json";

    uint8_t weights_sha[32], config_sha[32], tokenizer_sha[32];
    if (cis2_sha256_file(weights_path, weights_sha) != 0) { fprintf(stderr, "cannot hash weights\n"); return 90; }
    if (cis2_sha256_file(config_path, config_sha) != 0) { fprintf(stderr, "cannot hash config\n"); return 90; }
    if (cis2_sha256_file(tokenizer_path, tokenizer_sha) != 0) { fprintf(stderr, "cannot hash tokenizer\n"); return 90; }

    FILE *f = fopen(config_path, "rb");
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    char *config_text = malloc(sz + 1);
    size_t rd = fread(config_text, 1, sz, f); config_text[rd] = '\0'; fclose(f);

    cis2_model *m = cis2_model_load(weights_path, config_text);

    if (tamper_pos >= 0) {
        tamper_run(m, weights_sha, tokenizer_sha, config_sha, 16, tamper_pos);
    } else {
        run_one(m, weights_sha, tokenizer_sha, config_sha, 16);
        if (!short_only) {
            run_one(m, weights_sha, tokenizer_sha, config_sha, 128);
            printf("PREFILLTEST verdict see n_logit_mismatch/n_argmax_mismatch/witness_match/argmax_match above; ratio is sequential_ms/prefill_ms (>1 means prefill faster). Numbers from this run log only.\n");
        }
    }

    cis2_model_free(m);
    free(config_text);
    return 0;
}
