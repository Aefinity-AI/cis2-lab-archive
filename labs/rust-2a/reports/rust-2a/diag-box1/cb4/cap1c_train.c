/* cap1c_train.c — cap-1c FIXED-ORDER C TRAINER.
 *
 * Follow-up to cap-1/cap-1b (train/tiny_receipt_train.py, torch-based).
 * torch does not run on the phone (aarch64, no termux/python), so this is
 * a from-scratch, dependency-free scalar C reimplementation whose ONLY
 * goal is CROSS-PLATFORM SELF-IDENTITY of its own checkpoints (byte-exact
 * across x86_64 AVX2, x86_64 no-AVX2, and aarch64) -- NOT numeric parity
 * with the torch run, which uses different ops/architecture entirely.
 *
 * Determinism rules followed (see claudius-maximus state/QUEUE.md cap-1c
 * entry): fp32 only, fixed left-to-right summation order, single thread,
 * -ffp-contract=off (no FMA fusion), no libm calls whose results can
 * differ across platforms -- exp/tanh/softmax use the CIS-2 v0.2
 * mathpin.c pinned bit-exact polynomial primitives (vendored from
 * cis2-spec/verify3/, same file, unmodified) instead of libm expf/tanhf.
 * The only libm calls that remain (sqrtf via cis2_rsqrt, floorf, isnan)
 * are IEEE-754-mandated exact/exact-bit operations, not approximations.
 *
 * Model: from-scratch tiny byte-level MLP language model (embedding ->
 * tanh hidden layer -> softmax over 256 byte classes), NOT the GQA/RoPE/
 * SwiGLU ALICEModel used by cap-1's torch script -- reimplementing that
 * exactly in scalar C was out of scope for a cross-ISA identity check;
 * exact parity with cap-1 was explicitly not required by the task.
 *
 * Data: same deterministic-LCG-generated synthetic ASCII corpus
 * generator (glibc LCG constants) as tiny_receipt_train.py's
 * _build_corpus_bytes, reimplemented here in C so both are independently
 * reproducible from source, not from a shared binary blob.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>

#include "mathpin.h"
#include "sha256.h"

#define SEED        20260924u
#define TOTAL_STEPS 200
#define CKPT_EVERY  50
#define SEQ_LEN     64
#define D           16   /* embedding dim */
#define H           32   /* hidden dim */
#define VOCAB       256
#define LR          0.15f
#define CORPUS_LEN  20000

/* ---- deterministic corpus (same LCG as cap-1's _build_corpus_bytes) ---- */
static void build_corpus(uint8_t *out, size_t n)
{
    uint32_t state = SEED & 0xFFFFFFFFu;
    for (size_t i = 0; i < n; i++) {
        state = (uint32_t)(1103515245u * state + 12345u) & 0x7FFFFFFFu;
        out[i] = (uint8_t)(0x20 + (state % (0x7Fu - 0x20u)));
    }
}

/* ---- deterministic weight init: separate fixed LCG, values in [-s, s] ---- */
static uint32_t init_state = SEED ^ 0xA5A5A5A5u;
static float next_init_val(float scale)
{
    init_state = (uint32_t)(1103515245u * init_state + 12345u) & 0x7FFFFFFFu;
    float u = (float)(init_state % 1000000u) / 1000000.0f; /* [0,1) */
    return (u * 2.0f - 1.0f) * scale;
}

/* tanh via the pinned exp primitive: tanh(x) = (e^{2x}-1)/(e^{2x}+1) */
static float tanh_pinned(float x)
{
    float two_x = x + x;
    float e = cis2_exp_pinned(two_x);
    float num = e - 1.0f;
    float den = e + 1.0f;
    return num / den;
}

typedef struct {
    float V[VOCAB * D];
    float W1[H * D];   /* [out=H, in=D], row-major, per cis2_matvec convention */
    float b1[H];
    float W2[VOCAB * H]; /* [out=VOCAB, in=H] */
    float b2[VOCAB];
} Params;

static void init_params(Params *p)
{
    for (int i = 0; i < VOCAB * D; i++) p->V[i] = next_init_val(0.1f);
    for (int i = 0; i < H * D; i++) p->W1[i] = next_init_val(0.1f);
    for (int i = 0; i < H; i++) p->b1[i] = 0.0f;
    for (int i = 0; i < VOCAB * H; i++) p->W2[i] = next_init_val(0.1f);
    for (int i = 0; i < VOCAB; i++) p->b2[i] = 0.0f;
}

/* checkpoint digest: sha256 over raw fp32 bytes, fixed field order
 * V, W1, b1, W2, b2 -- identical convention to cap-1's raw-tensor-bytes
 * digest (native-endian; all four target hosts are little-endian). */
static void checkpoint_sha256(const Params *p, uint8_t out[32])
{
    cis2_sha256_ctx ctx;
    cis2_sha256_init(&ctx);
    cis2_sha256_update(&ctx, (const uint8_t *)p->V, sizeof(p->V));
    cis2_sha256_update(&ctx, (const uint8_t *)p->W1, sizeof(p->W1));
    cis2_sha256_update(&ctx, (const uint8_t *)p->b1, sizeof(p->b1));
    cis2_sha256_update(&ctx, (const uint8_t *)p->W2, sizeof(p->W2));
    cis2_sha256_update(&ctx, (const uint8_t *)p->b2, sizeof(p->b2));
    cis2_sha256_final(&ctx, out);
}

static void write_hex(const uint8_t h[32], char out[65])
{
    static const char hexd[] = "0123456789abcdef";
    for (int i = 0; i < 32; i++) {
        out[2 * i] = hexd[(h[i] >> 4) & 0xF];
        out[2 * i + 1] = hexd[h[i] & 0xF];
    }
    out[64] = '\0';
}

typedef struct {
    float dV[VOCAB * D];
    float dW1[H * D];
    float db1[H];
    float dW2[VOCAB * H];
    float db2[VOCAB];
} Grads;

static void zero_grads(Grads *g)
{
    memset(g, 0, sizeof(*g));
}

int main(int argc, char **argv)
{
    const char *out_dir = (argc > 1) ? argv[1] : "artifacts/cap1c_receipt";
    cis2_pin_ftz_daz();
    cis2_ftz_daz_selftest();

    uint8_t *corpus = malloc(CORPUS_LEN);
    build_corpus(corpus, CORPUS_LEN);

    char cmd[512];
    snprintf(cmd, sizeof(cmd), "mkdir -p %s", out_dir);
    system(cmd);

    Params p;
    init_params(&p);
    Grads g;

    /* rust-2a patch: --export-inputs DIR writes the initial weights and the
     * batch order (byte_in, byte_target per position, 200 x 64 pairs) and
     * prints their sha256. No arithmetic is changed. */
    if (argc > 3 && strcmp(argv[2], "--export-inputs") == 0) {
        char pa[512], pb[512];
        snprintf(pa, sizeof(pa), "%s/init_params.bin", argv[3]);
        snprintf(pb, sizeof(pb), "%s/batch_order.bin", argv[3]);
        FILE *fa = fopen(pa, "wb");
        fwrite(p.V, sizeof(p.V), 1, fa); fwrite(p.W1, sizeof(p.W1), 1, fa);
        fwrite(p.b1, sizeof(p.b1), 1, fa); fwrite(p.W2, sizeof(p.W2), 1, fa);
        fwrite(p.b2, sizeof(p.b2), 1, fa); fclose(fa);
        FILE *fb = fopen(pb, "wb");
        for (int st = 1; st <= TOTAL_STEPS; st++)
            for (int tt = 0; tt < SEQ_LEN; tt++) {
                size_t ix = (((size_t)(st - 1)) * SEQ_LEN + tt) % (CORPUS_LEN - 1);
                uint8_t pr[2] = { corpus[ix], corpus[ix + 1] };
                fwrite(pr, 1, 2, fb);
            }
        fclose(fb);
        uint8_t dg[32]; char hx[65];
        checkpoint_sha256(&p, dg); write_hex(dg, hx);
        fprintf(stderr, "EXPORT init_checkpoint_sha256=%s (sha256 of the same 5 arrays, file sha256 via sha256sum)\n", hx);
    }
    struct timespec t_start;
    clock_gettime(CLOCK_MONOTONIC, &t_start);

    char manifest_path[512];
    snprintf(manifest_path, sizeof(manifest_path), "%s/manifest.json", out_dir);
    FILE *mf = fopen(manifest_path, "w");
    fprintf(mf, "{\n  \"seed\": %u,\n  \"total_steps\": %d,\n  \"ckpt_every\": %d,\n  \"seq_len\": %d,\n  \"d_model\": %d,\n  \"hidden\": %d,\n  \"vocab\": %d,\n  \"lr\": %f,\n  \"checkpoints\": [\n",
            SEED, TOTAL_STEPS, CKPT_EVERY, SEQ_LEN, D, H, VOCAB, LR);

    int first_entry = 1;
    float *h_pre = malloc(H * sizeof(float));
    float *h_act = malloc(H * sizeof(float));
    float *logits = malloc(VOCAB * sizeof(float));
    float *probs = malloc(VOCAB * sizeof(float));
    float *dlogits = malloc(VOCAB * sizeof(float));
    float *dh_act = malloc(H * sizeof(float));
    float *dh_pre = malloc(H * sizeof(float));

    for (int step = 1; step <= TOTAL_STEPS; step++) {
        zero_grads(&g);
        size_t block_start = ((size_t)(step - 1)) * SEQ_LEN;
        float loss_acc = 0.0f;

        for (int t = 0; t < SEQ_LEN; t++) {
            size_t idx = (block_start + t) % (CORPUS_LEN - 1);
            uint8_t byte_in = corpus[idx];
            uint8_t byte_target = corpus[idx + 1];
            const float *x = &p.V[(size_t)byte_in * D];

            /* forward */
            cis2_matvec(p.W1, x, h_pre, H, D);
            for (int hh = 0; hh < H; hh++) h_pre[hh] = h_pre[hh] + p.b1[hh];
            for (int hh = 0; hh < H; hh++) h_act[hh] = tanh_pinned(h_pre[hh]);

            cis2_matvec(p.W2, h_act, logits, VOCAB, H);
            for (int o = 0; o < VOCAB; o++) logits[o] = logits[o] + p.b2[o];

            float m = logits[0];
            for (int o = 1; o < VOCAB; o++) if (logits[o] > m) m = logits[o];
            float sum = 0.0f;
            for (int o = 0; o < VOCAB; o++) {
                float e = cis2_exp_pinned(logits[o] - m);
                probs[o] = e;
                sum = sum + e;
            }
            for (int o = 0; o < VOCAB; o++) probs[o] = probs[o] / sum;
            float logsum = cis2_ln_pinned(sum);
            float loss = -(logits[byte_target] - m) + logsum;
            loss_acc = loss_acc + loss;

            /* backward */
            for (int o = 0; o < VOCAB; o++)
                dlogits[o] = probs[o] - ((o == byte_target) ? 1.0f : 0.0f);

            for (int o = 0; o < VOCAB; o++) {
                float dlo = dlogits[o];
                for (int hh = 0; hh < H; hh++)
                    g.dW2[(size_t)o * H + hh] = g.dW2[(size_t)o * H + hh] + dlo * h_act[hh];
                g.db2[o] = g.db2[o] + dlo;
            }

            for (int hh = 0; hh < H; hh++) {
                float acc = 0.0f;
                for (int o = 0; o < VOCAB; o++)
                    acc = acc + dlogits[o] * p.W2[(size_t)o * H + hh];
                dh_act[hh] = acc;
            }
            for (int hh = 0; hh < H; hh++) {
                float t2 = h_act[hh] * h_act[hh];
                float deriv = 1.0f - t2;
                dh_pre[hh] = dh_act[hh] * deriv;
            }

            for (int hh = 0; hh < H; hh++) {
                float dh = dh_pre[hh];
                for (int dd = 0; dd < D; dd++)
                    g.dW1[(size_t)hh * D + dd] = g.dW1[(size_t)hh * D + dd] + dh * x[dd];
                g.db1[hh] = g.db1[hh] + dh;
            }

            for (int dd = 0; dd < D; dd++) {
                float acc = 0.0f;
                for (int hh = 0; hh < H; hh++)
                    acc = acc + dh_pre[hh] * p.W1[(size_t)hh * D + dd];
                g.dV[(size_t)byte_in * D + dd] = g.dV[(size_t)byte_in * D + dd] + acc;
            }
        }

        float scale = LR / (float)SEQ_LEN;
        for (int i = 0; i < VOCAB * D; i++) p.V[i] = p.V[i] - scale * g.dV[i];
        for (int i = 0; i < H * D; i++) p.W1[i] = p.W1[i] - scale * g.dW1[i];
        for (int i = 0; i < H; i++) p.b1[i] = p.b1[i] - scale * g.db1[i];
        for (int i = 0; i < VOCAB * H; i++) p.W2[i] = p.W2[i] - scale * g.dW2[i];
        for (int i = 0; i < VOCAB; i++) p.b2[i] = p.b2[i] - scale * g.db2[i];

        if (step % CKPT_EVERY == 0) {
            uint8_t digest[32];
            char hex[65];
            checkpoint_sha256(&p, digest);
            write_hex(digest, hex);
            float avg_loss = loss_acc / (float)SEQ_LEN;

            char ckpt_path[512];
            snprintf(ckpt_path, sizeof(ckpt_path), "%s/ckpt_step%03d.bin", out_dir, step);
            FILE *cf = fopen(ckpt_path, "wb");
            fwrite(p.V, sizeof(p.V), 1, cf);
            fwrite(p.W1, sizeof(p.W1), 1, cf);
            fwrite(p.b1, sizeof(p.b1), 1, cf);
            fwrite(p.W2, sizeof(p.W2), 1, cf);
            fwrite(p.b2, sizeof(p.b2), 1, cf);
            fclose(cf);

            if (!first_entry) fprintf(mf, ",\n");
            first_entry = 0;
            fprintf(mf, "    {\"step\": %d, \"loss\": %f, \"checkpoint_sha256\": \"%s\", \"checkpoint_file\": \"ckpt_step%03d.bin\"}",
                    step, avg_loss, hex, step);
            fprintf(stderr, "step=%d loss=%f sha256=%s\n", step, avg_loss, hex);
        }
    }

    {
        struct timespec t_end;
        clock_gettime(CLOCK_MONOTONIC, &t_end);
        fprintf(stderr, "TRAIN_WALL_S=%.6f\n", (double)(t_end.tv_sec - t_start.tv_sec) + (double)(t_end.tv_nsec - t_start.tv_nsec) * 1e-9);
    }
    fprintf(mf, "\n  ]\n}\n");
    fclose(mf);

    free(corpus);
    free(h_pre); free(h_act); free(logits); free(probs);
    free(dlogits); free(dh_act); free(dh_pre);
    return 0;
}
