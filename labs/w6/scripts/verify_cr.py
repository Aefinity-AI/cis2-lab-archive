#!/usr/bin/env -S python3 -I
"""w6 PREREG step 1: multiprecision spot check that cr_expf is the correctly
rounded binary32 value. Reference = Python decimal exp at 80 digits, rounded
to binary32 with exact integer arithmetic (ties to even, gradual underflow).
usage: verify_cr.py LIB.so N SEED  -> prints RESULT/SMOKE line."""
import ctypes, random, struct, sys
from decimal import Decimal, getcontext
from fractions import Fraction
lib = ctypes.CDLL(sys.argv[1]); n = int(sys.argv[2]); seed = int(sys.argv[3])
lib.cr_expf.restype = ctypes.c_float; lib.cr_expf.argtypes = [ctypes.c_float]
getcontext().prec = 80
def f2u(f): return struct.unpack("<I", struct.pack("<f", f))[0]
def u2f(u): return struct.unpack("<f", struct.pack("<I", u))[0]
def unord(o): return (0x80000000 | -o) if o < 0 else o
def ref_bits(x):
    """binary32 bits of the correctly rounded exp(x) (x finite float32)."""
    if x == 0: return f2u(1.0)
    e = Fraction(Decimal(x).exp())          # Decimal(x) is exact for a float
    # exponent k with 2^k <= e < 2^(k+1)
    k = e.numerator.bit_length() - e.denominator.bit_length()
    if Fraction(2) ** k > e: k -= 1
    q = max(k - 23, -149)                    # quantum exponent
    m = e / Fraction(2) ** q                 # in units of the quantum
    r = m.numerator // m.denominator
    rem = m - r
    if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and r % 2 == 1): r += 1
    val_exp = q
    if r >= 1 << 24: r >>= 1; val_exp += 1   # carried to next binade
    if val_exp + 23 > 127: return 0x7f800000
    if r < (1 << 23):                        # subnormal (val_exp == -149)
        return r
    return ((val_exp + 23 + 127) << 23) | (r & 0x7fffff)
rng = random.Random(seed)
LO, HI = -0x42B00000, 0x42B17217           # ordered image of [-88, 88.7228]
bad = 0; bad_example = None
for i in range(n):
    o = rng.randint(LO, HI)
    xb = unord(o); x = u2f(xb)
    got = f2u(lib.cr_expf(x)); want = ref_bits(x)
    if got != want:
        bad += 1
        if bad_example is None: bad_example = (xb, got, want)
tag = "RESULT" if n >= 1000000 else "SMOKE"
status = "OK" if bad == 0 else "FAIL"
print("%s: %s w6-verify-cr n=%d seed=%d mismatches=%d%s" % (tag, status, n, seed, bad,
      "" if bad_example is None else " bad_example=x:0x%08x got:0x%08x want:0x%08x" % bad_example))
