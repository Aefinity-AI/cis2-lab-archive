# cis2-sample RESULTS (clause DRAFT v0 §14; hq, i7-7700HQ AVX2, GTX 1050 sm_61, nvcc 12.4, g++ 14.2)

## Builds (run under nice -n 10, from this dir)
- host: g++ -std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math -I gpu -o out/host gpu/cis2_host.cpp
- cuda: nvcc -x cu -std=c++17 -O2 -fmad=false -ftz=true -prec-div=true -prec-sqrt=true --extended-lambda -DCIS2_CUDA_FTZ=1 -arch=sm_61 -I gpu -o out/cuda gpu/cis2_host.cpp
- KAT: same flags on gpu/cis2_murmur_kat.cpp (host and CUDA outputs byte-identical)
- numpy: <home>/projects/alice-model/.venv/bin/python -I ref/sample_ref.py (numpy 2.5.2; system python3 has no numpy, nothing installed)

## Design
New: gpu/cis2_sample.h. Per-index hash+u+g is a cis2_for_each lambda (CUDA kernel on the CUDA build, host loop otherwise),
writing u,g to device buffers that are copied back. Rank / top-k / top-p / z / first-index argmax run on the HOST in both builds
(logits already host-side), using cis2_exp_pinned, f32 div/add and sequential f32 accumulation. cis2_host.cpp: --sample SEED,T,K,P,
--sample-trace (model run: u/g/z hex for kept indices; toy: all 8), --sample-toy (toy vector, no model), --dump-logits DIR
(logits_stepNNN.f32, the vector used at step N). Greedy path untouched (no --sample => original argmax branch).
Greedy check (first and last, host and CUDA): CIS2_REF d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df at 16 tokens.

## KAT table (python and C++ identical; hash seed 0x43495332)

```
kat  seed               step  index  hash     u_bits   g_bits   bytecheck
0    0x0000000000000001 0     0      07731ea2 3cee63e0 bfa1b32b ok
1    0x0000000000000001 0     1      c832451b 3f483245 3fb392c7 ok
2    0x0000000000000001 1     0      c0d0c4fa 3f40d0c5 3fa15ffe ok
3    0xffffffffffffffff 7     49151  e682298d 3f668229 40104f5a ok
empty/seed0=00000000 empty/seed1=514e28b7 (expect 00000000 514e28b7)
```

## Toy vector (V=8, seed=1, step=0, T=0.8, K=4, P=0.9); host == CUDA == numpy (u,g,z bits, kept set, next_id)
Kept set = {1,2,5,6} (top-k 4; top-p keeps all four: c = 0.389, 0.778, 0.889 each < 0.9 before the next rank).
```
toy i=0 l=3f800000 s=3fa00000 h=07731ea2 u=3cee63e0 g=bfa1b32b kept=0 z=ff800000
toy i=1 l=40000000 s=40200000 h=c832451b u=3f483245 g=3fb392c7 kept=1 z=4079c964
toy i=2 l=40000000 s=40200000 h=68663a0b u=3ed0cc76 g=3ddeb89e kept=1 z=4026f5c5
toy i=3 l=bf800000 s=bfa00000 h=0f68eb80 u=3d768eb0 g=bf844163 kept=0 z=ff800000
toy i=4 l=3f000000 s=3f200000 h=ef1f23d1 u=3f6f1f23 g=402bdae7 kept=0 z=ff800000
toy i=5 l=40400000 s=40700000 h=62c78d96 u=3ec58f1a g=3d483f2a kept=1 z=407320fd
toy i=6 l=40400000 s=40700000 h=03469a9a u=3c51a6c0 g=bfbc6f8d kept=1 z=4011c83a
toy i=7 l=c0800000 s=c0a00000 h=de644043 u=3f5e6441 g=3ffafd67 kept=0 z=ff800000
step 0 next_id=1
```

## Model vector SmolLM2-135M, ids 6403,1980,253,655, seed=1 T=0.8 K=40 P=0.95
- 16 tokens host: CIS2_REF 98ed8bf7997816f366b7434f3fb097944cefe569debc75033f28390478f2aa35
- 16 tokens CUDA: CIS2_REF 98ed8bf7997816f366b7434f3fb097944cefe569debc75033f28390478f2aa35
  ids: 28,253,555,3365,15688,28203,761,354,2359,288,724,468,511,30,909,2275  (CUDA ids identical, cmp verified)
- 64 tokens host: CIS2_REF 6a760d9e4d7125517d8120c031327202ab1cffdb19edf24fc82b437884ccf55a
- 64 tokens CUDA: CIS2_REF 6a760d9e4d7125517d8120c031327202ab1cffdb19edf24fc82b437884ccf55a
  ids: 28,253,555,3365,15688,28203,761,354,2359,288,724,468,511,30,909,2275,338,5196,392,856,919,1365,2990,411,1380,732,502,736,536,876,284,638,392,856,536,1495,1365,30,1848,506,1048,731,13199,28,392,1124,457,701,617,416,1492,990,653,1798,284,919,2090,338,2573,7422,5587,284,2991,30  (CUDA ids identical, cmp verified)

## numpy agreement
ref/sample_ref.py (from clause text + spec §6.2/§6.5 only, np.float32 scalars, sequential sums): --kat reproduces all 4 hash/u/g rows; --toy reproduces u,g,z bits and next_id=1 of the port (kept indices; masked z = ff800000); --logits on the 16 dumped step-logit files reproduces all 16 sampled ids (out/np_steps16.txt). The 64-token run was not numpy-checked (not requested). numpy computes noise only for kept indices (masked z is -inf irrespective of g); the port computes it for all V.

## Job result (jobs/cis2-sample-hq.sh, SM=sm_61, host + CUDA)
```
RESULT: OK cis2-sample-hq greedy16=MATCH s16=98ed8bf7997816f366b7434f3fb097944cefe569debc75033f28390478f2aa35 s64=6a760d9e4d7125517d8120c031327202ab1cffdb19edf24fc82b437884ccf55a ids16=f8e7a6b6a0a6f54848d36f7fbaa08d3fcd2c89f49f5cfd585b6187c32985cfb7 hostcuda=MATCH weights=80521b40 ids=4b6618b6
```

## Clause ambiguities and choices
1. step index: "step (u32 LE)" -- not stated whether 0- or 1-based or relation to prompt. Chose the 0-based generation step (the loop variable of §11 decode; toy uses step=0).
2. "u = f32((h >> 9) * 2 + 1) * 2^-24": the integer is exact in f32 (< 2^24); implemented as (float)m * 0x33800000 bits. No ambiguity in value.
3. Parsing of T and P in "--sample SEED,T,K,P" (not in the clause): strtof (correctly rounded decimal -> f32); "0.8" -> 0x3f4ccccd, "0.95" -> 0x3f733333. numpy uses np.float32(string), same value.
4. "keep rank r iff r == 0 or c_{r-1} < top_p": taken literally with c = running f32 sum of p_0..p_r; the first failing rank ends the prefix (c is monotone non-decreasing, so later ranks also fail).
5. top-p "over the kept indices" (after top-k): m, e_r, denom are taken over the top-k survivors only (not all V); when top_k = 0 or >= V all V are used. top_k >= V treated as disabled.
6. "p_r = e_r / denom (division, §9.3 style)": plain f32 division.
7. §14.3 step 1 "temperature == 1.0 leaves s_i == l_i": always divides (x/1.0f is exact), no special case.
8. §14.5 "seed (u64 LE)": absorbed byte-wise little-endian; "f32 bits, u32 LE" via update_u32le. The sampled receipt absorbs the 13+8+4+4+4 bytes after the prompt ids, before step 0's logits.
9. §14.4 "FIRST index attaining the maximum of z" with -inf masked: rank 0 is always kept so z has a finite max; scan starts best=0 with strict >, as in §11.2.
10. §14.2 "ln_pinned(0.0f - ln_pinned(u))": ln(u) < 0 so the argument is positive; with u in (2^-24, 1-2^-24) no domain branch is hit. The inner ln of u close to 1 is a tiny negative number (> 2^-25 in magnitude), still normal under FTZ.
11. Validity checks (T finite > 0, P in (0,1]) are enforced in the CLI only; the clause does not say what a receipt verifier does with invalid headers. K is parsed as u32 (decimal).
12. The clause does not say the hash is computed at its length-16 specialisation; since MurmurHash3_x86_32 finalisation mixes the length, I implemented len=16 (4 blocks, empty tail) and cross-checked against a generic-length implementation (and the published empty-key/seed-1 value 0x514e28b7).
