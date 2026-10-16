//! CIS-2 E15b milestone 1 — fp32 reference forward pass for
//! HuggingFaceTB/SmolLM2-135M. Published 2026-10-16 as part of the CIS-2 archive.
//! See docs/E15b_REFERENCE_RESULT.md for the full writeup, repro commands,
//! and honest open questions.
//!
//! E15d additions (see docs/E15d_bc_RESULT.md): `--gen-toks N`,
//! `--prompt-set FILE` (JSON array of prompt strings) for milestone (b);
//! optional QKV bias + untied LM head + generic rope_theta (via the new
//! `math::ln_pinned`) for milestone (c)'s second model family
//! (Qwen2.5-0.5B-Instruct). With no CLI args, behavior is unchanged from
//! E15c (single default prompt, gen_toks=16) except that the printed
//! `table_digest=` value changed because `math::table_digest()` now also
//! covers the new `ln_pinned` coefficient table.

mod denormal;
mod math;
mod stream_widen;
mod whole_buffer_widen;

use math::{dot_seq, exp_pinned, rsqrt_cr, silu_pinned, softmax_seq};
use sha2::{Digest, Sha256};
use std::path::Path;

/// v0.4 CANDIDATE (E18c) — which reduction order a run uses. `Sequential`
/// (the default) reproduces v0.3b's strict left-to-right accumulation
/// byte-for-byte: the `dot`/`sum`/`softmax` wrappers below call exactly
/// the pre-existing `dot_seq`/`math::sum_seq`/`softmax_seq`, unmodified,
/// with no other code path in between. `Tree` routes the same call sites
/// through `math::tree_dot`/`math::tree_sum`/`math::softmax_tree` (see
/// docs/design/CIS2_V04_TREE_REDUCTION.md). The mode is printed as
/// receipt metadata (`reduction_mode=`) alongside `CIS2_REF` but is NOT
/// folded into the witness hash — see the design doc §5 for why.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Reduction {
    Sequential,
    Tree,
}

impl Reduction {
    fn as_str(self) -> &'static str {
        match self {
            Reduction::Sequential => "sequential",
            Reduction::Tree => "tree",
        }
    }
}

#[inline]
fn dot(a: &[f32], b: &[f32], r: Reduction) -> f32 {
    match r {
        Reduction::Sequential => dot_seq(a, b),
        Reduction::Tree => math::tree_dot(a, b),
    }
}

#[inline]
fn sum(a: &[f32], r: Reduction) -> f32 {
    match r {
        Reduction::Sequential => math::sum_seq(a),
        Reduction::Tree => math::tree_sum(a),
    }
}

#[inline]
fn softmax(scores: &mut [f32], r: Reduction) {
    match r {
        Reduction::Sequential => softmax_seq(scores),
        Reduction::Tree => math::softmax_tree(scores),
    }
}

struct LayerWeights {
    input_layernorm: Vec<f32>,
    post_attention_layernorm: Vec<f32>,
    q_proj: Vec<f32>,    // [576,576] row-major [out,in]
    k_proj: Vec<f32>,    // [192,576]
    v_proj: Vec<f32>,    // [192,576]
    o_proj: Vec<f32>,    // [576,576]
    gate_proj: Vec<f32>, // [1536,576]
    up_proj: Vec<f32>,   // [1536,576]
    down_proj: Vec<f32>, // [576,1536]
    // E15d(c): optional QKV bias (Qwen2-family checkpoints set
    // attention_bias=true; Llama-family SmolLM2 has none of these tensors
    // in the checkpoint, so these stay None and forward_token adds nothing).
    q_bias: Option<Vec<f32>>,
    k_bias: Option<Vec<f32>>,
    v_bias: Option<Vec<f32>>,
}

/// LLM-8b: opt-in per-layer streaming context. When `Model.stream` is
/// `Some`, `Model.layers` is left empty and `forward_token` instead loads
/// each layer's weights from disk immediately before it is used (via
/// `load_layer_weights`, the exact same tensor-name/shape/order sequence
/// as the eager preload path below) and drops them at the end of that
/// layer's scope, so at most one layer's f32 weights are resident at a
/// time. This is a pure loader/ordering change: `load_layer_weights` calls
/// `stream_widen::load_tensor_streaming` with the same names, shapes, and
/// element order the eager path already used, so the arithmetic and the
/// resulting `CIS2_REF` digest are unchanged (see
/// `stream_widen::tests::streaming_matches_whole_buffer_bit_for_bit` and
/// the SmolLM2-135M `--stream-weights` vs. default digest match this flag
/// exists to prove). Note: because `forward_token` is called once per
/// generated token, streaming mode re-reads and re-widens every layer's
/// raw bytes from disk on every token (not cached across the run) --- more
/// disk I/O than the eager path, not a correctness difference.
struct StreamCtx {
    weights_file: std::cell::RefCell<std::fs::File>,
    tensor_index: std::collections::HashMap<String, stream_widen::TensorEntry>,
    data_start: u64,
}

struct Model {
    embed_tokens: Vec<f32>, // [vocab*hidden]
    layers: Vec<LayerWeights>,
    final_norm: Vec<f32>,
    hidden: usize,
    inter: usize,
    n_layers: usize,
    n_heads: usize,
    n_kv_heads: usize,
    head_dim: usize,
    vocab: usize,
    eps: f32,
    inv_freq: Vec<f32>, // len head_dim/2
    // E15d(c): tied embeddings reuse embed_tokens for the LM head (as
    // SmolLM2-135M does); an untied checkpoint provides a separate
    // lm_head.weight tensor here instead.
    lm_head: Option<Vec<f32>>,
    // LLM-8b: `Some` iff `--stream-weights` was passed; `layers` is empty
    // in that case and each layer is loaded lazily via `stream`.
    stream: Option<StreamCtx>,
}

/// LLM-8b: loads exactly one transformer layer's weights, in the same
/// tensor order the eager preload loop below uses. Shared by both the
/// eager path (called once per layer, up front, result stored in
/// `Model.layers`) and the `--stream-weights` path (called once per layer
/// per `forward_token` invocation, result dropped at the end of that
/// layer's iteration) so the two paths cannot drift apart.
fn load_layer_weights(
    weights_file: &std::cell::RefCell<std::fs::File>,
    data_start: u64,
    tensor_index: &std::collections::HashMap<String, stream_widen::TensorEntry>,
    li: usize,
    hidden: usize,
    inter: usize,
    n_kv_heads: usize,
    head_dim: usize,
) -> LayerWeights {
    let p = |suffix: &str| format!("model.layers.{li}.{suffix}");
    let load_f32_tensor = |name: &str, expect_shape: &[usize]| -> Vec<f32> {
        stream_widen::load_tensor_streaming(
            &mut *weights_file.borrow_mut(),
            data_start,
            tensor_index,
            name,
            expect_shape,
        )
    };
    let load_bias_opt = |name: &str, len: usize| -> Option<Vec<f32>> {
        if tensor_index.contains_key(name) {
            Some(load_f32_tensor(name, &[len]))
        } else {
            None
        }
    };
    LayerWeights {
        input_layernorm: load_f32_tensor(&p("input_layernorm.weight"), &[hidden]),
        post_attention_layernorm: load_f32_tensor(
            &p("post_attention_layernorm.weight"),
            &[hidden],
        ),
        q_proj: load_f32_tensor(&p("self_attn.q_proj.weight"), &[hidden, hidden]),
        k_proj: load_f32_tensor(
            &p("self_attn.k_proj.weight"),
            &[n_kv_heads * head_dim, hidden],
        ),
        v_proj: load_f32_tensor(
            &p("self_attn.v_proj.weight"),
            &[n_kv_heads * head_dim, hidden],
        ),
        o_proj: load_f32_tensor(&p("self_attn.o_proj.weight"), &[hidden, hidden]),
        gate_proj: load_f32_tensor(&p("mlp.gate_proj.weight"), &[inter, hidden]),
        up_proj: load_f32_tensor(&p("mlp.up_proj.weight"), &[inter, hidden]),
        down_proj: load_f32_tensor(&p("mlp.down_proj.weight"), &[hidden, inter]),
        q_bias: load_bias_opt(&p("self_attn.q_proj.bias"), hidden),
        k_bias: load_bias_opt(&p("self_attn.k_proj.bias"), n_kv_heads * head_dim),
        v_bias: load_bias_opt(&p("self_attn.v_proj.bias"), n_kv_heads * head_dim),
    }
}

/// LLM-8b: a layer's weights for one `forward_token` iteration, either
/// borrowed from `Model.layers` (eager mode) or freshly loaded from disk
/// and owned for the duration of the loop body (`--stream-weights` mode,
/// dropped when this value goes out of scope at the end of the layer's
/// iteration).
enum LayerHandle<'a> {
    Borrowed(&'a LayerWeights),
    Owned(LayerWeights),
}

impl<'a> std::ops::Deref for LayerHandle<'a> {
    type Target = LayerWeights;
    fn deref(&self) -> &LayerWeights {
        match self {
            LayerHandle::Borrowed(r) => r,
            LayerHandle::Owned(o) => o,
        }
    }
}

fn get_layer(model: &Model, li: usize) -> LayerHandle<'_> {
    match &model.stream {
        None => LayerHandle::Borrowed(&model.layers[li]),
        Some(s) => LayerHandle::Owned(load_layer_weights(
            &s.weights_file,
            s.data_start,
            &s.tensor_index,
            li,
            model.hidden,
            model.inter,
            model.n_kv_heads,
            model.head_dim,
        )),
    }
}

fn matvec(
    w: &[f32],
    x: &[f32],
    out_features: usize,
    in_features: usize,
    reduction: Reduction,
) -> Vec<f32> {
    debug_assert_eq!(w.len(), out_features * in_features);
    debug_assert_eq!(x.len(), in_features);
    let mut y = vec![0.0f32; out_features];
    for o in 0..out_features {
        let row = &w[o * in_features..(o + 1) * in_features];
        y[o] = dot(row, x, reduction);
    }
    y
}

fn rmsnorm(x: &[f32], weight: &[f32], eps: f32, reduction: Reduction) -> Vec<f32> {
    let n = x.len();
    let mut sq = vec![0.0f32; n];
    for i in 0..n {
        sq[i] = x[i] * x[i];
    }
    let ss = sum(&sq, reduction);
    let mean = ss / (n as f32);
    let inv = rsqrt_cr(mean + eps);
    let mut out = vec![0.0f32; n];
    for i in 0..n {
        let scaled = x[i] * inv;
        out[i] = scaled * weight[i];
    }
    out
}

/// E15d(c) — add an optional per-output-feature bias vector in place
/// (strict left-to-right elementwise add, §3.1), a no-op if `bias` is None
/// (Llama-family checkpoints with no QKV bias tensors).
fn add_bias_opt(x: &mut [f32], bias: &Option<Vec<f32>>) {
    if let Some(b) = bias {
        debug_assert_eq!(x.len(), b.len());
        for i in 0..x.len() {
            x[i] = x[i] + b[i];
        }
    }
}

fn elementwise_add(a: &[f32], b: &[f32]) -> Vec<f32> {
    let mut out = vec![0.0f32; a.len()];
    for i in 0..a.len() {
        out[i] = a[i] + b[i];
    }
    out
}

/// RoPE rotate-half convention (rope_interleaved=false, matching config),
/// applied in place to one head's 64-dim slice, using CIS-2 §3.3(b) pinned
/// sin/cos.
fn apply_rope_head(head: &mut [f32], pos: usize, inv_freq: &[f32]) {
    let half = head.len() / 2;
    let mut cos_v = vec![0.0f32; half];
    let mut sin_v = vec![0.0f32; half];
    for i in 0..half {
        let angle = (pos as f32) * inv_freq[i];
        cos_v[i] = math::cos_pinned(angle);
        sin_v[i] = math::sin_pinned(angle);
    }
    let mut out = vec![0.0f32; head.len()];
    for i in 0..half {
        let x1 = head[i];
        let x2 = head[i + half];
        // rotate_half(x) = [-x2, x1]; out = x*cos + rotate_half(x)*sin
        let t1 = x1 * cos_v[i];
        let t2 = (-x2) * sin_v[i];
        out[i] = t1 + t2;
        let t3 = x2 * cos_v[i];
        let t4 = x1 * sin_v[i];
        out[i + half] = t3 + t4;
    }
    head.copy_from_slice(&out);
}

struct KvCache {
    k: Vec<Vec<f32>>, // per position, len n_kv_heads*head_dim
    v: Vec<Vec<f32>>,
}

/// E15k debug-only helper: SHA-256 over the raw LE f32 bit patterns of a
/// slice. Used only by the `CIS2_DUMP_LAYERS`/`dump_pos` side-channel below
/// to localize a cross-language divergence; not part of any normative
/// digest and not read by default (env var gated).
fn hash_f32_slice(xs: &[f32]) -> [u8; 32] {
    let mut h = Sha256::new();
    for &v in xs {
        h.update(v.to_bits().to_le_bytes());
    }
    h.finalize().into()
}

/// E15k debug-only: print one `CIS2_DUMP` line to stderr in a format the
/// C clean-room's matching dump mode also produces, so the two can be
/// diffed line-for-line. Not part of CIS2_REF; gated on `dump_pos`.
fn dump_line(layer: &str, field: &str, pos: usize, xs: &[f32]) {
    let d = hash_f32_slice(xs);
    eprintln!(
        "CIS2_DUMP layer={layer} field={field} pos={pos} digest={}",
        hex::encode(d)
    );
}

/// E18b: one `--trace` line — SHA-256 over the raw LE f32 bit patterns of
/// one op's output. `layer` is the layer index, or -1 for the whole-model
/// ops. The CUDA-portable C++ port emits byte-identical lines; see
/// gpu/README.md §5. Not part of CIS2_REF.
fn trace_line(t: &mut Option<&mut std::fs::File>, pos: usize, layer: i64, op: &str, xs: &[f32]) {
    if let Some(f) = t.as_mut() {
        use std::io::Write;
        let d = hash_f32_slice(xs);
        writeln!(
            f,
            "pos={pos} layer={layer} op={op} sha256={}",
            hex::encode(d)
        )
        .expect("write --trace line");
    }
}

#[allow(clippy::too_many_arguments)]
fn forward_token(
    model: &Model,
    caches: &mut [KvCache],
    pos: usize,
    token_id: u32,
    dump_positions: &[usize],
    layer_digest_positions: &[usize],
    trace: &mut Option<&mut std::fs::File>,
    reduction: Reduction,
) -> Vec<f32> {
    let dump = dump_positions.contains(&pos);
    let want_layer_digest = layer_digest_positions.contains(&pos);
    let hidden = model.hidden;
    let head_dim = model.head_dim;
    let n_heads = model.n_heads;
    let n_kv_heads = model.n_kv_heads;
    let group = n_heads / n_kv_heads;
    let scale = rsqrt_cr(head_dim as f32);

    let mut h: Vec<f32> = {
        let start = token_id as usize * hidden;
        model.embed_tokens[start..start + hidden].to_vec()
    };
    if dump {
        dump_line("embed", "token_embedding", pos, &h);
    }
    trace_line(trace, pos, -1, "embedding", &h);
    if want_layer_digest {
        println!("LAYER_DIGEST embed {}", hex::encode(hash_f32_slice(&h)));
    }

    let tracing = trace.is_some();
    for li in 0..model.n_layers {
        let layer_handle = get_layer(model, li);
        let layer: &LayerWeights = &layer_handle;
        let lid = li as i64;
        let ln1 = rmsnorm(&h, &layer.input_layernorm, model.eps, reduction);
        trace_line(trace, pos, lid, "norm1", &ln1);
        let mut q = matvec(&layer.q_proj, &ln1, hidden, hidden, reduction);
        add_bias_opt(&mut q, &layer.q_bias);
        trace_line(trace, pos, lid, "q", &q);
        let mut k = matvec(
            &layer.k_proj,
            &ln1,
            n_kv_heads * head_dim,
            hidden,
            reduction,
        );
        add_bias_opt(&mut k, &layer.k_bias);
        trace_line(trace, pos, lid, "k", &k);
        let mut v = matvec(
            &layer.v_proj,
            &ln1,
            n_kv_heads * head_dim,
            hidden,
            reduction,
        );
        add_bias_opt(&mut v, &layer.v_bias);
        trace_line(trace, pos, lid, "v", &v);

        for qh in 0..n_heads {
            let s = qh * head_dim;
            apply_rope_head(&mut q[s..s + head_dim], pos, &model.inv_freq);
        }
        trace_line(trace, pos, lid, "rope_q", &q);
        for kh in 0..n_kv_heads {
            let s = kh * head_dim;
            apply_rope_head(&mut k[s..s + head_dim], pos, &model.inv_freq);
        }
        trace_line(trace, pos, lid, "rope_k", &k);

        caches[li].k.push(k);
        caches[li].v.push(v);

        // E18b --trace: the `scores`/`softmax` lines hash the concatenation
        // over query heads, in head order, of each head's pos+1 values.
        let mut trace_scores: Vec<f32> = Vec::new();
        let mut trace_softmax: Vec<f32> = Vec::new();

        let mut attn_out = vec![0.0f32; hidden];
        for qh in 0..n_heads {
            let kv_head = qh / group;
            let qs = qh * head_dim;
            let q_head = &q[qs..qs + head_dim];

            let mut scores = vec![0.0f32; pos + 1];
            for j in 0..=pos {
                let kj = &caches[li].k[j][kv_head * head_dim..kv_head * head_dim + head_dim];
                let d = dot(q_head, kj, reduction);
                scores[j] = d * scale;
            }
            if tracing {
                trace_scores.extend_from_slice(&scores);
            }
            softmax(&mut scores, reduction);
            if tracing {
                trace_softmax.extend_from_slice(&scores);
            }

            let mut out_head = vec![0.0f32; head_dim];
            for d in 0..head_dim {
                let mut acc = 0.0f32;
                for j in 0..=pos {
                    let vj = caches[li].v[j][kv_head * head_dim + d];
                    let p = scores[j] * vj;
                    acc = acc + p;
                }
                out_head[d] = acc;
            }
            attn_out[qs..qs + head_dim].copy_from_slice(&out_head);
        }
        trace_line(trace, pos, lid, "scores", &trace_scores);
        trace_line(trace, pos, lid, "softmax", &trace_softmax);
        trace_line(trace, pos, lid, "attn_out", &attn_out);

        let o = matvec(&layer.o_proj, &attn_out, hidden, hidden, reduction);
        trace_line(trace, pos, lid, "o_proj", &o);
        h = elementwise_add(&h, &o);
        trace_line(trace, pos, lid, "resid1", &h);
        if dump {
            dump_line(&format!("block{li}"), "post_attention_hidden", pos, &h);
        }

        let ln2 = rmsnorm(&h, &layer.post_attention_layernorm, model.eps, reduction);
        trace_line(trace, pos, lid, "norm2", &ln2);
        let gate = matvec(&layer.gate_proj, &ln2, model.inter, hidden, reduction);
        trace_line(trace, pos, lid, "gate", &gate);
        let up = matvec(&layer.up_proj, &ln2, model.inter, hidden, reduction);
        trace_line(trace, pos, lid, "up", &up);
        let mut hid = vec![0.0f32; model.inter];
        for i in 0..model.inter {
            hid[i] = silu_pinned(gate[i]) * up[i];
        }
        trace_line(trace, pos, lid, "silu_mul", &hid);
        let down = matvec(&layer.down_proj, &hid, hidden, model.inter, reduction);
        trace_line(trace, pos, lid, "down", &down);
        h = elementwise_add(&h, &down);
        trace_line(trace, pos, lid, "resid2", &h);
        if dump {
            dump_line(&format!("block{li}"), "post_mlp_hidden", pos, &h);
        }
        if want_layer_digest {
            println!(
                "LAYER_DIGEST block_{li} {}",
                hex::encode(hash_f32_slice(&h))
            );
        }
    }

    let hn = rmsnorm(&h, &model.final_norm, model.eps, reduction);
    trace_line(trace, pos, -1, "final_norm", &hn);
    if dump {
        dump_line("final_norm", "final_norm_output", pos, &hn);
    }
    if want_layer_digest {
        println!(
            "LAYER_DIGEST final_norm {}",
            hex::encode(hash_f32_slice(&hn))
        );
    }
    // LM head: tied to embed_tokens when the checkpoint has no separate
    // lm_head.weight tensor (SmolLM2-135M; confirmed by header inspection,
    // see docs/E15b_REFERENCE_RESULT.md), otherwise the untied tensor
    // loaded into model.lm_head (E15d(c) generalization).
    let lm_head_weights = model.lm_head.as_ref().unwrap_or(&model.embed_tokens);
    let logits = matvec(lm_head_weights, &hn, model.vocab, hidden, reduction);
    trace_line(trace, pos, -1, "logits", &logits);
    if dump {
        dump_line("logits", "pre_argmax_logits", pos, &logits);
    }
    if want_layer_digest {
        println!("LAYER_DIGEST logits {}", hex::encode(hash_f32_slice(&logits)));
    }
    logits
}

/// Config-only architecture gate. Returns Err(named reason) for any checkpoint
/// outside the subset CIS-2 actually specifies.
///
/// Rationale: the decode path implements ONE architecture family (Llama-shaped,
/// full rotary, dense MLP, no attention multipliers, no logit softcapping).
/// Most unsupported checkpoints fail loudly on a shape or missing-tensor
/// assert, but a residual class -- scalar multipliers whose shapes all match,
/// e.g. IBM Granite's `attention_multiplier` against the hardcoded
/// rsqrt(head_dim) -- passes every assert and emits a confident WRONG digest.
/// A verifier that emits a plausible wrong digest is worse than no verifier,
/// so scope is enforced here, by name, and no digest is printed on refusal.
///
/// This runs on config.json alone: no weights file is opened or hashed, so a
/// refusal fixture needs only the config.
fn gate_architecture(config: &serde_json::Value) -> Result<(), String> {
    const SUPPORTED_MODEL_TYPES: &[&str] = &["llama", "qwen2"];

    if let Some(mt) = config["model_type"].as_str() {
        if !SUPPORTED_MODEL_TYPES.contains(&mt) {
            return Err(format!(
                "model_type={mt:?} is not in the CIS-2 specified subset {SUPPORTED_MODEL_TYPES:?}"
            ));
        }
    }

    if let Some(dt) = config["torch_dtype"].as_str() {
        if dt != "bfloat16" {
            return Err(format!(
                "torch_dtype={dt:?}; CIS-2 pins bf16-on-disk weights (\u{00a7}3.5)"
            ));
        }
    }

    // head_dim must be the derived value: the decode path computes
    // hidden/n_heads and ignores any explicit key (Qwen3 declares 128 against
    // a derived 64).
    let hidden = config["hidden_size"].as_u64();
    let n_heads = config["num_attention_heads"].as_u64();
    if let (Some(h), Some(nh)) = (hidden, n_heads) {
        if nh == 0 {
            return Err("num_attention_heads=0".to_string());
        }
        let derived = h / nh;
        if let Some(explicit) = config["head_dim"].as_u64() {
            if explicit != derived {
                return Err(format!(
                    "config declares head_dim={explicit} but this implementation derives \
                     hidden_size/num_attention_heads={derived}; the decode path uses the \
                     derived value, so the explicit one would be silently ignored"
                ));
            }
        }
        if derived % 2 != 0 {
            return Err(format!(
                "derived head_dim={derived} is odd; RoPE pairs require even"
            ));
        }
    }

    if let Some(prf) = config["partial_rotary_factor"].as_f64() {
        if prf != 1.0 {
            return Err(format!(
                "partial_rotary_factor={prf}; only full rotary is specified"
            ));
        }
    }

    if !config["rope_scaling"].is_null() {
        return Err("rope_scaling is set; only unscaled RoPE is specified".to_string());
    }

    if config["use_sliding_window"].as_bool() == Some(true) {
        return Err("use_sliding_window=true; only full causal attention is specified".to_string());
    }

    if !config["quantization_config"].is_null() {
        return Err(
            "quantization_config is present; CIS-2 reads unquantized bf16 weights".to_string(),
        );
    }

    // Scalar multipliers: the silent-wrong-digest class. Shapes all match, so
    // no assert fires, but the arithmetic is wrong.
    for key in [
        "attention_multiplier",
        "embedding_multiplier",
        "residual_multiplier",
        "logits_scaling",
        "attn_logit_softcapping",
        "final_logit_softcapping",
        "query_pre_attn_scalar",
    ] {
        if !config[key].is_null() {
            return Err(format!(
                "{key} is set; this implementation hardcodes rsqrt(head_dim) attention \
                 scaling and no logit scaling, so the result would be silently wrong"
            ));
        }
    }

    // Mixture-of-experts routing is not implemented.
    for key in [
        "num_local_experts",
        "num_experts",
        "n_routed_experts",
        "moe_intermediate_size",
    ] {
        if !config[key].is_null() {
            return Err(format!("{key} is set; MoE routing is not specified"));
        }
    }

    Ok(())
}

// LLM-5b: the whole-buffer loader that used to live here (require the
// entire safetensors file already read into one `Vec<u8>`, plus a
// `safetensors::SafeTensors` view over it, both held alive for the whole
// load loop) has moved to `whole_buffer_widen::load_f32_tensor_whole_buffer`
// — kept only as a reference implementation for tests and the `mem_probe`
// memory-comparison binary. The production path below now streams each
// tensor's raw bytes directly off disk via `stream_widen`, never holding
// more than one tensor's raw bf16 bytes at a time (see
// docs/LLM5b_STREAMING_WIDEN.md for the diagnosis and fix).

/// §2.1 artifact digest — returns the raw 32-byte SHA-256 digest (CIS-2 v0.2
/// §12.1 pins that the witness header is fed these raw bytes, not the
/// 64-char hex-ASCII rendering; hex is used only for display/printing, via
/// `hex::encode` at the call site).
fn sha256_file(path: &Path) -> [u8; 32] {
    use std::io::Read;
    let file = std::fs::File::open(path).unwrap_or_else(|e| panic!("open {path:?}: {e}"));
    let mut reader = std::io::BufReader::new(file);
    let mut h = Sha256::new();
    // 8 MiB chunks: bounded memory regardless of file size, byte-identical
    // digest to a whole-file `Sha256::update` since SHA-256 is a streaming
    // Merkle-Damgard hash (feeding it in pieces is equivalent to feeding it
    // all at once).
    let mut buf = vec![0u8; 8 * 1024 * 1024];
    loop {
        let n = reader
            .read(&mut buf)
            .unwrap_or_else(|e| panic!("read {path:?}: {e}"));
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    h.finalize().into()
}

// tiny hex encoder (avoid pulling in the `hex` crate for one call site)
mod hex {
    pub fn encode(bytes: impl AsRef<[u8]>) -> String {
        let mut s = String::new();
        for b in bytes.as_ref() {
            s.push_str(&format!("{:02x}", b));
        }
        s
    }
}

/// E15d(b) — CLI options. Defaults reproduce E15c's invocation exactly
/// (single hardcoded prompt "Once upon a time", gen_toks=16, weights/).
struct Args {
    gen_toks: usize,
    prompt_set: Option<std::path::PathBuf>,
    weights_dir: String,
    /// E18b: write prompt 0's tokenizer output (one decimal u32 per line)
    /// to this file, so the CUDA-portable C++ port in `gpu/` consumes the
    /// reference tokenization instead of re-implementing it. Non-normative
    /// side output; does not touch the decode path or CIS2_REF.
    dump_ids: Option<std::path::PathBuf>,
    /// E18b: write the per-(position, layer, op) SHA-256 trace described in
    /// gpu/README.md §5 to this file, for prompt 0's first run only. The
    /// CUDA-portable C++ port emits the identical format, so a divergence
    /// is located by one `diff` instead of a bisect. Non-normative side
    /// output; the decode path and CIS2_REF are unaffected.
    trace: Option<std::path::PathBuf>,
    /// v0.4 CANDIDATE (E18c): `--reduction sequential|tree`, default
    /// `sequential`. Default reproduces every prior invocation's digest
    /// byte-for-byte (see `Reduction` doc comment above).
    reduction: Reduction,
    /// LLM-8b: opt-in. When set, layer weights are streamed one layer at a
    /// time (see `StreamCtx`/`load_layer_weights`/`get_layer`) instead of
    /// all being preloaded into `Model.layers` before the forward pass
    /// starts. Same arithmetic, same digest; only load-time/forward-pass
    /// memory residency changes. Default `false` reproduces every prior
    /// invocation's behavior exactly.
    stream_weights: bool,
    /// H3 instrumentation (cis3-1b): when set, prints one `LAYER_DIGEST
    /// <label> <hex>` line to stdout per forward pass — after the embedding
    /// lookup, after each transformer block, after the final norm, and of
    /// the final logits — for run1/prompt 0's last prefill position only
    /// (one full forward pass through every layer). Purely additive: does
    /// not alter the witness/argmax digests or any existing output line.
    /// Added to root-cause a real fp32 forward-pass divergence between a
    /// Kaggle Qwen2-7B run and a box1 CPU streamed run of the same weights
    /// (see docs/LLM8b_STREAM_WEIGHTS.md); localizes the first diverging
    /// layer instead of only the final witness digest.
    layer_digests: bool,
}

fn parse_args() -> Args {
    let argv: Vec<String> = std::env::args().collect();
    let mut gen_toks = 16usize;
    let mut prompt_set = None;
    let mut weights_dir = "weights".to_string();
    let mut dump_ids = None;
    let mut trace = None;
    let mut reduction = Reduction::Sequential;
    let mut stream_weights = false;
    let mut layer_digests = false;
    let mut i = 1;
    while i < argv.len() {
        match argv[i].as_str() {
            "--stream-weights" => {
                stream_weights = true;
            }
            "--layer-digests" => {
                layer_digests = true;
            }
            "--dump-ids" => {
                i += 1;
                dump_ids = Some(std::path::PathBuf::from(&argv[i]));
            }
            "--trace" => {
                i += 1;
                trace = Some(std::path::PathBuf::from(&argv[i]));
            }
            "--gen-toks" => {
                i += 1;
                gen_toks = argv[i]
                    .parse()
                    .unwrap_or_else(|e| panic!("--gen-toks: invalid integer {:?}: {e}", argv[i]));
            }
            "--prompt-set" => {
                i += 1;
                prompt_set = Some(std::path::PathBuf::from(&argv[i]));
            }
            "--weights-dir" => {
                i += 1;
                weights_dir = argv[i].clone();
            }
            "--reduction" => {
                i += 1;
                reduction = match argv[i].as_str() {
                    "sequential" => Reduction::Sequential,
                    "tree" => Reduction::Tree,
                    other => panic!("--reduction: expected 'sequential' or 'tree', got {other:?}"),
                };
            }
            other => panic!("unknown CLI argument: {other}"),
        }
        i += 1;
    }
    Args {
        gen_toks,
        prompt_set,
        weights_dir,
        dump_ids,
        trace,
        reduction,
        stream_weights,
        layer_digests,
    }
}

fn main() {
    denormal::pin_ftz_daz();
    assert!(
        denormal::ftz_daz_on(),
        "FTZ/DAZ (or FPCR.FZ on aarch64) must be pinned before any decode-path fp32 arithmetic (§3.4)"
    );

    let args = parse_args();

    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join(&args.weights_dir);
    let weights_path = root.join("model.safetensors");
    let tokenizer_path = root.join("tokenizer.json");
    let config_path = root.join("config.json");

    // Parse and GATE the config before touching the weights file. The gate is
    // config-only, so an unsupported checkpoint is refused by name without its
    // weights being present or hashed. Hashing first would panic inside
    // sha256_file on a missing model.safetensors before the gate could run.
    let config: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&config_path).unwrap()).unwrap();
    if let Err(reason) = gate_architecture(&config) {
        eprintln!("CIS2_REF_UNSUPPORTED reason={reason}");
        eprintln!("This checkpoint is outside the CIS-2 specified subset; no digest emitted.");
        std::process::exit(2);
    }

    let weights_sha256 = sha256_file(&weights_path);
    let tokenizer_sha256 = sha256_file(&tokenizer_path);
    let config_sha256 = sha256_file(&config_path);
    let hidden = config["hidden_size"].as_u64().unwrap() as usize;
    let inter = config["intermediate_size"].as_u64().unwrap() as usize;
    let n_layers = config["num_hidden_layers"].as_u64().unwrap() as usize;
    let n_heads = config["num_attention_heads"].as_u64().unwrap() as usize;
    let n_kv_heads = config["num_key_value_heads"].as_u64().unwrap() as usize;
    let vocab = config["vocab_size"].as_u64().unwrap() as usize;
    let eps = config["rms_norm_eps"].as_f64().unwrap() as f32;
    let rope_theta = config["rope_theta"].as_f64().unwrap();
    let head_dim = hidden / n_heads;

    // §3.3(b)-pinned RoPE inv_freq (normative, per spec-change on top of
    // milestone 1): inv_freq[i] = exp_pinned( -(2*i/d) * ln_pinned(theta) ),
    // using ONLY the route-(b) pinned polynomials already in src/math.rs —
    // NOT host f64::powf, NOT std ln/exp. E15d(c) generalizes this from a
    // hardcoded literal (pinned for exactly rope_theta=1e5, SmolLM2) to a
    // config-driven `ln_pinned(rope_theta)` call, since Qwen2.5-0.5B uses
    // rope_theta=1e6, not 1e5. This is the SAME math for SmolLM2 (theta is
    // still read from config.json; `math::tests::ln_matches_std_within_tolerance`
    // checks ln_pinned(100_000.0) and ln_pinned(1_000_000.0) both agree with
    // host ln to the same 2e-6 relative tolerance used elsewhere in this
    // module), just no longer restricted to one hardcoded value.
    let ln_theta = math::ln_pinned(rope_theta as f32);
    let mut inv_freq = vec![0.0f32; head_dim / 2];
    for i in 0..head_dim / 2 {
        let frac = (2 * i) as f32 / (head_dim as f32);
        let neg_arg = {
            let a = frac * ln_theta;
            -a
        };
        inv_freq[i] = exp_pinned(neg_arg);
    }
    // §7.2 (v0.2) — raw 32-byte digest, folded into the witness header below
    // (v0.1 computed and printed this but never bound it into CIS2_REF;
    // v0.2 §12.1 closes that gap, see docs/CIS2_SPEC_v0.2.md changelog).
    let inv_freq_table_digest: [u8; 32] = {
        use sha2::{Digest, Sha256};
        let mut h = Sha256::new();
        for &v in &inv_freq {
            h.update(v.to_le_bytes());
        }
        h.finalize().into()
    };

    // LLM-5b: streaming load. Only the safetensors header (name -> dtype /
    // shape / byte-range index) is parsed up front; no tensor's data bytes
    // are read here. `weights_file` is wrapped in a `RefCell` so the
    // `load_f32_tensor`/`load_bias_opt` closures below can share one file
    // handle without overlapping borrows (each borrow is released at the
    // end of the streaming call that needs it, before the next tensor is
    // requested) -- never more than one tensor's raw bf16 bytes resident
    // at a time (see stream_widen.rs and docs/LLM5b_STREAMING_WIDEN.md).
    let weights_file = std::cell::RefCell::new(
        std::fs::File::open(&weights_path).expect("open model.safetensors"),
    );
    let (tensor_index, data_start) = stream_widen::read_index(&mut *weights_file.borrow_mut());

    eprintln!("loading + widening weights (bf16 -> fp32, exact bit-shift, §3.5)...");
    let load_f32_tensor = |name: &str, expect_shape: &[usize]| -> Vec<f32> {
        stream_widen::load_tensor_streaming(
            &mut *weights_file.borrow_mut(),
            data_start,
            &tensor_index,
            name,
            expect_shape,
        )
    };
    let embed_tokens = load_f32_tensor("model.embed_tokens.weight", &[vocab, hidden]);

    // E15d(c): optional bias load helper -- returns Some(vec) if the tensor
    // exists in the checkpoint (Qwen2-family attention_bias=true), None if
    // absent (Llama-family SmolLM2, which has no QKV bias tensors at all).
    let load_bias_opt = |name: &str, len: usize| -> Option<Vec<f32>> {
        if tensor_index.contains_key(name) {
            Some(load_f32_tensor(name, &[len]))
        } else {
            None
        }
    };

    // LLM-8b: `--stream-weights` skips this eager per-layer preload
    // entirely (each layer is loaded lazily inside forward_token instead,
    // via the identical `load_layer_weights` tensor sequence); with no
    // flag, behavior is byte-for-byte unchanged from before this change.
    let mut layers = Vec::new();
    if !args.stream_weights {
        layers.reserve(n_layers);
        for i in 0..n_layers {
            layers.push(load_layer_weights(
                &weights_file,
                data_start,
                &tensor_index,
                i,
                hidden,
                inter,
                n_kv_heads,
                head_dim,
            ));
        }
    }
    let final_norm = load_f32_tensor("model.norm.weight", &[hidden]);
    // E15d(c): untied LM head, if the checkpoint carries a separate
    // lm_head.weight tensor (config tie_word_embeddings=false).
    let tie_word_embeddings = config
        .get("tie_word_embeddings")
        .and_then(|v| v.as_bool())
        .unwrap_or(true);
    let lm_head = if tie_word_embeddings {
        None
    } else {
        Some(load_f32_tensor("lm_head.weight", &[vocab, hidden]))
    };
    let _ = load_f32_tensor;
    let _ = load_bias_opt;
    // LLM-8b: eager mode has finished reading every tensor it needs, so
    // the file handle is dropped exactly as before. Streaming mode keeps
    // it open (moved into `Model.stream`) for per-layer reads during the
    // forward pass.
    let stream = if args.stream_weights {
        Some(StreamCtx {
            weights_file,
            tensor_index,
            data_start,
        })
    } else {
        drop(weights_file);
        None
    };
    eprintln!("weights loaded.");

    let model = Model {
        embed_tokens,
        layers,
        final_norm,
        hidden,
        inter,
        n_layers,
        n_heads,
        n_kv_heads,
        head_dim,
        vocab,
        eps,
        inv_freq,
        lm_head,
        stream,
    };

    let tok = tokenizers::Tokenizer::from_file(&tokenizer_path)
        .unwrap_or_else(|e| panic!("load tokenizer: {e}"));

    // E15d(b): --prompt-set FILE loads a JSON array of prompt strings
    // (checked into the repo, see prompts/e15d_prompt_set.json); with no
    // --prompt-set flag, behavior is byte-for-byte unchanged from E15c
    // (single hardcoded prompt "Once upon a time").
    let prompts: Vec<String> = match &args.prompt_set {
        Some(path) => {
            let text = std::fs::read_to_string(path)
                .unwrap_or_else(|e| panic!("read --prompt-set {path:?}: {e}"));
            serde_json::from_str(&text).unwrap_or_else(|e| {
                panic!("--prompt-set {path:?} must be a JSON array of strings: {e}")
            })
        }
        None => vec!["Once upon a time".to_string()],
    };
    let gen_toks = args.gen_toks;

    for (prompt_idx, prompt) in prompts.iter().enumerate() {
        run_one_prompt(
            &model,
            &tok,
            prompt,
            prompt_idx,
            gen_toks,
            weights_sha256,
            tokenizer_sha256,
            config_sha256,
            inv_freq_table_digest,
            if prompt_idx == 0 {
                args.dump_ids.as_deref()
            } else {
                None
            },
            if prompt_idx == 0 {
                args.trace.as_deref()
            } else {
                None
            },
            args.reduction,
            args.layer_digests,
        );
    }
}

/// Runs the full deterministic-twice-run reference pass for one prompt and
/// prints its CIS2_REF block. Factored out of `main()` in E15d(b) so the
/// same logic drives both the legacy single-prompt path and the new
/// `--prompt-set` multi-prompt path identically.
#[allow(clippy::too_many_arguments)]
fn run_one_prompt(
    model: &Model,
    tok: &tokenizers::Tokenizer,
    prompt: &str,
    prompt_idx: usize,
    gen_toks: usize,
    weights_sha256: [u8; 32],
    tokenizer_sha256: [u8; 32],
    config_sha256: [u8; 32],
    inv_freq_table_digest: [u8; 32],
    dump_ids: Option<&Path>,
    trace_path: Option<&Path>,
    reduction: Reduction,
    layer_digests: bool,
) {
    let enc = tok.encode(prompt, false).expect("tokenize prompt");
    let prompt_ids: Vec<u32> = enc.get_ids().to_vec();
    eprintln!(
        "[prompt {prompt_idx}] token ids ({} toks): {prompt_ids:?}",
        prompt_ids.len()
    );

    // E18b (non-normative): hand the reference tokenization to the C++ port.
    if let Some(path) = dump_ids {
        let mut text = String::new();
        for &t in &prompt_ids {
            text.push_str(&format!("{t}\n"));
        }
        std::fs::write(path, &text).unwrap_or_else(|e| panic!("write --dump-ids {path:?}: {e}"));
        eprintln!(
            "[prompt {prompt_idx}] wrote {} token ids to {path:?}",
            prompt_ids.len()
        );
    }

    let run = |label: &str| {
        // E18b --trace: prompt 0's first run only (run2 is a determinism
        // re-run of identical arithmetic, so its trace would be identical
        // and only doubles the file).
        let mut trace_file: Option<std::fs::File> = if label == "run1" && prompt_idx == 0 {
            trace_path.map(|p| {
                std::fs::File::create(p).unwrap_or_else(|e| panic!("create --trace {p:?}: {e}"))
            })
        } else {
            None
        };
        let mut caches: Vec<KvCache> = (0..model.n_layers)
            .map(|_| KvCache {
                k: Vec::new(),
                v: Vec::new(),
            })
            .collect();

        // CIS-2 v0.2 §12.1 witness header: raw 32-byte digests (not the
        // 64-char hex-ASCII rendering, v0.1's §14.2 gap — v0.2 closes it),
        // now ALSO binding table_digest and inv_freq_table_digest (v0.1's
        // §14.3 gap: those two digests were computed and printed but never
        // fed into CIS2_REF, so a receipt holder could not detect a
        // different transcendental table producing the same logits).
        let mut witness = Sha256::new();
        witness.update(weights_sha256);
        witness.update(tokenizer_sha256);
        witness.update(config_sha256);
        witness.update(math::table_digest());
        witness.update(inv_freq_table_digest);
        for &t in &prompt_ids {
            witness.update(t.to_le_bytes());
        }

        let mut all_token_ids: Vec<u32> = prompt_ids.clone();
        let mut logits: Vec<f32> = Vec::new();

        // E15k debug-only: per-layer state dump for the forward pass that
        // produces step 0's logits (the last prefill position), gated on
        // env var CIS2_DUMP_LAYERS (any value) and only on run1/prompt 0
        // to avoid duplicate/noisy output. Not part of CIS2_REF.
        // E15k: dump both the forward pass that produces step 0's logits
        // (pos = prompt_ids.len()-1) and the one that produces step 1's
        // logits (pos = prompt_ids.len()) -- step 0 alone was found to
        // match bit-for-bit against verify3/, so step 1 is needed to
        // localize the actual divergence.
        let dump_positions: Vec<usize> =
            if label == "run1" && prompt_idx == 0 && std::env::var("CIS2_DUMP_LAYERS").is_ok() {
                vec![prompt_ids.len() - 1, prompt_ids.len()]
            } else {
                Vec::new()
            };

        // H3 (cis3-1b): --layer-digests positions, mirroring dump_positions
        // above but printed to stdout as `LAYER_DIGEST` lines rather than
        // stderr `CIS2_DUMP` lines, and gated on the CLI flag rather than an
        // env var. Only the last prefill position of run1/prompt 0 emits, so
        // a single full forward pass (embed -> every block -> final_norm ->
        // logits) is captured once per invocation.
        let layer_digest_positions: Vec<usize> =
            if label == "run1" && prompt_idx == 0 && layer_digests {
                vec![prompt_ids.len() - 1]
            } else {
                Vec::new()
            };

        // Prefill: run every prompt position to populate the KV cache.
        for (pos, &tid) in prompt_ids.iter().enumerate() {
            logits = forward_token(
                model,
                &mut caches,
                pos,
                tid,
                &dump_positions,
                &layer_digest_positions,
                &mut trace_file.as_mut(),
                reduction,
            );
        }

        // Debug-only (m1.5 correctness check): dump the step-0 full fp32
        // logit vector (raw LE bytes) to a file if requested via env var.
        // Not part of the CIS2_REF normative output; used only to diff
        // against an external oracle. Only on the first labeled run to
        // avoid overwriting with run2 (both runs are identical anyway).
        if label == "run1" && prompt_idx == 0 {
            if let Ok(path) = std::env::var("CIS2_DUMP_STEP0_LOGITS") {
                let mut bytes = Vec::with_capacity(logits.len() * 4);
                for &v in &logits {
                    bytes.extend_from_slice(&v.to_le_bytes());
                }
                std::fs::write(&path, &bytes).unwrap_or_else(|e| panic!("write {path}: {e}"));
                eprintln!(
                    "[debug] wrote step-0 logits ({} f32 values) to {path}",
                    logits.len()
                );
            }
        }

        for step in 0..gen_toks {
            // logits currently correspond to the last processed position.
            let mut best_idx = 0usize;
            let mut best_val = logits[0];
            for (idx, &v) in logits.iter().enumerate() {
                if v > best_val {
                    best_val = v;
                    best_idx = idx;
                }
            }
            let next_id = best_idx as u32;

            // Bind this step's full fp32 logit vector into the witness
            // chain (bit pattern, LE, mirroring CIS-1's per-step chain but
            // over fp32 bits instead of exact integers).
            let mut step_bytes = Vec::with_capacity(logits.len() * 4);
            for &v in &logits {
                step_bytes.extend_from_slice(&v.to_bits().to_le_bytes());
            }
            witness.update(&step_bytes);
            witness.update(next_id.to_le_bytes());

            all_token_ids.push(next_id);
            let pos = prompt_ids.len() + step;
            logits = forward_token(
                model,
                &mut caches,
                pos,
                next_id,
                &dump_positions,
                &layer_digest_positions,
                &mut trace_file.as_mut(),
                reduction,
            );
            eprintln!("[{label}] step {step}: token_id={next_id}");
        }

        // Debug-only (H1 512-tok oracle check): dump the FINAL step's
        // full fp32 logit vector, mirroring CIS2_DUMP_STEP0_LOGITS above
        // but at the last generated step instead of step 0. Not part of
        // the CIS2_REF normative output.
        if label == "run1" && prompt_idx == 0 {
            if let Ok(path) = std::env::var("CIS2_DUMP_LASTSTEP_LOGITS") {
                let mut bytes = Vec::with_capacity(logits.len() * 4);
                for &v in &logits {
                    bytes.extend_from_slice(&v.to_le_bytes());
                }
                std::fs::write(&path, &bytes).unwrap_or_else(|e| panic!("write {path}: {e}"));
                eprintln!(
                    "[debug] wrote final-step logits ({} f32 values) to {path}",
                    logits.len()
                );
            }
        }

        let witness_digest = witness.finalize();
        let mut argmax_hasher = Sha256::new();
        for &t in &all_token_ids {
            argmax_hasher.update(t.to_le_bytes());
        }
        let argmax_digest = argmax_hasher.finalize();

        (
            hex::encode(witness_digest),
            hex::encode(argmax_digest),
            all_token_ids,
        )
    };

    let (w1, a1, toks1) = run("run1");
    let (w2, a2, toks2) = run("run2");

    println!("weights_sha256={}", hex::encode(weights_sha256));
    println!("tokenizer_sha256={}", hex::encode(tokenizer_sha256));
    println!("config_sha256={}", hex::encode(config_sha256));
    println!("table_digest={}", hex::encode(math::table_digest()));
    println!(
        "inv_freq_table_digest={}",
        hex::encode(inv_freq_table_digest)
    );
    println!("prompt_idx={prompt_idx} prompt_tokens={prompt_ids:?}");
    println!("prompt_idx={prompt_idx} run1_tokens={toks1:?}");
    println!("prompt_idx={prompt_idx} run2_tokens={toks2:?}");
    println!("prompt_idx={prompt_idx} run1_witness_digest={w1}");
    println!("prompt_idx={prompt_idx} run2_witness_digest={w2}");
    println!("prompt_idx={prompt_idx} run1_argmax_digest={a1}");
    println!("prompt_idx={prompt_idx} run2_argmax_digest={a2}");
    println!(
        "prompt_idx={prompt_idx} runs_identical={}",
        w1 == w2 && a1 == a2 && toks1 == toks2
    );
    // v0.4 CANDIDATE (E18c): reduction_mode is receipt metadata, printed
    // like dtype=fp32 already is — NOT folded into the witness hash above
    // (w1/w2 are computed identically regardless of this line), so this
    // field cannot change any digest, including the sequential-mode ones.
    println!(
        "prompt_idx={prompt_idx} reduction_mode={}",
        reduction.as_str()
    );
    println!(
        "CIS2_REF digest={w1} prompt_idx={prompt_idx} prompt_toks={} gen_toks={gen_toks} dtype=fp32 reduction_mode={}",
        prompt_ids.len(),
        reduction.as_str()
    );
}
