"""E18/E18c GPU leg: build the single-source CUDA-portable C++ port with
nvcc and run it on a Kaggle GPU, in BOTH modes in one kernel run:

  1. sequential  — the spec-NORMATIVE v0.3b reduction order (`dot_seq`/
     `sum_seq`/`softmax_seq`). This is the load-bearing result. Exit
     status is governed by this mode alone (see "Exit status" below).
  2. tree        — the v0.4 CANDIDATE pinned blocked-tree reduction order
     (`-DCIS2_REDUCTION_TREE`; docs/design/CIS2_V04_TREE_REDUCTION.md).
     Reported as CANDIDATE PASS/FAIL. It is expected to disagree with the
     sequential digests (non-associative fp32 addition, different
     rounding, different bits, by design — see the design doc's
     "plan-wording bug" note) and never masks or overrides the sequential
     verdict.

Everything this needs — the gpu/ sources (which already contain BOTH
reduction orders, selected at compile time by -DCIS2_REDUCTION_TREE; see
cis2_math.h/cis2_host.cpp), the exact Makefile (read for its flags, not
invoked for the link step — see "Why not `make -C gpu cuda`" below), the
model weights, the prompt token-id files (sequential AND tree), and the
expected digests/traces (sequential AND tree) — is pulled from the
attached aefinityaiinc/cis2-e18b-gpu dataset (see ../make_dataset.sh).

Also builds and runs the HOST target here on the Kaggle CPU, as a control,
sequential mode only: if the host build mismatches on Kaggle, the problem
is this box's toolchain, not GPU arithmetic, and neither GPU result below
should be trusted until that is resolved.

Why not `make -C gpu cuda` / `cuda-tree` directly: those Makefile targets
pass `-c` (compile a relocatable device OBJECT only, never linked) — that
is deliberate on the dev box, which has nvcc but no physical GPU, so
nothing there could ever be run anyway (gpu/README.md SS12b). On a real
Kaggle GPU box we need a genuinely LINKED, RUNNABLE executable, so this
script invokes nvcc itself with the Makefile's own NVCCFLAGS (transcribed
below, kept in sync with gpu/Makefile's NVCCFLAGS by inspection) but
without `-c`, producing a real `cis2_cuda` / `cis2_cuda_tree` binary that
this script then actually executes on the device. This is the one place
this leg's flags are not mechanically read from the Makefile file itself
(only reproduced by hand) — everything else (source files, weights,
token ids, expected digests) is dataset-supplied with no transcription.

Also runs `make -C gpu nofma-cuda` here (needs no physical GPU — it
compiles a device object and greps its SASS with cuobjdump, exactly as
verified host-side; see gpu/README.md SS12b) so the FMA-free SASS claim is
independently re-checked on Kaggle's own CUDA toolchain/driver image, not
just on the dev box's.

PASS/FAIL definition (see ../README.md "Kaggle leg" / SS12): a run PASSES
only if its CIS2_REF digest is bit-identical to the pinned expected digest
AND (at 16 tokens, where a trace is compared) its trace file is
byte-identical to the expected trace. Anything else is FAIL, reported
with the first divergent trace line named.

Exit status: 0 ONLY IF both sequential checks (host_16tok, host_128tok,
gpu_16tok, gpu_128tok — i.e. host control AND GPU, both lengths) pass.
The tree/CANDIDATE checks are always reported in the results table and
JSON but NEVER affect the exit code — a tree FAIL is news, not a leg
failure, exactly because SS12 of the README establishes the tree digests
are new values with no claim to equal the sequential ones.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

INPUT_ROOT = Path("/kaggle/input")


def find_dataset():
    """Locate the cis2-e18b-gpu dataset wherever Kaggle mounted it.

    Kaggle has mounted datasets at /kaggle/input/<slug> and at
    /kaggle/input/datasets/<owner>/<slug>; v1 of this kernel hard-coded the
    first and died with FileNotFoundError. Resolve by content instead: the
    directory that holds gpu/Makefile, weights/ and gate/expected_digests.json.
    """
    fixed = INPUT_ROOT / "cis2-e18b-gpu"
    cands = [fixed] + [m.parent.parent for m in INPUT_ROOT.glob("**/gpu/Makefile")]
    for c in cands:
        if (c / "gpu" / "Makefile").exists() and (c / "weights").is_dir() \
                and (c / "gate" / "expected_digests.json").exists():
            return c
    print("dataset not found under /kaggle/input; tree (depth 4):")
    for q in sorted(INPUT_ROOT.glob("*/**/"))[:200]:
        if len(q.relative_to(INPUT_ROOT).parts) <= 4:
            print("  ", q)
    raise SystemExit("cis2-e18b-gpu dataset not mounted")


DATASET = None  # resolved in main() via find_dataset()
WORK = Path("/kaggle/working/e18b")
GPU = WORK / "gpu"
WEIGHTS = WORK / "weights"
GATE = WORK / "gate"
RESULTS_JSON = Path("/kaggle/working/e18_results.json")

# Transcribed from gpu/Makefile's NVCCFLAGS (README SS12b / SS7 "Build and
# gates"). Kept flag-for-flag identical, minus `-c` (this script links a
# real executable) and `-arch=$(NVCC_ARCH)` (substituted at call time,
# default sm_75 for Kaggle's T4, see below).
NVCC_ARCH = "sm_75"  # Kaggle free-tier GPU is a T4 (Turing). Override in
                      # code below if nvidia-smi reports a P100 (sm_60).
NVCCFLAGS_BASE = [
    "-x", "cu",
    "-std=c++17", "-O2", "-fmad=false", "-ftz=true",
    "-prec-div=true", "-prec-sqrt=true", "--extended-lambda",
    # nvcc has no preprocessor macro reflecting -ftz=true (PTXAS codegen
    # flag, not visible to the front end); define our own marker so
    # cis2_fpenv.h's compile-time guard can confirm this build script
    # actually passed -ftz=true. Keep in lockstep with the flag above.
    "-DCIS2_CUDA_FTZ=1",
]

RESULTS = {}  # label -> {"digest_pass":..., "trace_pass":..., "mode":...}


def hr(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def run(cmd, **kw):
    """Run a command, echo it, stream output, return CompletedProcess. Never
    raises: a missing binary (e.g. cuobjdump/nvidia-smi on an unexpected
    image) is reported as a non-zero-returncode CompletedProcess instead of
    crashing the whole kernel run."""
    print(f"$ {' '.join(str(c) for c in cmd)}")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    except (FileNotFoundError, OSError) as e:
        print(f"  (command failed to start: {e})", file=sys.stderr)
        return subprocess.CompletedProcess(cmd, returncode=127, stdout="", stderr=str(e))
    if p.stdout:
        print(p.stdout)
    if p.stderr:
        print(p.stderr, file=sys.stderr)
    return p


def parse_digest(stdout: str):
    for line in stdout.splitlines():
        if line.startswith("CIS2_REF"):
            for tok in line.split():
                if tok.startswith("digest="):
                    return tok.split("=", 1)[1]
    return None


def first_trace_divergence(expected_path: Path, got_path: Path):
    """Line-by-line compare. Returns None if identical, else a dict
    describing the first differing (layer, op)."""
    with open(expected_path) as fe, open(got_path) as fg:
        i = 0
        for i, (le, lg) in enumerate(zip(fe, fg), start=1):
            if le != lg:
                return {"line": i, "expected": le.rstrip("\n"), "got": lg.rstrip("\n")}
        rest_e = fe.readline()
        rest_g = fg.readline()
        if rest_e or rest_g:
            return {
                "line": i + 1,
                "expected": rest_e.rstrip("\n") or "<eof>",
                "got": rest_g.rstrip("\n") or "<eof>",
            }
    return None


def check(label, mode, binary, gen_toks, ids_file, expected, extra_args=None,
          trace_expected=None):
    """Run `binary --weights-dir WEIGHTS --ids ids_file --gen-toks N
    [--reduction tree] [--trace out]`, compare digest (+ trace, if given)
    against `expected`. Prints and returns a result dict; also records it
    into RESULTS[label]."""
    trace_out = GATE / f"{label}.trace" if trace_expected else None
    cmd = [
        str(binary),
        "--weights-dir", str(WEIGHTS),
        "--ids", str(ids_file),
        "--gen-toks", str(gen_toks),
    ]
    if extra_args:
        cmd += extra_args
    if trace_out:
        cmd += ["--trace", str(trace_out)]
    p = run(cmd)
    digest = parse_digest(p.stdout)
    digest_pass = (digest == expected)
    print(f"---- {label}: expected digest={expected}")
    print(f"---- {label}: got      digest={digest}")
    print(f"---- {label}: digest {'PASS' if digest_pass else 'FAIL'}")

    trace_pass = None
    divergence = None
    if trace_expected:
        if p.returncode == 0 and trace_out.exists():
            divergence = first_trace_divergence(Path(trace_expected), trace_out)
            trace_pass = divergence is None
            if trace_pass:
                print(f"---- {label}: trace PASS (byte-identical)")
            else:
                print(f"---- {label}: trace FAIL — first divergence at line {divergence['line']}:")
                print(f"       expected: {divergence['expected']}")
                print(f"       got     : {divergence['got']}")
        else:
            trace_pass = False
            print(f"---- {label}: trace FAIL — run did not produce a trace file (returncode={p.returncode})")

    overall = digest_pass and (trace_pass is not False)
    RESULTS[label] = {
        "mode": mode,
        "digest_pass": digest_pass,
        "trace_pass": trace_pass,
        "expected_digest": expected,
        "got_digest": digest,
        "returncode": p.returncode,
        "divergence": divergence,
    }
    print(f"---- {label}: OVERALL {'PASS' if overall else 'FAIL'}")
    return overall


def nvcc_link(src, out, tree, arch):
    """Link a genuinely runnable CUDA executable directly with nvcc (the
    Makefile's `cuda`/`cuda-tree` targets pass -c: object-only, never
    linked — see module docstring). Same flags as gpu/Makefile's
    NVCCFLAGS, minus -c, plus -DCIS2_REDUCTION_TREE for the tree binary."""
    flags = list(NVCCFLAGS_BASE) + [f"-arch={arch}", "-I", str(GPU)]
    if tree:
        flags = flags + ["-DCIS2_REDUCTION_TREE"]
    cmd = ["nvcc"] + flags + ["-o", str(out), str(src)]
    p = run(cmd)
    return p.returncode == 0 and out.exists()


def sass_dump_real_binary(label, binary):
    """cuobjdump --dump-sass the ACTUAL linked, runnable binary this script
    just built and is about to execute (cis2_cuda / cis2_cuda_tree) — not
    the standalone probe kernels `make nofma-cuda` uses (gpu/Makefile,
    cis2_sass_probe.cu). Addresses E18B_GPU_RESULT.md adversarial-review
    caveat 1: the probe wraps the same cis2_math.h arithmetic in its own
    __global__ kernels, not in the production cis2_index_kernel<F> lambda
    dispatcher this binary actually launches, so a future run should dump
    the real binary's SASS directly.

    The real binary's device code is one function template
    (`cis2_index_kernel<F>`, gpu/cis2_model.h) instantiated once per lambda
    call-site, so there is no clean per-op name like `k_dot_seq` to grep
    for as the probe does. Instead: dump the whole binary's SASS to a file,
    then report an FFMA count per demangled instantiation, so a human (or
    a future automated gate) can see directly which lambda call-sites, if
    any, contain FFMA — the same signal the probe gate reports, just
    against the real dispatch context instead of a stand-in.
    """
    out_txt = GATE / f"{label}.sass.txt"
    p = run(["cuobjdump", "--dump-sass", str(binary)])
    sass = p.stdout
    out_txt.write_text(sass if sass else f"(cuobjdump produced no stdout; returncode={p.returncode})\n"
                                          f"{p.stderr}")
    summary = {"binary": str(binary), "sass_file": str(out_txt),
               "cuobjdump_returncode": p.returncode, "functions": []}
    if p.returncode != 0 or not sass:
        print(f"---- {label}: cuobjdump FAILED (returncode={p.returncode}) — see {out_txt}")
        RESULTS.setdefault("sass_real_binary", {})[label] = summary
        return summary

    # Split on "Function :" lines (cuobjdump's own delimiter, same one
    # gpu/Makefile's nofma-cuda target awks on for the probe object).
    parts = re.split(r"^(\s*Function\s*:\s*.*)$", sass, flags=re.MULTILINE)
    total_ffma = 0
    # parts[0] is the preamble before the first Function; then alternating
    # (header-line, body) pairs.
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        name = header.split(":", 1)[1].strip() if ":" in header else header
        n_ffma = len(re.findall(r"\bFFMA\b", body))
        total_ffma += n_ffma
        summary["functions"].append({"name": name, "ffma_count": n_ffma})
        tag = "index_kernel" if "index_kernel" in name else "other"
        print(f"---- {label}: {name[:100]} [{tag}] FFMA count = {n_ffma}")
    summary["total_ffma"] = total_ffma
    summary["n_functions"] = len(summary["functions"])
    print(f"---- {label}: {summary['n_functions']} device function(s) found, "
          f"{total_ffma} total FFMA instruction(s) across all of them "
          f"(full disassembly: {out_txt})")
    RESULTS.setdefault("sass_real_binary", {})[label] = summary
    return summary


class NvidiaSmiSampler:
    """Sample `nvidia-smi --query-gpu=...` at a fixed interval into a CSV
    file for the duration of a run, addressing E18B_GPU_RESULT.md
    adversarial-review caveat 2 (no GPU-utilization/timing sample was
    captured; device execution was established from source structure, not
    a runtime measurement). This is a Kaggle-GPU-process observation, not
    a timing/benchmark claim about this dev box (no measurement here runs
    on penguin/box1)."""

    QUERY = "timestamp,utilization.gpu,utilization.memory,memory.used,memory.total"

    def __init__(self, label, interval_s=1):
        self.label = label
        self.csv_path = GATE / f"{label}_nvidia-smi.csv"
        self.proc = None
        self.interval_s = interval_s

    def start(self):
        try:
            f = open(self.csv_path, "w")
            self.proc = subprocess.Popen(
                ["nvidia-smi", f"--query-gpu={self.QUERY}", "--format=csv",
                 "-l", str(self.interval_s)],
                stdout=f, stderr=subprocess.STDOUT,
            )
            self._fh = f
            print(f"---- {self.label}: nvidia-smi sampler started -> {self.csv_path} "
                  f"(interval {self.interval_s}s)")
        except Exception as e:  # nvidia-smi missing, etc. — never fail the run for this
            print(f"---- {self.label}: nvidia-smi sampler FAILED to start: {e}")
            self.proc = None

    def stop_and_summarize(self):
        rows = []
        try:
            if self.proc is not None:
                time.sleep(self.interval_s)  # make sure at least one more sample lands
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except Exception:
                    self.proc.kill()
                try:
                    self._fh.close()
                except Exception:
                    pass
        except Exception as e:
            print(f"---- {self.label}: nvidia-smi sampler stop error: {e}")
        try:
            if self.csv_path.exists():
                lines = [l for l in self.csv_path.read_text().splitlines() if l.strip()]
                for l in lines[1:] if lines and lines[0].lower().startswith("timestamp") else lines:
                    cols = [c.strip() for c in l.split(",")]
                    if len(cols) >= 2:
                        rows.append(cols)
        except Exception as e:
            print(f"---- {self.label}: nvidia-smi sampler CSV parse error: {e}")
        util_vals = []
        for cols in rows:
            try:
                util_vals.append(float(cols[1].replace("%", "").strip()))
            except Exception:
                pass
        summary = {
            "label": self.label,
            "csv_file": str(self.csv_path),
            "n_samples": len(rows),
            "gpu_util_min": min(util_vals) if util_vals else None,
            "gpu_util_max": max(util_vals) if util_vals else None,
            "gpu_util_mean": (sum(util_vals) / len(util_vals)) if util_vals else None,
        }
        print(f"---- {self.label}: nvidia-smi samples n={summary['n_samples']} "
              f"gpu_util min/mean/max = "
              f"{summary['gpu_util_min']}/{summary['gpu_util_mean']}/{summary['gpu_util_max']} "
              f"(full CSV: {self.csv_path})")
        RESULTS.setdefault("nvidia_smi_samples", {})[self.label] = summary
        return summary


def gpu_name_and_arch():
    """Return (name, suggested_arch). Defaults to sm_75 (T4) unless
    nvidia-smi clearly reports a P100 (sm_60)."""
    p = run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    name = p.stdout.strip() if p.returncode == 0 else "UNKNOWN"
    arch = NVCC_ARCH
    if "P100" in name:
        arch = "sm_60"
    return name, arch


def main():
    hr("0. Environment")
    nvcc_ver = run(["nvcc", "--version"])
    gpu_name, arch = gpu_name_and_arch()
    print(f"GPU name (nvidia-smi): {gpu_name}")
    print(f"Selected NVCC_ARCH: {arch}")

    hr("1. Stage dataset -> writable working dir")
    global DATASET
    DATASET = find_dataset()
    print(f"dataset mounted at: {DATASET}")
    if WORK.exists():
        shutil.rmtree(WORK)
    shutil.copytree(DATASET / "gpu", GPU)
    shutil.copytree(DATASET / "weights", WEIGHTS)
    shutil.copytree(DATASET / "gate", GATE)
    # Overlay dataset (cis2-e18b-gpu-overlay): build files that changed after the
    # 215 MB weights dataset was uploaded. Files are copied over gpu/ and their
    # sha256 printed so the run log records exactly which sources were built.
    import hashlib
    for od in sorted(INPUT_ROOT.glob("**/cis2-e18b-gpu-overlay")):
        for f in sorted(od.glob("*")):  # flat: Kaggle CLI uploads top-level files only
            if f.is_file():
                shutil.copy2(f, GPU / f.name)
                print(f"overlay {f.name} sha256={hashlib.sha256(f.read_bytes()).hexdigest()}")

    expected = json.loads((GATE / "expected_digests.json").read_text())
    host_trace_16_seq = GATE / expected["sequential"]["16"]["trace_file"]
    host_trace_16_tree = GATE / expected["tree"]["16"]["trace_file"]

    hr("2. SASS FMA gate (no GPU execution needed): make -C gpu nofma-cuda")
    p_nofma = run(["make", "-C", str(GPU), "nofma-cuda", f"NVCC_ARCH={arch}"])
    nofma_pass = p_nofma.returncode == 0
    print(f"---- nofma-cuda (SASS, {arch}): {'PASS' if nofma_pass else 'FAIL'}")

    hr("3. Build: nvcc link, sequential  (cis2_cuda)")
    seq_bin = GPU / "cis2_cuda"
    cuda_seq_built = nvcc_link(GPU / "cis2_host.cpp", seq_bin, tree=False, arch=arch)
    if not cuda_seq_built:
        print("FATAL: nvcc link (sequential) failed or produced no binary.")
    else:
        hr("3b. SASS gate on the REAL cis2_cuda binary (cuobjdump --dump-sass)")
        sass_dump_real_binary("cis2_cuda", seq_bin)

    hr("4. Build: nvcc link, tree CANDIDATE  (cis2_cuda_tree, -DCIS2_REDUCTION_TREE)")
    tree_bin = GPU / "cis2_cuda_tree"
    cuda_tree_built = nvcc_link(GPU / "cis2_host.cpp", tree_bin, tree=True, arch=arch)
    if not cuda_tree_built:
        print("FATAL: nvcc link (tree) failed or produced no binary.")
    else:
        hr("4b. SASS gate on the REAL cis2_cuda_tree binary (cuobjdump --dump-sass)")
        sass_dump_real_binary("cis2_cuda_tree", tree_bin)

    hr("5. Control: build the HOST target here, on the Kaggle CPU (sequential only)")
    have_clang = shutil.which("clang++") is not None
    if have_clang:
        p = run(["make", "-C", str(GPU), "host"])
        host_bin = GPU / "cis2_host"
        host_label_build = "host (clang++)"
    else:
        print("clang++ not found on this image — falling back to host-gcc "
              "(gpu/README.md SS8 already shows host-gcc reproduces the "
              "same digest and a byte-identical trace, so this is still a "
              "valid control build, just via a different compiler).")
        p = run(["make", "-C", str(GPU), "host-gcc"])
        host_bin = GPU / "cis2_host_gcc"
        host_label_build = "host-gcc (g++)"
    host_built = p.returncode == 0 and host_bin.exists()
    if not host_built:
        print(f"FATAL: {host_label_build} build failed or produced no binary.")

    hr(f"6. Host control run ({host_label_build}) — sequential, 16 tokens, digest + trace")
    if host_built:
        check("host_16tok", "sequential", host_bin, 16, GATE / "ids_16tok.txt",
              expected["sequential"]["16"]["digest"], trace_expected=host_trace_16_seq)
    else:
        RESULTS["host_16tok"] = {"mode": "sequential", "digest_pass": False,
                                  "trace_pass": False, "skipped": "build failed"}

    hr(f"7. Host control run ({host_label_build}) — sequential, 128 tokens, digest only")
    if host_built:
        check("host_128tok", "sequential", host_bin, 128, GATE / "ids_128tok.txt",
              expected["sequential"]["128"]["digest"])
    else:
        RESULTS["host_128tok"] = {"mode": "sequential", "digest_pass": False,
                                   "trace_pass": None, "skipped": "build failed"}

    hr("8. GPU run (cis2_cuda) — SEQUENTIAL (spec-normative), 16 tokens, digest + trace")
    if cuda_seq_built:
        check("gpu_16tok", "sequential", seq_bin, 16, GATE / "ids_16tok.txt",
              expected["sequential"]["16"]["digest"], trace_expected=host_trace_16_seq)
    else:
        RESULTS["gpu_16tok"] = {"mode": "sequential", "digest_pass": False,
                                 "trace_pass": False, "skipped": "build failed"}

    hr("9. GPU run (cis2_cuda) — SEQUENTIAL, 128 tokens, digest only "
       "(nvidia-smi utilization sampled for this run)")
    if cuda_seq_built:
        smi_seq = NvidiaSmiSampler("gpu_128tok")
        smi_seq.start()
        try:
            check("gpu_128tok", "sequential", seq_bin, 128, GATE / "ids_128tok.txt",
                  expected["sequential"]["128"]["digest"])
        finally:
            smi_seq.stop_and_summarize()
    else:
        RESULTS["gpu_128tok"] = {"mode": "sequential", "digest_pass": False,
                                  "trace_pass": None, "skipped": "build failed"}

    hr("10. GPU run (cis2_cuda_tree) — v0.4 CANDIDATE tree, 16 tokens, digest + trace")
    if cuda_tree_built:
        check("gpu_16tok_tree", "tree", tree_bin, 16, GATE / "ids_16tok_tree.txt",
              expected["tree"]["16"]["digest"],
              trace_expected=host_trace_16_tree)
    else:
        RESULTS["gpu_16tok_tree"] = {"mode": "tree", "digest_pass": False,
                                      "trace_pass": False, "skipped": "build failed"}

    hr("11. GPU run (cis2_cuda_tree) — v0.4 CANDIDATE tree, 128 tokens, digest only "
       "(nvidia-smi utilization sampled for this run)")
    if cuda_tree_built:
        smi_tree = NvidiaSmiSampler("gpu_128tok_tree")
        smi_tree.start()
        try:
            check("gpu_128tok_tree", "tree", tree_bin, 128, GATE / "ids_128tok_tree.txt",
                  expected["tree"]["128"]["digest"])
        finally:
            smi_tree.stop_and_summarize()
    else:
        RESULTS["gpu_128tok_tree"] = {"mode": "tree", "digest_pass": False,
                                       "trace_pass": None, "skipped": "build failed"}

    hr("FINAL TABLE")
    header = f"{'mode':<11} {'tokens':<7} {'expected':<18} {'got':<18} {'verdict'}"
    print(header)
    print("-" * len(header))
    row_order = ["host_16tok", "host_128tok", "gpu_16tok", "gpu_128tok",
                 "gpu_16tok_tree", "gpu_128tok_tree"]
    toks_of = {"host_16tok": 16, "host_128tok": 128, "gpu_16tok": 16,
               "gpu_128tok": 128, "gpu_16tok_tree": 16, "gpu_128tok_tree": 128}
    for label in row_order:
        r = RESULTS.get(label, {})
        mode = r.get("mode", "?")
        toks = toks_of[label]
        exp = (r.get("expected_digest") or "")[:16] + "…"
        got = (r.get("got_digest") or "<none>")[:16] + ("…" if r.get("got_digest") else "")
        if r.get("skipped"):
            verdict = f"SKIPPED({r['skipped']})"
        else:
            ok = r["digest_pass"] and (r["trace_pass"] is not False)
            is_candidate = mode == "tree"
            verdict = ("CANDIDATE " if is_candidate else "") + ("PASS" if ok else "FAIL")
        print(f"{mode:<11} {toks:<7} {exp:<18} {got:<18} {verdict}")

    print()
    print(f"nvidia-smi GPU name : {gpu_name}")
    print(f"nvcc version        : {nvcc_ver.stdout.strip().splitlines()[-1] if nvcc_ver.returncode == 0 else 'FAILED'}")
    print(f"nofma-cuda SASS gate: {'PASS' if nofma_pass else 'FAIL'} (arch={arch})")

    # Sequential verdict governs exit status. Tree is reported, never gates.
    sequential_labels = ["host_16tok", "host_128tok", "gpu_16tok", "gpu_128tok"]
    tree_labels = ["gpu_16tok_tree", "gpu_128tok_tree"]

    def label_ok(label):
        r = RESULTS.get(label, {})
        if r.get("skipped"):
            return False
        return r["digest_pass"] and (r["trace_pass"] is not False)

    sequential_pass = all(label_ok(l) for l in sequential_labels)
    tree_pass = all(label_ok(l) for l in tree_labels)

    hr("SEQUENTIAL VERDICT (spec-normative v0.3b — governs exit status)")
    print("SEQUENTIAL: " + ("ALL PASS" if sequential_pass else "AT LEAST ONE FAILED"))
    hr("TREE VERDICT (v0.4 CANDIDATE — reported only, never gates exit status)")
    print("TREE: " + ("CANDIDATE ALL PASS" if tree_pass else "CANDIDATE AT LEAST ONE FAILED"))

    out = {
        "gpu_name": gpu_name,
        "nvcc_arch": arch,
        "nvcc_version": nvcc_ver.stdout.strip() if nvcc_ver.returncode == 0 else None,
        "nofma_cuda_pass": nofma_pass,
        "results": RESULTS,
        "sequential_pass": sequential_pass,
        "tree_candidate_pass": tree_pass,
    }
    RESULTS_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote {RESULTS_JSON}")

    sys.exit(0 if sequential_pass else 1)


if __name__ == "__main__":
    main()
