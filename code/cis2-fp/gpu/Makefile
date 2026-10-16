# gpu/Makefile — CIS-2 v0.3b CUDA-portable C++ port.
#
# E18c update: this box now HAS nvcc 12.9 (/usr/local/cuda/bin/nvcc) —
# compile-only, still no physical GPU. `cuda`/`cuda-tree`/`nofma-cuda`
# below are therefore real, exercised targets (they compile actual device
# code and disassemble the actual SASS) but their outputs are still never
# LINKED into a runnable executable and never RUN on a device — see
# gpu/README.md §8b for exactly what "compiled" does and does not prove
# here, and §11 for the still-outstanding real-GPU Kaggle leg.
#
# No timing figures are produced by any target here (lab Rule A).

ROOT      := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))..)
GPU       := $(ROOT)/gpu
WEIGHTS   ?= $(ROOT)/weights
CARGO     ?= cargo
# Every heavy build/run of the model goes through the box lock and is
# niced, per the lab's shared-box rule. The lock is taken by the individual
# commands, NOT by `make` itself — wrapping the whole make invocation in
# flock would deadlock against these (flock is not reentrant).
LOCK      ?= flock /tmp/aefinity-os.lock nice -n 10
CARGOWRAP ?= $(LOCK) env CARGO_BUILD_JOBS=4
REF       := $(ROOT)/target/release/cis2_ref
MATHDUMP  := $(ROOT)/target/release/math_dump

# -ffp-contract=off  : never fuse a multiply and an add (§1.4). This is the
#                      one flag that is NOT optional on aarch64: clang and
#                      gcc both contract separate mul+add into fmadd/fmla
#                      by default on AArch64 (the ISA has a native FMA and
#                      the "on" contraction default assumes you want it),
#                      unlike x86-64 where FMA needs -mfma to even be
#                      selectable. Omitting this flag on arm would silently
#                      reintroduce FMA and break bit-parity with the Rust
#                      reference, which never calls `.mul_add(`.
# -fno-fast-math     : no reassociation, no reciprocal substitution
# -ffp-model=strict  : no value-changing transforms at all
# NO -march=native   : it would let the compiler select FMA instructions
# `?=` will not do here: make defines CXX itself (to g++), so an unset CXX
# still counts as "already defined". Only replace make's own default.
ifeq ($(origin CXX),default)
CXX        := clang++
endif

UNAME_M    := $(shell uname -m)

CXXFLAGS   := -std=c++17 -O2 -ffp-contract=off -fno-fast-math -ffp-model=strict -I$(GPU)

# g++ equivalent. -fexcess-precision=standard keeps every f32 intermediate
# at f32. -msse2/-mfpmath=sse (x86-64 only) are the ISA floor the MXCSR pin
# assumes and are meaningless (and rejected by g++) on aarch64, where the
# scalar FP unit is always IEEE-conformant AAPCS64 hardware float — no
# x87-style 80-bit spill risk exists there, so nothing needs to replace
# -mfpmath=sse on that arch.
GCC        ?= g++
# g++ < 13 rejects -fexcess-precision=standard for C++ ('sorry, unimplemented');
# on x86-64 with -mfpmath=sse it is a no-op anyway (no x87 excess precision),
# so probe for it and drop it where unsupported. Kaggle's image hit this (E18b v2).
GCC_EXCESS := $(shell echo 'int main(){}' | $(GCC) -std=c++17 -fexcess-precision=standard -x c++ -c -o /dev/null - 2>/dev/null && echo -fexcess-precision=standard)
GCCFLAGS_COMMON := -std=c++17 -O2 -ffp-contract=off $(GCC_EXCESS) \
                    -fno-fast-math -I$(GPU)
ifeq ($(UNAME_M),$(filter $(UNAME_M),x86_64 amd64))
GCCFLAGS   := $(GCCFLAGS_COMMON) -msse2 -mfpmath=sse
else
GCCFLAGS   := $(GCCFLAGS_COMMON)
endif

# Device flags.
#   -fmad=false     : no fused multiply-add contraction (the device
#                     equivalent of -ffp-contract=off)
#   -ftz=true       : flush denormal inputs and outputs to zero, the device
#                     equivalent of the host MXCSR FTZ|DAZ pin (§1.3)
#   -prec-div=true  : IEEE correctly-rounded division, not an approximation
#   -prec-sqrt=true : IEEE correctly-rounded sqrt (§6.1 depends on it)
# and deliberately NO -use_fast_math and no __expf/__sinf/__cosf/__fdividef
# intrinsics anywhere in the source.
#   -DCIS2_CUDA_FTZ=1 : nvcc has no macro that reflects -ftz=true (it's a
#                       PTXAS codegen flag, not visible to the preprocessor),
#                       so this defines our own marker for cis2_fpenv.h's
#                       compile-time guard to check. Keep in lockstep with
#                       -ftz=true above.
# NVCC_ARCH: Kaggle's free-tier GPU is a T4 (Turing, sm_75) — pinned so
# `cuda`/`cuda-tree`/`nofma-cuda` generate real SASS for the actual target
# device, not a default/fallback virtual architecture. Override with
# `make ... NVCC_ARCH=sm_60` if Kaggle assigns a P100 instead.
NVCC       ?= nvcc
CUOBJDUMP  ?= cuobjdump
NVCC_ARCH  ?= sm_75
NVCCFLAGS  := -std=c++17 -O2 -fmad=false -ftz=true -prec-div=true -prec-sqrt=true \
              --extended-lambda -arch=$(NVCC_ARCH) -I$(GPU) -DCIS2_CUDA_FTZ=1

GEN_TOKS   ?= 16
SCRATCH    ?= $(GPU)/.gate

.PHONY: all host host-gcc host-tree cuda cuda-tree test-math gate gate-128 \
        gate-tree gate-tree-128 nofma nofma-cuda nolibm rust clean

all: host test_math

# ---------------------------------------------------------------- binaries

host: $(GPU)/cis2_host
$(GPU)/cis2_host: $(GPU)/cis2_host.cpp $(GPU)/cis2_model.h $(GPU)/cis2_math.h \
                  $(GPU)/cis2_fpenv.h $(GPU)/cis2_sha256.h $(GPU)/cis2_consts.inc
	$(LOCK) $(CXX) $(CXXFLAGS) -o $@ $<

host-gcc: $(GPU)/cis2_host_gcc
$(GPU)/cis2_host_gcc: $(GPU)/cis2_host.cpp $(GPU)/cis2_model.h $(GPU)/cis2_math.h \
                      $(GPU)/cis2_fpenv.h $(GPU)/cis2_sha256.h $(GPU)/cis2_consts.inc
	$(LOCK) $(GCC) $(GCCFLAGS) -o $@ $<

# v0.4 CANDIDATE (E18c): same source, same flags, +CIS2_REDUCTION_TREE.
host-tree: $(GPU)/cis2_host_tree
$(GPU)/cis2_host_tree: $(GPU)/cis2_host.cpp $(GPU)/cis2_model.h $(GPU)/cis2_math.h \
                       $(GPU)/cis2_fpenv.h $(GPU)/cis2_sha256.h $(GPU)/cis2_consts.inc
	$(LOCK) $(CXX) $(CXXFLAGS) -DCIS2_REDUCTION_TREE -o $@ $<

# E18c: this box now has nvcc (compile-only, no GPU — see header note).
# `-c`: a relocatable device object, not a linked executable — this box
# has no libcudart-linkable runtime target to run it against anyway, and
# an object file is all `nofma-cuda`'s SASS inspection needs. Compiling
# the FULL host driver (weights/JSON/safetensors loading, not just the
# arithmetic kernels) is real signal that the single-source file is
# actually nvcc-clean, not just clang/g++-clean — that is what this
# target proves, and ONLY what it proves: it has never been linked into
# a runnable binary and never executed on a device.
cuda: $(GPU)/cis2_cuda.o
$(GPU)/cis2_cuda.o: $(GPU)/cis2_host.cpp $(GPU)/cis2_model.h $(GPU)/cis2_math.h \
                    $(GPU)/cis2_fpenv.h $(GPU)/cis2_sha256.h $(GPU)/cis2_consts.inc
	$(LOCK) $(NVCC) $(NVCCFLAGS) -x cu -c -o $@ $<

# v0.4 CANDIDATE — same, +CIS2_REDUCTION_TREE.
cuda-tree: $(GPU)/cis2_cuda_tree.o
$(GPU)/cis2_cuda_tree.o: $(GPU)/cis2_host.cpp $(GPU)/cis2_model.h $(GPU)/cis2_math.h \
                         $(GPU)/cis2_fpenv.h $(GPU)/cis2_sha256.h $(GPU)/cis2_consts.inc
	$(LOCK) $(NVCC) $(NVCCFLAGS) -x cu -DCIS2_REDUCTION_TREE -c -o $@ $<

test_math: $(GPU)/test_math
$(GPU)/test_math: $(GPU)/test_math.cpp $(GPU)/cis2_math.h $(GPU)/cis2_fpenv.h \
                  $(GPU)/cis2_consts.inc
	$(LOCK) $(CXX) $(CXXFLAGS) -o $@ $<

rust:
	cd $(ROOT) && $(CARGOWRAP) $(CARGO) build --release

# The golden sweep and the hex-float constant file are GENERATED from
# src/math.rs, never hand-typed.
$(GPU)/math_golden.bin: rust
	cd $(ROOT) && $(LOCK) $(MATHDUMP) $(GPU)/cis2_consts.inc $(GPU)/math_golden.bin

# ------------------------------------------------------------------- gates

## Every pinned function, bit-exact against the Rust reference over the
## recorded sweep (edge inputs, denormals, range-reduction boundaries, and
## 240 000 pseudo-random draws).
test-math: $(GPU)/test_math $(GPU)/math_golden.bin
	$(LOCK) $(GPU)/test_math $(GPU)/math_golden.bin

## Digest equality + trace equality at GEN_TOKS tokens. Exits non-zero on
## any mismatch.
gate: $(GPU)/cis2_host rust
	@mkdir -p $(SCRATCH)
	cd $(ROOT) && $(LOCK) $(REF) --weights-dir $(WEIGHTS) --gen-toks $(GEN_TOKS) \
	    --dump-ids $(SCRATCH)/ids.txt --trace $(SCRATCH)/rust.trace \
	    > $(SCRATCH)/rust.out 2> $(SCRATCH)/rust.err
	cd $(ROOT) && $(LOCK) $(GPU)/cis2_host --weights-dir $(WEIGHTS) \
	    --ids $(SCRATCH)/ids.txt --gen-toks $(GEN_TOKS) \
	    --trace $(SCRATCH)/cpp.trace \
	    > $(SCRATCH)/cpp.out 2> $(SCRATCH)/cpp.err
	@echo "---- CIS2_REF, side by side (gen_toks=$(GEN_TOKS)) ----"
	@printf 'rust: %s\n' "$$(grep '^CIS2_REF' $(SCRATCH)/rust.out)"
	@printf 'c++ : %s\n' "$$(grep '^CIS2_REF' $(SCRATCH)/cpp.out)"
	@r=$$(grep '^CIS2_REF' $(SCRATCH)/rust.out | sed 's/.*digest=\([0-9a-f]*\).*/\1/'); \
	 c=$$(grep '^CIS2_REF' $(SCRATCH)/cpp.out  | sed 's/.*digest=\([0-9a-f]*\).*/\1/'); \
	 if [ -z "$$r" ] || [ "$$r" != "$$c" ]; then \
	   echo "GATE FAIL: digest mismatch"; exit 1; \
	 fi; \
	 echo "digest equality: PASS"
	@if cmp -s $(SCRATCH)/rust.trace $(SCRATCH)/cpp.trace; then \
	   echo "trace equality : PASS ($$(wc -l < $(SCRATCH)/rust.trace) lines identical)"; \
	 else \
	   echo "GATE FAIL: first differing trace line:"; \
	   diff $(SCRATCH)/rust.trace $(SCRATCH)/cpp.trace | head -8; exit 1; \
	 fi
	@echo "GATE PASS"

## The same digest gate at 128 tokens (no trace: the file is large and the
## 16-token trace already localises any divergence).
gate-128: $(GPU)/cis2_host rust
	@mkdir -p $(SCRATCH)
	cd $(ROOT) && $(LOCK) $(REF) --weights-dir $(WEIGHTS) --gen-toks 128 --dump-ids $(SCRATCH)/ids128.txt \
	    > $(SCRATCH)/rust128.out 2> $(SCRATCH)/rust128.err
	cd $(ROOT) && $(LOCK) $(GPU)/cis2_host --weights-dir $(WEIGHTS) \
	    --ids $(SCRATCH)/ids128.txt --gen-toks 128 \
	    > $(SCRATCH)/cpp128.out 2> $(SCRATCH)/cpp128.err
	@echo "---- CIS2_REF, side by side (gen_toks=128) ----"
	@printf 'rust: %s\n' "$$(grep '^CIS2_REF' $(SCRATCH)/rust128.out)"
	@printf 'c++ : %s\n' "$$(grep '^CIS2_REF' $(SCRATCH)/cpp128.out)"
	@r=$$(grep '^CIS2_REF' $(SCRATCH)/rust128.out | sed 's/.*digest=\([0-9a-f]*\).*/\1/'); \
	 c=$$(grep '^CIS2_REF' $(SCRATCH)/cpp128.out  | sed 's/.*digest=\([0-9a-f]*\).*/\1/'); \
	 if [ -z "$$r" ] || [ "$$r" != "$$c" ]; then echo "GATE FAIL: digest mismatch"; exit 1; fi
	@echo "GATE PASS (128 tokens)"

## v0.4 CANDIDATE (E18c): the same digest+trace gate as `gate`, but both
## sides run --reduction tree / -DCIS2_REDUCTION_TREE. This does NOT
## reproduce the v0.3b sequential digests (see docs/design/
## CIS2_V04_TREE_REDUCTION.md) — it establishes a NEW digest pair,
## Rust-tree == C++-host-tree, which is this leg's actual claim.
gate-tree: $(GPU)/cis2_host_tree rust
	@mkdir -p $(SCRATCH)
	cd $(ROOT) && $(LOCK) $(REF) --weights-dir $(WEIGHTS) --gen-toks $(GEN_TOKS) \
	    --reduction tree \
	    --dump-ids $(SCRATCH)/ids_tree.txt --trace $(SCRATCH)/rust_tree.trace \
	    > $(SCRATCH)/rust_tree.out 2> $(SCRATCH)/rust_tree.err
	cd $(ROOT) && $(LOCK) $(GPU)/cis2_host_tree --weights-dir $(WEIGHTS) \
	    --ids $(SCRATCH)/ids_tree.txt --gen-toks $(GEN_TOKS) \
	    --trace $(SCRATCH)/cpp_tree.trace \
	    > $(SCRATCH)/cpp_tree.out 2> $(SCRATCH)/cpp_tree.err
	@echo "---- CIS2_REF, tree mode, side by side (gen_toks=$(GEN_TOKS)) ----"
	@printf 'rust: %s\n' "$$(grep '^CIS2_REF' $(SCRATCH)/rust_tree.out)"
	@printf 'c++ : %s\n' "$$(grep '^CIS2_REF' $(SCRATCH)/cpp_tree.out)"
	@r=$$(grep '^CIS2_REF' $(SCRATCH)/rust_tree.out | sed 's/.*digest=\([0-9a-f]*\).*/\1/'); \
	 c=$$(grep '^CIS2_REF' $(SCRATCH)/cpp_tree.out  | sed 's/.*digest=\([0-9a-f]*\).*/\1/'); \
	 if [ -z "$$r" ] || [ "$$r" != "$$c" ]; then \
	   echo "GATE FAIL: tree-mode digest mismatch"; exit 1; \
	 fi; \
	 echo "tree-mode digest equality: PASS"
	@if cmp -s $(SCRATCH)/rust_tree.trace $(SCRATCH)/cpp_tree.trace; then \
	   echo "tree-mode trace equality : PASS ($$(wc -l < $(SCRATCH)/rust_tree.trace) lines identical)"; \
	 else \
	   echo "GATE FAIL: first differing tree-mode trace line:"; \
	   diff $(SCRATCH)/rust_tree.trace $(SCRATCH)/cpp_tree.trace | head -8; exit 1; \
	 fi
	@echo "GATE PASS (tree mode)"

## v0.4 CANDIDATE — tree-mode digest gate at 128 tokens.
gate-tree-128: $(GPU)/cis2_host_tree rust
	@mkdir -p $(SCRATCH)
	cd $(ROOT) && $(LOCK) $(REF) --weights-dir $(WEIGHTS) --gen-toks 128 --reduction tree \
	    --dump-ids $(SCRATCH)/ids128_tree.txt \
	    > $(SCRATCH)/rust128_tree.out 2> $(SCRATCH)/rust128_tree.err
	cd $(ROOT) && $(LOCK) $(GPU)/cis2_host_tree --weights-dir $(WEIGHTS) \
	    --ids $(SCRATCH)/ids128_tree.txt --gen-toks 128 \
	    > $(SCRATCH)/cpp128_tree.out 2> $(SCRATCH)/cpp128_tree.err
	@echo "---- CIS2_REF, tree mode, side by side (gen_toks=128) ----"
	@printf 'rust: %s\n' "$$(grep '^CIS2_REF' $(SCRATCH)/rust128_tree.out)"
	@printf 'c++ : %s\n' "$$(grep '^CIS2_REF' $(SCRATCH)/cpp128_tree.out)"
	@r=$$(grep '^CIS2_REF' $(SCRATCH)/rust128_tree.out | sed 's/.*digest=\([0-9a-f]*\).*/\1/'); \
	 c=$$(grep '^CIS2_REF' $(SCRATCH)/cpp128_tree.out  | sed 's/.*digest=\([0-9a-f]*\).*/\1/'); \
	 if [ -z "$$r" ] || [ "$$r" != "$$c" ]; then echo "GATE FAIL: tree-mode digest mismatch"; exit 1; fi
	@echo "GATE PASS (tree mode, 128 tokens)"

## §1.4: the binary must contain no fused multiply-add instruction.
## x86-64 FMA mnemonics: vfmadd/vfnmadd/vfmsub/vfnmsub.
## aarch64 FMA mnemonics: fmadd/fmsub/fnmadd/fnmsub (scalar), fmla/fmls
## (Advanced SIMD/NEON, contracted from separate mul+add without -ffma).
ifeq ($(UNAME_M),$(filter $(UNAME_M),x86_64 amd64))
FMA_GREP   := 'vfmadd|vfnmadd|vfmsub|vfnmsub'
else
FMA_GREP   := 'fmadd|fmsub|fnmadd|fnmsub|fmla|fmls'
endif
nofma: $(GPU)/cis2_host $(GPU)/test_math $(GPU)/cis2_host_tree
	@for b in $(GPU)/cis2_host $(GPU)/test_math $(GPU)/cis2_host_tree; do \
	  n=$$(objdump -d $$b | grep -cE $(FMA_GREP) || true); \
	  echo "$$b: fma instructions ($(UNAME_M), pattern=$(FMA_GREP)) = $$n"; \
	  if [ "$$n" != "0" ]; then \
	    echo "GATE FAIL: FMA present in $$b"; \
	    objdump -d $$b | grep -E $(FMA_GREP) | head -8; \
	    exit 1; \
	  fi; \
	done
	@echo "no-FMA gate: PASS (host, host-tree, test_math)"

## v0.4 CANDIDATE (E18c): compile the reduction kernels (sequential AND
## tree) to real device SASS for NVCC_ARCH (default sm_75, T4) and assert
## zero FFMA in the four pure reduction kernels (no division, no sqrt:
## k_dot_seq/k_sum_seq/k_dot_tree/k_sum_tree). The two softmax kernels
## contain one genuine division each; -prec-div=true division on an
## architecture with no hardware DIV (Turing included) is a MUFU.RCP +
## Newton-Raphson refinement sequence that legitimately contains FFMA —
## the documented exception (gpu/README.md §1) — so their FFMA count is
## reported, not gated to zero. No physical GPU is used or required:
## `cuobjdump --dump-sass` disassembles the compiled object directly.
$(GPU)/cis2_sass_probe.o: $(GPU)/cis2_sass_probe.cu $(GPU)/cis2_math.h \
                          $(GPU)/cis2_consts.inc
	$(LOCK) $(NVCC) $(NVCCFLAGS) -c -o $@ $<
nofma-cuda: $(GPU)/cis2_sass_probe.o
	@sass=$$($(LOCK) $(CUOBJDUMP) --dump-sass $(GPU)/cis2_sass_probe.o); \
	strict_fail=0; \
	for fn in k_dot_seq k_sum_seq k_dot_tree k_sum_tree; do \
	  body=$$(printf '%s\n' "$$sass" | awk -v f="$$fn" '/^\t\tFunction : /{p=(index($$0,f)>0)} p'); \
	  n=$$(printf '%s\n' "$$body" | grep -cE 'FFMA' || true); \
	  echo "$$fn (SASS, $(NVCC_ARCH)): FFMA count = $$n"; \
	  if [ "$$n" != "0" ]; then strict_fail=1; \
	    printf '%s\n' "$$body" | grep -E 'FFMA' | head -8; \
	  fi; \
	done; \
	for fn in k_softmax_seq k_softmax_tree; do \
	  body=$$(printf '%s\n' "$$sass" | awk -v f="$$fn" '/^\t\tFunction : /{p=(index($$0,f)>0)} p'); \
	  n=$$(printf '%s\n' "$$body" | grep -cE 'FFMA' || true); \
	  echo "$$fn (SASS, $(NVCC_ARCH)): FFMA count = $$n (expected: attributable to -prec-div division refinement, NOT gated to zero)"; \
	done; \
	if [ "$$strict_fail" != "0" ]; then echo "GATE FAIL: FMA present in a pure reduction kernel"; exit 1; fi
	@echo "no-FMA-cuda gate: PASS (k_dot_seq/k_sum_seq/k_dot_tree/k_sum_tree strictly zero FFMA; softmax reported separately)"

## No libm transcendental is linked into the arithmetic path.
nolibm: $(GPU)/cis2_host $(GPU)/test_math
	@for b in $(GPU)/cis2_host $(GPU)/test_math; do \
	  n=$$(nm -u $$b | grep -cE '\b(expf|sinf|cosf|powf|logf|exp|log|sin|cos|pow)@' || true); \
	  echo "$$b: undefined libm math symbols = $$n"; \
	  nm -u $$b | grep -E '\b(expf|sinf|cosf|powf|logf|exp|log|sin|cos|pow)@' || true; \
	  if [ "$$n" != "0" ]; then echo "GATE FAIL: libm math symbol in $$b"; exit 1; fi; \
	done
	@echo "no-libm gate: PASS"

clean:
	rm -f $(GPU)/cis2_host $(GPU)/cis2_host_gcc $(GPU)/cis2_host_tree \
	      $(GPU)/test_math $(GPU)/test_math_gcc \
	      $(GPU)/cis2_cuda $(GPU)/cis2_cuda.o $(GPU)/cis2_cuda_tree.o \
	      $(GPU)/cis2_sass_probe.o
	rm -rf $(SCRATCH)
