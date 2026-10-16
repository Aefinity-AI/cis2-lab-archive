# w1x-opencl plan (2026-10-16)
Payload ~/feed-payload/cis2-opencl (gpu/ OpenCL backend of the C++ port: hardware div/sqrt build and CIS2_SOFT_DIVSQRT=1 build with software binary64 reduce_pi_2 for no-fp64 devices; gpu/test_soft unit test; jobs/cis2-opencl.template.sh; builder RESULTS.md).
Leg: cis2-opencl-hq via cm-feed on hq (sized by `cm-hosts budget hq`), TOKS "16 128". Rows: host g++, pocl (CPU), NVIDIA OpenCL (GTX 1050), Intel HD 630 iGPU via rusticl with soft div/sqrt, pocl with soft div/sqrt. Negative control: HD 630 with hardware div/sqrt (expected DIVERGE, informational, not in the bar).
Supplementary (not in the bar): pocl rows on w3/w4 (SSE4.2 class) if pocl installs there.
On MET: publish score, then cis2-spec PR: REPRODUCTIONS.md non-NVIDIA GPU cell (HD 630 soft) + pocl rows, HALL-OF-DIVERGENCE entry for the hardware div/sqrt control with the first-divergence localisation (norm1, layer 0, rsqrt/divide not correctly rounded), gpu/ OpenCL sources. Rule A: no timing figures.
Prior art: state/reports/prior-art/ (no public spec pins a non-NVIDIA GPU reproduction of a decode digest; vendor OpenCL conformance covers single ops, not an end-to-end decode).
