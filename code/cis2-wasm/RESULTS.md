# RESULTS
Published 2026-10-16 as part of the CIS-2 archive.
Date 2026-10-16, host hq. node v22.23.3, emcc 3.1.69 (Debian, clang 19.1.7, target wasm32-unknown-emscripten).
Flags: -std=c++17 -O2 -ffp-contract=off -fno-fast-math -sALLOW_MEMORY_GROWTH=1 -sMAXIMUM_MEMORY=4GB (+ -sNODERAWFS=1 for node).
Run under systemd-run --user --scope MemoryMax=2500M CPUWeight=60, nice 10.

| run | wall | digest | expected | verdict |
|---|---|---|---|---|
| smol16 | 12.8s | d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df | d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df | MATCH |
| smol128 | 31.7s | 22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6 | 22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6 | MATCH |
| qwen16 | 31.9s | c9dff099d927a6dda91514c260c7207de7aca4b361291e57fae390a352392e62 | c9dff099d927a6dda91514c260c7207de7aca4b361291e57fae390a352392e62 | MATCH |
| cov8 | 0.2s | 93ecb8384ec59629f60232aa5a184d50c38ca15cf94ee613de1e41bffe2d47f0 | 4660d6c33b6c0d51529b4be43687c004c8b7c0d8804439999b5af32683528734 | DIVERGE |
| smol16 via browser build (node harness, FS.writeFile+callMain) | 8s | d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df | same | MATCH |

## Coverage vector
wasm digest 93ecb8384ec59629f60232aa5a184d50c38ca15cf94ee613de1e41bffe2d47f0 (tokens 3,11,22,8,5,5,5,5,5,5,5,5).
A native g++ build of the ORIGINAL sources with the FTZ/DAZ pin and self-test disabled (scratch copy, not committed) gives the identical digest 93ecb838...,
so the absence of FTZ/DAZ is what moves it. No flush emulation was added; the divergence is reported, not hidden.

## FMA check
wasm-dis of cis2_host_node.wasm: 0 occurrences of fma or relaxed ops; 165 f32.mul, 168 f32.add, 9 f32.sqrt. -ffp-contract=off holds.

## Browser
Verified: web/cis2_host.js loads in headless Chromium (module init, FS.writeFile exported, callMain runs and prints the fpenv warnings and the --ids usage error); index.html loads and contains the expected-digest note; non-NODERAWFS build runs SmolLM2-16 end to end in node via web/harness.cjs with the matching digest.
NOT verified: the file-picker flow in index.html (cannot drive a native picker headless), and in-browser wall time/memory (a 1 GB Qwen file may stress browser memory; untested).
