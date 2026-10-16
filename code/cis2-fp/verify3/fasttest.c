#define _POSIX_C_SOURCE 199309L
/* fasttest.c — faster-2 prototype driver: runs the full spec-exact
 * decode once to get a genuine (untampered) receipt, confirms the fast
 * verifier accepts it, then runs a small tamper-mutant matrix (single
 * corrupted step, at several positions, across several audit seeds) and
 * reports whether/how the fast verifier catches each mutant. Not part of
 * the CIS2_REF conformance surface — a QUEUE "faster-2" prototype
 * harness only. See docs/CIS2_SPEC_v0.3.md for the spec this recomputes
 * against, and model.h's cis2_verify_receipt_fast() doc comment for the
 * precise, honest guarantee this fast path provides.
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

int main(void)
{
    cis2_pin_ftz_daz();
    cis2_ftz_daz_selftest();

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

    /* ground-truth honest receipt via the unmodified, spec-exact decoder */
    cis2_run_result honest;
    double t_full0 = now_ms();
    cis2_run_decode(m, PINNED_PROMPT_IDS, 4, 16, weights_sha, tokenizer_sha, config_sha, &honest);
    double t_full_ms = now_ms() - t_full0;
    printf("FASTTEST timing full_decode_ms=%.1f n_gen=%zu\n", t_full_ms, honest.n_gen);
    printf("FASTTEST honest generated_token_ids=");
    for (size_t i = 0; i < honest.n_gen; i++) printf("%s%u", i ? "," : "", honest.generated_ids[i]);
    printf("\n");

    /* 1. fast-verify on the honest, untampered receipt: must PASS for every seed. */
    int honest_pass_count = 0, honest_total = 5;
    double t_fast_sum = 0.0;
    for (uint64_t seed = 1; seed <= (uint64_t)honest_total; seed++) {
        cis2_fast_verify_result r;
        double t0 = now_ms();
        cis2_verify_receipt_fast(m, PINNED_PROMPT_IDS, 4, honest.generated_ids, honest.n_gen, seed, 0.10, &r);
        double dt = now_ms() - t0; t_fast_sum += dt;
        printf("FASTTEST timing fast_verify_ms=%.1f seed=%llu n_audited=%zu/%zu\n", dt, (unsigned long long)seed, r.n_audited, r.n_gen);
        if (r.ok) honest_pass_count++;
        else printf("FASTTEST UNEXPECTED FAIL on honest receipt seed=%llu step=%ld reason=%s\n",
                    (unsigned long long)seed, r.fail_step, r.fail_reason);
        cis2_fast_verify_result_free(&r);
    }
    printf("FASTTEST honest_receipt: %d/%d seeds PASS (expect %d/%d)\n",
           honest_pass_count, honest_total, honest_total, honest_total);
    printf("FASTTEST timing mean_fast_verify_ms=%.1f full_decode_ms=%.1f ratio_full_over_fast=%.3f\n",
           t_fast_sum / honest_total, t_full_ms, t_full_ms / (t_fast_sum / honest_total));

    /* 2. tamper matrix: corrupt one step's claimed token, try several
     * positions x several audit seeds. */
    size_t mutate_steps[] = {0, 4, 8, 12, 15};
    size_t n_mutate = sizeof(mutate_steps) / sizeof(mutate_steps[0]);
    uint64_t seeds[] = {1, 2, 3, 4};
    size_t n_seeds = sizeof(seeds) / sizeof(seeds[0]);

    size_t total_trials = 0, caught_audited = 0, caught_cheap = 0, missed = 0;

    for (size_t mi = 0; mi < n_mutate; mi++) {
        size_t step = mutate_steps[mi];
        uint32_t *mutant = malloc(honest.n_gen * sizeof(uint32_t));
        memcpy(mutant, honest.generated_ids, honest.n_gen * sizeof(uint32_t));
        /* flip the token: change to a different, in-range vocab id */
        uint32_t orig = mutant[step];
        mutant[step] = (orig + 1) % 49152;
        if (mutant[step] == orig) mutant[step] = (orig + 2) % 49152;

        for (size_t si = 0; si < n_seeds; si++) {
            cis2_fast_verify_result r;
            cis2_verify_receipt_fast(m, PINNED_PROMPT_IDS, 4, mutant, honest.n_gen, seeds[si], 0.10, &r);
            total_trials++;
            if (!r.ok && r.fail_step == (long)step) {
                if (strstr(r.fail_reason, "audited")) caught_audited++;
                else caught_cheap++;
            } else if (!r.ok) {
                /* caught, but reported failing at a different step than the
                 * mutated one (can legitimately happen: forward pass from
                 * the mutated token onward differs, so a later audited
                 * step can also fail first if it's reached before step
                 * itself is scrutinized -- but our loop mutates step then
                 * feeds it forward immediately, so the first check AT
                 * `step` is always the first place divergence could be
                 * caught; a fail at a later step means step's own cheap
                 * check passed and a downstream audited step caught the
                 * propagated effect instead). Still counts as "caught".*/
                if (strstr(r.fail_reason, "audited")) caught_audited++;
                else caught_cheap++;
                printf("FASTTEST note: mutate_step=%zu seed=%llu caught at different step=%ld reason=%s\n",
                       step, (unsigned long long)seeds[si], r.fail_step, r.fail_reason);
            } else {
                missed++;
                printf("FASTTEST MISS: mutate_step=%zu seed=%llu not caught (audited=%zu/16)\n",
                       step, (unsigned long long)seeds[si], r.n_audited);
            }
            cis2_fast_verify_result_free(&r);
        }
        free(mutant);
    }

    printf("FASTTEST tamper_matrix: trials=%zu caught_by_audit=%zu caught_by_cheap_check=%zu missed=%zu\n",
           total_trials, caught_audited, caught_cheap, missed);

    free(honest.generated_ids);
    cis2_model_free(m);
    free(config_text);
    return 0;
}
