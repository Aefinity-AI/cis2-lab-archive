//! Clean-room FTZ/DAZ pin, per E14a memo §3.4: "pin FTZ=on, DAZ=on for
//! all fp32 arithmetic in the decode path, on every ISA."

#[cfg(target_arch = "x86_64")]
pub fn pin_ftz_daz() {
    use std::arch::x86_64::{_mm_getcsr, _mm_setcsr};
    const FTZ_BIT: u32 = 1 << 15;
    const DAZ_BIT: u32 = 1 << 6;
    unsafe {
        let csr = _mm_getcsr();
        _mm_setcsr(csr | FTZ_BIT | DAZ_BIT);
    }
}

#[cfg(target_arch = "aarch64")]
pub fn pin_ftz_daz() {
    // FPCR bit 24 = FZ (flush-to-zero). NEON is FTZ-by-default per the
    // memo's §2 table, but we still set it explicitly on the scalar FPCR
    // so non-NEON scalar fp32 ops (which is everything in this reference)
    // are also pinned, matching the x86_64 leg's explicit-pin discipline
    // rather than relying on an assumed default.
    unsafe {
        let mut fpcr: u64;
        std::arch::asm!("mrs {0}, fpcr", out(reg) fpcr);
        fpcr |= 1 << 24;
        std::arch::asm!("msr fpcr, {0}", in(reg) fpcr);
    }
}

#[cfg(not(any(target_arch = "x86_64", target_arch = "aarch64")))]
compile_error!("cis2-verify: FTZ/DAZ pin not implemented for this ISA");

#[cfg(target_arch = "x86_64")]
pub fn ftz_daz_on() -> bool {
    use std::arch::x86_64::_mm_getcsr;
    let csr = unsafe { _mm_getcsr() };
    (csr & (1 << 15)) != 0 && (csr & (1 << 6)) != 0
}

#[cfg(target_arch = "aarch64")]
pub fn ftz_daz_on() -> bool {
    unsafe {
        let fpcr: u64;
        std::arch::asm!("mrs {0}, fpcr", out(reg) fpcr);
        (fpcr & (1 << 24)) != 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ftz_daz_pinned_and_denormal_input_flushed() {
        pin_ftz_daz();
        assert!(ftz_daz_on());
        let smallest_normal = f32::MIN_POSITIVE;
        let tiny = 1.0e-30f32;
        let r = std::hint::black_box(smallest_normal) * std::hint::black_box(tiny);
        assert_eq!(r, 0.0f32);
        let subnormal_literal = f32::from_bits(1);
        let r2 = std::hint::black_box(subnormal_literal) + std::hint::black_box(0.0f32);
        assert_eq!(r2, 0.0f32);
    }
}
