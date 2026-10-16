//! E18b support binary — dumps (a) the pinned CIS-2 v0.3b transcendental
//! constants as exact C++ hex-float literals and (b) a golden sweep of
//! `math.rs` function outputs over a deterministic input set, so the
//! CUDA-portable C++ port in `gpu/` is checked against the Rust reference
//! bit-for-bit instead of against hand-typed values.
//!
//! This binary is NOT part of the normative decode path. It reuses
//! `src/math.rs` and `src/denormal.rs` verbatim via `#[path]` so there is
//! exactly one copy of the normative arithmetic in the crate.
//!
//!   cargo run --release --bin math_dump -- <consts.h.frag> <golden.bin>

#[path = "../denormal.rs"]
mod denormal;
#[path = "../math.rs"]
mod math;

use std::io::Write;

/// Format an f32 as an exact C++ hex-float literal (`0x1.abcdefp+12f`).
/// Exact by construction: sign/exponent/mantissa are copied out of the
/// bit pattern, so there is no decimal round-trip to get wrong.
fn hexf32(x: f32) -> String {
    let b = x.to_bits();
    let sign = if b >> 31 == 1 { "-" } else { "" };
    let exp = ((b >> 23) & 0xFF) as i32;
    let man = b & 0x007F_FFFF;
    if exp == 0 {
        if man == 0 {
            return format!("{sign}0x0p+0f");
        }
        // subnormal: 0x0.<man>p-126
        return format!("{sign}0x0.{:06x}p-126f", man << 1);
    }
    format!("{sign}0x1.{:06x}p{:+}f", man << 1, exp - 127)
}

/// Format an f64 as an exact C++ hex-float literal (`0x1.abcdefabcdefap+0`).
fn hexf64(x: f64) -> String {
    let b = x.to_bits();
    let sign = if b >> 63 == 1 { "-" } else { "" };
    let exp = ((b >> 52) & 0x7FF) as i32;
    let man = b & 0x000F_FFFF_FFFF_FFFF;
    if exp == 0 {
        if man == 0 {
            return format!("{sign}0x0p+0");
        }
        return format!("{sign}0x0.{:013x}p-1022", man);
    }
    format!("{sign}0x1.{:013x}p{:+}", man, exp - 1023)
}

/// Deterministic 64-bit LCG (Knuth MMIX constants) — the sweep generator.
/// The generated inputs are written into the golden file, so the C++ side
/// never has to reproduce this generator; it only replays what it reads.
struct Lcg(u64);
impl Lcg {
    fn next(&mut self) -> u64 {
        self.0 = self
            .0
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        self.0
    }
}

fn sweep_inputs() -> Vec<f32> {
    let mut v: Vec<f32> = Vec::new();

    // --- explicit edge inputs -------------------------------------------
    let edge_bits: [u32; 20] = [
        0x0000_0000, // +0
        0x8000_0000, // -0
        0x0000_0001, // smallest positive subnormal
        0x8000_0001, // smallest negative subnormal
        0x007F_FFFF, // largest positive subnormal
        0x807F_FFFF,
        0x0080_0000, // smallest positive normal (2^-126)
        0x8080_0000,
        0x3F80_0000, // 1.0
        0xBF80_0000, // -1.0
        0x3F00_0000, // 0.5
        0xBF00_0000,
        0x7F7F_FFFF, // FLT_MAX
        0xFF7F_FFFF, // -FLT_MAX
        0x7F80_0000, // +inf
        0xFF80_0000, // -inf
        0x7FC0_0000, // qNaN
        0x3400_0000, // 2^-23
        0x4B00_0000, // 2^23
        0x5F00_0000, // 2^63
    ];
    for b in edge_bits {
        v.push(f32::from_bits(b));
    }

    // exp() range-reduction / clamp boundaries
    for &x in &[
        -88.0f32,
        -87.999_99,
        -88.000_01,
        88.0,
        87.999_99,
        88.000_01,
        -0.0,
        1e-10,
        -1e-10,
        0.693_147_2,
        -0.693_147_2,
        0.346_573_6,
        1e10,
        -1e10,
    ] {
        v.push(x);
        v.push(next_up(x));
        v.push(next_down(x));
    }

    // sin/cos octant-reduction boundaries: k*pi/2 and k*pi/4, both sides.
    let pi_2 = std::f64::consts::FRAC_PI_2;
    for k in -64i64..=64 {
        for frac in [0.5f64, 1.0, 1.5, 2.0] {
            let x = ((k as f64) * pi_2 * frac) as f32;
            v.push(x);
            v.push(next_up(x));
            v.push(next_down(x));
        }
    }

    // ln() frexp boundary: sqrt(0.5) either side, and powers of two.
    for e in -30i32..=30 {
        let p = (2.0f64).powi(e) as f32;
        v.push(p);
        v.push(next_up(p));
        v.push(next_down(p));
        let q = ((2.0f64).powi(e) * 0.707_106_781_186_547_5) as f32;
        v.push(q);
        v.push(next_up(q));
        v.push(next_down(q));
    }
    for &t in &[100_000.0f32, 1_000_000.0, 10_000.0, 500_000.0] {
        v.push(t);
    }

    // RoPE-realistic angles: pos * inv_freq for the actual SmolLM2 table.
    let ln_theta = math::ln_pinned(100_000.0f32);
    for i in 0..32usize {
        let frac = (2 * i) as f32 / 64.0f32;
        let a = frac * ln_theta;
        let inv_freq = math::exp_pinned(-a);
        for &pos in &[
            0usize, 1, 2, 3, 4, 7, 15, 16, 63, 127, 255, 1023, 4095, 8191,
        ] {
            v.push((pos as f32) * inv_freq);
        }
    }

    // --- deterministic pseudo-random sweep ------------------------------
    let mut r = Lcg(0x0123_4567_89AB_CDEF);
    // (a) uniform over the whole f32 bit space (hits NaN/inf/subnormals)
    for _ in 0..60_000 {
        v.push(f32::from_bits(r.next() as u32));
    }
    // (b) uniform in [-100, 100] (the exp/silu working range)
    for _ in 0..60_000 {
        let u = (r.next() >> 11) as f64 / (1u64 << 53) as f64;
        v.push(((u * 200.0) - 100.0) as f32);
    }
    // (c) uniform in [-9000, 9000] (the RoPE angle working range at
    //     max_position_embeddings = 8192)
    for _ in 0..60_000 {
        let u = (r.next() >> 11) as f64 / (1u64 << 53) as f64;
        v.push(((u * 18_000.0) - 9_000.0) as f32);
    }
    // (d) log-uniform positive in [2^-60, 2^60] (the ln working range)
    for _ in 0..60_000 {
        let u = (r.next() >> 11) as f64 / (1u64 << 53) as f64;
        v.push((2.0f64).powf(u * 120.0 - 60.0) as f32);
    }
    v
}

fn next_up(x: f32) -> f32 {
    if x.is_nan() || x == f32::INFINITY {
        return x;
    }
    let b = x.to_bits();
    if x == 0.0 {
        return f32::from_bits(1);
    }
    if x > 0.0 {
        f32::from_bits(b + 1)
    } else {
        f32::from_bits(b - 1)
    }
}
fn next_down(x: f32) -> f32 {
    if x.is_nan() || x == f32::NEG_INFINITY {
        return x;
    }
    let b = x.to_bits();
    if x == 0.0 {
        return f32::from_bits(0x8000_0001);
    }
    if x > 0.0 {
        f32::from_bits(b - 1)
    } else {
        f32::from_bits(b + 1)
    }
}

fn main() {
    // The golden values must be produced under the SAME fp environment the
    // decode path runs under (§1.3): FTZ/DAZ pinned, asserted by readback.
    denormal::pin_ftz_daz();
    assert!(denormal::ftz_daz_on(), "FTZ/DAZ must be pinned (§1.3)");

    let argv: Vec<String> = std::env::args().collect();
    let consts_path = argv
        .get(1)
        .cloned()
        .unwrap_or_else(|| "gpu/cis2_consts.inc".to_string());
    let golden_path = argv
        .get(2)
        .cloned()
        .unwrap_or_else(|| "gpu/math_golden.bin".to_string());

    // ---- (a) constants as exact C++ hex-float literals ------------------
    let mut c = String::new();
    c.push_str("// GENERATED by `cargo run --release --bin math_dump` — DO NOT EDIT.\n");
    c.push_str("// Exact hex-float renderings of the pinned CIS-2 v0.3b constants in\n");
    c.push_str("// src/math.rs. Hex-float, not decimal, so there is no decimal-parse\n");
    c.push_str("// ambiguity between the Rust and C++ front ends.\n");
    for (name, val) in math::exported_f32_consts() {
        c.push_str(&format!(
            "CIS2_CONST float {name} = {}; // bits 0x{:08x}\n",
            hexf32(val),
            val.to_bits()
        ));
    }
    for (name, val) in math::exported_f64_consts() {
        c.push_str(&format!(
            "CIS2_CONST double {name} = {}; // bits 0x{:016x}\n",
            hexf64(val),
            val.to_bits()
        ));
    }
    std::fs::write(&consts_path, &c).unwrap_or_else(|e| panic!("write {consts_path}: {e}"));
    eprintln!("wrote {consts_path}");

    // ---- (b) golden sweep ----------------------------------------------
    // Layout (all little-endian):
    //   magic "CIS2MTH1" (8 bytes)
    //   u32 n_inputs
    //   u32 n_funcs (= 6)
    //   then n_inputs records of (u32 x_bits, u32 out_bits[n_funcs])
    // Function order: exp, sin, cos, ln, silu, rsqrt.
    let inputs = sweep_inputs();
    let n = inputs.len();
    let mut buf: Vec<u8> = Vec::with_capacity(8 + 8 + n * 28);
    buf.extend_from_slice(b"CIS2MTH1");
    buf.extend_from_slice(&(n as u32).to_le_bytes());
    buf.extend_from_slice(&6u32.to_le_bytes());
    for &x in &inputs {
        buf.extend_from_slice(&x.to_bits().to_le_bytes());
        buf.extend_from_slice(&math::exp_pinned(x).to_bits().to_le_bytes());
        buf.extend_from_slice(&math::sin_pinned(x).to_bits().to_le_bytes());
        buf.extend_from_slice(&math::cos_pinned(x).to_bits().to_le_bytes());
        buf.extend_from_slice(&math::ln_pinned(x).to_bits().to_le_bytes());
        buf.extend_from_slice(&math::silu_pinned(x).to_bits().to_le_bytes());
        buf.extend_from_slice(&math::rsqrt_cr(x).to_bits().to_le_bytes());
    }
    let mut f =
        std::fs::File::create(&golden_path).unwrap_or_else(|e| panic!("create {golden_path}: {e}"));
    f.write_all(&buf).unwrap();
    eprintln!("wrote {golden_path} ({n} inputs)");

    // ---- (c) the table digest, so the C++ side can assert it ------------
    let td = math::table_digest();
    let hex: String = td.iter().map(|b| format!("{b:02x}")).collect();
    println!("table_digest={hex}");
}
