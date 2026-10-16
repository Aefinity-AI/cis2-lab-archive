/* vecgen.c: writes fixed test vectors from the C original (mathpin.c vendored, unmodified) for the
 * Rust unit tests: exp / ln / tanh over fixed input bit patterns, and the forward layer chain for
 * batch position 0 with the exported initial weights. Not part of the trainer.
 * build: gcc -O2 -ffp-contract=off -fno-fast-math -fexcess-precision=standard -std=c11 -mno-fma \
 *        -o vecgen vecgen.c mathpin.c sha256.c -lm      usage: vecgen init_params.bin batch_order.bin > vectors.txt */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "mathpin.h"
#define D 16
#define H 32
#define VOCAB 256
static uint32_t st = 0x1234567u;
static uint32_t rnd(void) { st = (uint32_t)(1103515245u * st + 12345u) & 0x7FFFFFFFu; st ^= st << 7; return st; }
static float tanh_pinned(float x) { float e = cis2_exp_pinned(x + x); float num = e - 1.0f; float den = e + 1.0f; return num / den; }
static void pr(const char *tag, const float *a, int n) { printf("%s", tag); for (int i = 0; i < n; i++) printf(i ? " %08x" : "%08x", cis2_f32_bits(a[i])); printf("\n"); }
int main(int argc, char **argv)
{
    cis2_pin_ftz_daz();
    cis2_ftz_daz_selftest();
    static const uint32_t spec_in[] = { 0x00000000u, 0x80000000u, 0x00000001u, 0x007FFFFFu, 0x00800000u, 0x3F800000u, 0xBF800000u,
        0x42B00000u, 0xC2B00000u, 0x42B00001u, 0xC2B00001u, 0x7F800000u, 0xFF800000u, 0x3F000000u, 0x40000000u, 0x3A83126Fu };
    for (size_t i = 0; i < sizeof(spec_in) / 4; i++) {
        float x = cis2_f32_from_bits(spec_in[i]);
        printf("exp %08x %08x\n", spec_in[i], cis2_f32_bits(cis2_exp_pinned(x)));
        printf("ln %08x %08x\n", spec_in[i], cis2_f32_bits(cis2_ln_pinned(x)));
        printf("tanh %08x %08x\n", spec_in[i], cis2_f32_bits(tanh_pinned(x)));
    }
    for (int i = 0; i < 3000; i++) {
        float u = (float)(rnd() % 2000001u) / 1000000.0f - 1.0f;  /* [-1,1] */
        float xe = u * 100.0f, xt = u * 12.0f;
        uint32_t lb = rnd() & 0x7FFFFFFFu; if (lb >= 0x7F800000u) lb &= 0x7F7FFFFFu;
        float xl = (i % 2) ? cis2_f32_from_bits(lb) : (u < 0 ? -u : u) * 300.0f;
        printf("exp %08x %08x\n", cis2_f32_bits(xe), cis2_f32_bits(cis2_exp_pinned(xe)));
        printf("ln %08x %08x\n", cis2_f32_bits(xl), cis2_f32_bits(cis2_ln_pinned(xl)));
        printf("tanh %08x %08x\n", cis2_f32_bits(xt), cis2_f32_bits(tanh_pinned(xt)));
    }
    if (argc > 2) {
        static float V[VOCAB * D], W1[H * D], b1[H], W2[VOCAB * H], b2[VOCAB];
        FILE *f = fopen(argv[1], "rb");
        if (!f || fread(V, sizeof V, 1, f) != 1 || fread(W1, sizeof W1, 1, f) != 1 || fread(b1, sizeof b1, 1, f) != 1 ||
            fread(W2, sizeof W2, 1, f) != 1 || fread(b2, sizeof b2, 1, f) != 1) { fprintf(stderr, "bad init\n"); return 1; }
        fclose(f);
        uint8_t pair[2];
        f = fopen(argv[2], "rb"); if (!f || fread(pair, 2, 1, f) != 1) { fprintf(stderr, "bad batch\n"); return 1; } fclose(f);
        float h_pre[H], h_act[H], logits[VOCAB], probs[VOCAB];
        const float *x = &V[(size_t)pair[0] * D];
        /* same statements as cap1c_train.c forward, position 0 */
        cis2_matvec(W1, x, h_pre, H, D);
        for (int hh = 0; hh < H; hh++) h_pre[hh] = h_pre[hh] + b1[hh];
        for (int hh = 0; hh < H; hh++) h_act[hh] = tanh_pinned(h_pre[hh]);
        cis2_matvec(W2, h_act, logits, VOCAB, H);
        for (int o = 0; o < VOCAB; o++) logits[o] = logits[o] + b2[o];
        float m = logits[0];
        for (int o = 1; o < VOCAB; o++) if (logits[o] > m) m = logits[o];
        float sum = 0.0f;
        for (int o = 0; o < VOCAB; o++) { float e = cis2_exp_pinned(logits[o] - m); probs[o] = e; sum = sum + e; }
        for (int o = 0; o < VOCAB; o++) probs[o] = probs[o] / sum;
        float logsum = cis2_ln_pinned(sum);
        float loss = -(logits[pair[1]] - m) + logsum;
        pr("fwd0_hpre ", h_pre, H); pr("fwd0_hact ", h_act, H); pr("fwd0_logits ", logits, VOCAB);
        pr("fwd0_probs ", probs, VOCAB); pr("fwd0_loss ", &loss, 1);
    }
    return 0;
}
