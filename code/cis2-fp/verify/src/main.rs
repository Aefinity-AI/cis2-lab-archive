//! cis2-verify: independent, clean-room CIS-2 fp32 reference implementation
//! for SmolLM2-135M, built strictly from the E14a design memo + E15b/E15c
//! result docs (see CLEANROOM_LOG.md). No cis2-fp src/ or tests/ file was
//! read to build this. Open ambiguities the memo left unresolved, and how
//! this implementation resolved them, are in SPEC_GAPS.md.
//!
//! Rule A: prints no timing numbers.

mod denormal;
mod math;

use safetensors::SafeTensors;
use sha2::{Digest, Sha256};
use std::path::Path;
use tokenizers::Tokenizer;

const PROMPT: &str = "Once upon a time";
const GEN_TOKS: usize = 16;

struct Config {
    hidden_size: usize,
    intermediate_size: usize,
    num_hidden_layers: usize,
    num_attention_heads: usize,
    num_key_value_heads: usize,
    rms_norm_eps: f32,
    rope_theta: f64,
    vocab_size: usize,
}

fn load_config(path: &Path) -> Config {
    let text = std::fs::read_to_string(path).expect("read config.json");
    let v: serde_json::Value = serde_json::from_str(&text).expect("parse config.json");
    Config {
        hidden_size: v["hidden_size"].as_u64().unwrap() as usize,
        intermediate_size: v["intermediate_size"].as_u64().unwrap() as usize,
        num_hidden_layers: v["num_hidden_layers"].as_u64().unwrap() as usize,
        num_attention_heads: v["num_attention_heads"].as_u64().unwrap() as usize,
        num_key_value_heads: v["num_key_value_heads"].as_u64().unwrap() as usize,
        rms_norm_eps: v["rms_norm_eps"].as_f64().unwrap() as f32,
        rope_theta: v["rope_theta"].as_f64().unwrap(),
        vocab_size: v["vocab_size"].as_u64().unwrap() as usize,
    }
}

/// Widen a named bf16 tensor from the safetensors file to a flat Vec<f32>,
/// per §3.5's exact bit-shift rule (math::widen_bf16). Row-major, shape
/// info discarded (caller knows the shape from the config).
fn widen_tensor(st: &SafeTensors, name: &str) -> Vec<f32> {
    let view = st.tensor(name).unwrap_or_else(|_| panic!("missing tensor {name}"));
    assert_eq!(format!("{:?}", view.dtype()), "BF16", "expected BF16 tensor {name}");
    let data = view.data();
    let n = data.len() / 2;
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        let bits = u16::from_le_bytes([data[2 * i], data[2 * i + 1]]);
        out.push(math::widen_bf16(bits));
    }
    out
}

struct Layer {
    input_layernorm: Vec<f32>,
    post_attention_layernorm: Vec<f32>,
    q_proj: Vec<f32>, // [n_heads*head_dim, hidden]
    k_proj: Vec<f32>, // [n_kv_heads*head_dim, hidden]
    v_proj: Vec<f32>,
    o_proj: Vec<f32>, // [hidden, n_heads*head_dim]
    gate_proj: Vec<f32>, // [intermediate, hidden]
    up_proj: Vec<f32>,   // [intermediate, hidden]
    down_proj: Vec<f32>, // [hidden, intermediate]
}

struct Model {
    cfg: Config,
    embed_tokens: Vec<f32>, // [vocab, hidden] -- also used as tied LM head
    layers: Vec<Layer>,
    final_norm: Vec<f32>,
    inv_freq: Vec<f32>,
    inv_freq_table_digest: [u8; 32],
}

/// RoPE inv_freq table per the standard Llama construction
/// (inv_freq[i] = theta^(-2i/head_dim)), computed via host f64::powf.
/// The memo (E15b's open question 4, not committed to specific formula or
/// digest bytes in the E14a memo itself) flags this exact construction as
/// underspecified for cross-implementation agreement -- see SPEC_GAPS.md
/// item 3. This is this implementation's own independent choice.
fn compute_inv_freq(theta: f64, head_dim: usize) -> (Vec<f32>, [u8; 32]) {
    let half = head_dim / 2;
    let mut inv_freq = Vec::with_capacity(half);
    for i in 0..half {
        let exponent = (2 * i) as f64 / head_dim as f64;
        let v = 1.0f64 / theta.powf(exponent);
        inv_freq.push(v as f32);
    }
    let mut hasher = Sha256::new();
    for &f in &inv_freq {
        hasher.update(f.to_bits().to_le_bytes());
    }
    let digest = hasher.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&digest);
    (inv_freq, out)
}

fn load_model(weights_dir: &Path) -> Model {
    let cfg = load_config(&weights_dir.join("config.json"));
    let bytes = std::fs::read(weights_dir.join("model.safetensors")).expect("read safetensors");
    let st = SafeTensors::deserialize(&bytes).expect("parse safetensors");

    let embed_tokens = widen_tensor(&st, "model.embed_tokens.weight");
    let final_norm = widen_tensor(&st, "model.norm.weight");

    let mut layers = Vec::with_capacity(cfg.num_hidden_layers);
    for l in 0..cfg.num_hidden_layers {
        let p = format!("model.layers.{l}");
        layers.push(Layer {
            input_layernorm: widen_tensor(&st, &format!("{p}.input_layernorm.weight")),
            post_attention_layernorm: widen_tensor(
                &st,
                &format!("{p}.post_attention_layernorm.weight"),
            ),
            q_proj: widen_tensor(&st, &format!("{p}.self_attn.q_proj.weight")),
            k_proj: widen_tensor(&st, &format!("{p}.self_attn.k_proj.weight")),
            v_proj: widen_tensor(&st, &format!("{p}.self_attn.v_proj.weight")),
            o_proj: widen_tensor(&st, &format!("{p}.self_attn.o_proj.weight")),
            gate_proj: widen_tensor(&st, &format!("{p}.mlp.gate_proj.weight")),
            up_proj: widen_tensor(&st, &format!("{p}.mlp.up_proj.weight")),
            down_proj: widen_tensor(&st, &format!("{p}.mlp.down_proj.weight")),
        });
    }

    let head_dim = cfg.hidden_size / cfg.num_attention_heads;
    let (inv_freq, inv_freq_table_digest) = compute_inv_freq(cfg.rope_theta, head_dim);

    Model {
        cfg,
        embed_tokens,
        layers,
        final_norm,
        inv_freq,
        inv_freq_table_digest,
    }
}

/// out[o] = dot(weight_row(o), x), weight is [out_dim, in_dim] row-major.
fn matvec(weight: &[f32], in_dim: usize, out_dim: usize, x: &[f32]) -> Vec<f32> {
    let mut out = Vec::with_capacity(out_dim);
    for o in 0..out_dim {
        let row = &weight[o * in_dim..(o + 1) * in_dim];
        out.push(math::dot_seq(row, x));
    }
    out
}

fn rmsnorm(x: &[f32], weight: &[f32], eps: f32) -> Vec<f32> {
    let sq: Vec<f32> = x.iter().map(|&v| v * v).collect();
    let mean_sq = math::sum_seq(&sq) / (x.len() as f32);
    let scale = math::rsqrt(mean_sq + eps);
    x.iter()
        .zip(weight.iter())
        .map(|(&xi, &wi)| (xi * scale) * wi)
        .collect()
}

/// Apply RoPE (non-interleaved / "rotate-half" layout, per config's
/// rope_interleaved: false) to one head's vector, in place, for position
/// `pos`.
fn apply_rope(v: &mut [f32], pos: usize, inv_freq: &[f32]) {
    let half = inv_freq.len();
    let mut out = vec![0.0f32; v.len()];
    for i in 0..half {
        let angle = (pos as f32) * inv_freq[i];
        let c = math::cos_route_a(angle);
        let s = math::sin_route_a(angle);
        let x1 = v[i];
        let x2 = v[i + half];
        out[i] = (x1 * c) - (x2 * s);
        out[i + half] = (x2 * c) + (x1 * s);
    }
    v.copy_from_slice(&out);
}

struct DecodeState {
    // per-layer, per-kv-head K/V history: Vec<Vec<f32>> of length head_dim,
    // indexed [layer][kv_head][pos]
    k_hist: Vec<Vec<Vec<Vec<f32>>>>,
    v_hist: Vec<Vec<Vec<Vec<f32>>>>,
}

fn forward_step(
    m: &Model,
    token_id: u32,
    pos: usize,
    state: &mut DecodeState,
) -> Vec<f32> {
    let hidden = m.cfg.hidden_size;
    let n_heads = m.cfg.num_attention_heads;
    let n_kv = m.cfg.num_key_value_heads;
    let head_dim = hidden / n_heads;
    let group = n_heads / n_kv;
    let eps = m.cfg.rms_norm_eps;

    let mut x: Vec<f32> = m.embed_tokens
        [(token_id as usize) * hidden..(token_id as usize + 1) * hidden]
        .to_vec();

    for (li, layer) in m.layers.iter().enumerate() {
        let normed = rmsnorm(&x, &layer.input_layernorm, eps);

        let q_all = matvec(&layer.q_proj, hidden, n_heads * head_dim, &normed);
        let k_all = matvec(&layer.k_proj, hidden, n_kv * head_dim, &normed);
        let v_all = matvec(&layer.v_proj, hidden, n_kv * head_dim, &normed);

        // Split into heads, apply RoPE to q and k.
        let mut attn_out = vec![0.0f32; n_heads * head_dim];
        for h in 0..n_heads {
            let kv_h = h / group;
            let mut q_head = q_all[h * head_dim..(h + 1) * head_dim].to_vec();
            apply_rope(&mut q_head, pos, &m.inv_freq);

            if h % group == 0 {
                let mut k_head = k_all[kv_h * head_dim..(kv_h + 1) * head_dim].to_vec();
                apply_rope(&mut k_head, pos, &m.inv_freq);
                state.k_hist[li][kv_h].push(k_head);
                let v_head = v_all[kv_h * head_dim..(kv_h + 1) * head_dim].to_vec();
                state.v_hist[li][kv_h].push(v_head);
            }

            let n_pos = state.k_hist[li][kv_h].len();
            let scale = math::rsqrt(head_dim as f32);
            let mut scores = Vec::with_capacity(n_pos);
            for t in 0..n_pos {
                let s = math::dot_seq(&q_head, &state.k_hist[li][kv_h][t]) * scale;
                scores.push(s);
            }
            let mx = math::max_seq(&scores);
            let exps: Vec<f32> = scores.iter().map(|&s| math::exp_route_a(s - mx)).collect();
            let denom = math::sum_seq(&exps);
            let probs: Vec<f32> = exps.iter().map(|&e| e / denom).collect();

            let mut out_head = vec![0.0f32; head_dim];
            for d in 0..head_dim {
                let mut acc = 0.0f32;
                for t in 0..n_pos {
                    let term = probs[t] * state.v_hist[li][kv_h][t][d];
                    acc = acc + term;
                }
                out_head[d] = acc;
            }
            attn_out[h * head_dim..(h + 1) * head_dim].copy_from_slice(&out_head);
        }

        let attn_proj = matvec(&layer.o_proj, n_heads * head_dim, hidden, &attn_out);
        for i in 0..hidden {
            x[i] = x[i] + attn_proj[i];
        }

        let normed2 = rmsnorm(&x, &layer.post_attention_layernorm, eps);
        let gate = matvec(&layer.gate_proj, hidden, m.cfg.intermediate_size, &normed2);
        let up = matvec(&layer.up_proj, hidden, m.cfg.intermediate_size, &normed2);
        let mut h_mlp = vec![0.0f32; m.cfg.intermediate_size];
        for i in 0..m.cfg.intermediate_size {
            h_mlp[i] = math::silu(gate[i]) * up[i];
        }
        let down = matvec(&layer.down_proj, m.cfg.intermediate_size, hidden, &h_mlp);
        for i in 0..hidden {
            x[i] = x[i] + down[i];
        }
    }

    let normed_final = rmsnorm(&x, &m.final_norm, eps);
    matvec(&m.embed_tokens, hidden, m.cfg.vocab_size, &normed_final)
}

fn sha256_file(path: &Path) -> [u8; 32] {
    let bytes = std::fs::read(path).expect("read for hashing");
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    let d = hasher.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&d);
    out
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

fn main() {
    denormal::pin_ftz_daz();
    assert!(denormal::ftz_daz_on(), "FTZ/DAZ pin did not take effect");

    let weights_dir = Path::new("weights");
    let model = load_model(weights_dir);

    let tokenizer = Tokenizer::from_file(weights_dir.join("tokenizer.json"))
        .expect("load tokenizer.json");
    let encoding = tokenizer.encode(PROMPT, false).expect("tokenize prompt");
    let prompt_ids: Vec<u32> = encoding.get_ids().to_vec();

    eprintln!("prompt_ids={:?}", prompt_ids);

    let n_kv = model.cfg.num_key_value_heads;
    let mut state = DecodeState {
        k_hist: (0..model.cfg.num_hidden_layers)
            .map(|_| (0..n_kv).map(|_| Vec::new()).collect())
            .collect(),
        v_hist: (0..model.cfg.num_hidden_layers)
            .map(|_| (0..n_kv).map(|_| Vec::new()).collect())
            .collect(),
    };

    let model_hash = sha256_file(&weights_dir.join("model.safetensors"));
    let config_hash = sha256_file(&weights_dir.join("config.json"));
    let tokenizer_hash = sha256_file(&weights_dir.join("tokenizer.json"));

    let mut hasher = Sha256::new();
    hasher.update(model_hash);
    hasher.update(config_hash);
    hasher.update(tokenizer_hash);
    for &t in &prompt_ids {
        hasher.update(t.to_le_bytes());
    }

    // Greedy decode: feed every prompt token through the model (positions
    // 0..prompt_len-1, building K/V history at each), then repeatedly take
    // the logits from the *most recent* forward_step (whichever token was
    // just fed) and argmax to get the next token, feeding that token back
    // in at the next position. The very first generated token therefore
    // comes from the logits produced by feeding the LAST prompt token at
    // position (prompt_len - 1) -- standard greedy-decode semantics, not
    // an extra/duplicate step.
    let mut pos = 0usize;
    let mut logits = Vec::new();
    for &t in &prompt_ids {
        logits = forward_step(&model, t, pos, &mut state);
        pos += 1;
    }

    let mut generated: Vec<u32> = Vec::with_capacity(GEN_TOKS);
    for _ in 0..GEN_TOKS {
        for &lg in &logits {
            hasher.update(lg.to_bits().to_le_bytes());
        }
        let next = math::argmax(&logits) as u32;
        hasher.update(next.to_le_bytes());
        generated.push(next);
        logits = forward_step(&model, next, pos, &mut state);
        pos += 1;
    }

    let digest = hasher.finalize();

    println!(
        "CIS2_VERIFY digest={} prompt_toks={} gen_toks={} dtype=fp32",
        hex(&digest),
        prompt_ids.len(),
        GEN_TOKS
    );
    println!(
        "inv_freq table_digest={}",
        hex(&model.inv_freq_table_digest)
    );
    println!("generated_token_ids={:?}", generated);
    println!(
        "model_sha256={} config_sha256={} tokenizer_sha256={}",
        hex(&model_hash),
        hex(&config_hash),
        hex(&tokenizer_hash)
    );
}
