"""LLM-5b Kaggle scale leg: acceptance test for cis2-fp PR #12
(cm/llm5b-stream-widen @ 26c752c, streaming per-tensor safetensors
widening instead of holding the whole bf16 file + f32 model at once).
Identical recipe to LLM-4 (tests/kaggle/LLM4-LOG.md), only the engine
source ref changed, plus added memory instrumentation
(/usr/bin/time -v around each cis2_ref invocation, free -g before/after).

  1. Qwen/Qwen2-7B (~15 GB bf16, 4 safetensors shards) — cis2_ref only
     understands a single `model.safetensors` file (see
     src/main.rs::main(), `weights_path = root.join("model.safetensors")`),
     so this script first merges the 4 HF shards into one file with a
     byte-level streaming merge (no tensor decode, no bf16->f32 widening —
     just copying each tensor's raw bytes to new offsets per
     model.safetensors.index.json) to keep the merge step itself cheap.
     It then runs cis2_ref once, gen-toks=4, and reports whatever actually
     happens: PASS-with-digest, a clean non-zero exit, or a kill (OOM).
     This is expected to fail from memory pressure (full bf16 load +
     per-tensor f32 widening + per-layer struct copies), NOT engineered to
     fail — if it happens to succeed, that is reported too.
  2. Qwen/Qwen2-1.5B (~3 GB bf16, single-shard) — run cis2_ref TWICE with
     identical prompt/gen-toks and print both CIS2_REF witness digest
     lines, to show run-to-run bit-identity on a real ~1.5B checkpoint.

Everything is downloaded from the public Hugging Face Hub, no gated repo,
no HF token required. Engine source comes from the attached PRIVATE
dataset aefinityaiinc/cis2-fp-engine-llm4 (src/, Cargo.toml, Cargo.lock,
rust-toolchain.toml only — no weights, no target/, no .git).
"""
import json
import os
import resource
import struct
import subprocess
import sys
import time
from pathlib import Path

INPUT_ROOT = Path("/kaggle/input")
WORK = Path("/kaggle/working")
ENGINE_SRC_NAME = "cis2-fp-engine-cis3-0k"
PROMPT = "Once upon a time"
GEN_TOKS_7B = 4
GEN_TOKS_1B = 8


def hr(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78, flush=True)


def run(cmd, **kw):
    print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    dt = time.time() - t0
    if p.stdout:
        print(p.stdout)
    if p.stderr:
        print(p.stderr, file=sys.stderr)
    print(f"  (exit={p.returncode}, {dt:.1f}s)", flush=True)
    return p, dt


def find_engine_src():
    fixed = INPUT_ROOT / ENGINE_SRC_NAME
    cands = [fixed] + [m.parent for m in INPUT_ROOT.glob(f"**/{ENGINE_SRC_NAME}/Cargo.toml")]
    for c in cands:
        if (c / "Cargo.toml").exists() and (c / "src" / "main.rs").exists():
            return c
    print("engine source dataset not found under /kaggle/input; tree:")
    for q in sorted(INPUT_ROOT.glob("**/*"))[:300]:
        print("  ", q)
    raise SystemExit("cis2-fp-engine-llm4 dataset not mounted")


def install_rust():
    hr("installing rust toolchain (rustup, matches rust-toolchain.toml)")
    p, _ = run([
        "bash", "-c",
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | "
        "sh -s -- -y --default-toolchain none --profile minimal",
    ])
    if p.returncode != 0:
        raise SystemExit("rustup install failed")
    os.environ["PATH"] = str(Path.home() / ".cargo" / "bin") + ":" + os.environ["PATH"]


def build_engine(src_dir: Path) -> Path:
    hr(f"building cis2_ref (release) from {src_dir}")
    build_dir = WORK / "engine"
    run(["bash", "-c", f"rm -rf {build_dir} && cp -r {src_dir} {build_dir}"])
    # rustup will fetch+install the exact toolchain named in rust-toolchain.toml
    # on first cargo invocation in this directory.
    p, dt = run(["cargo", "build", "--release"], cwd=str(build_dir))
    binary = build_dir / "target" / "release" / "cis2_ref"
    if p.returncode != 0 or not binary.exists():
        raise SystemExit(f"cargo build failed (exit={p.returncode}); see stderr above")
    print(f"built {binary} in {dt:.1f}s")
    return binary


def hf_download(repo_id: str, dest: Path, patterns):
    from huggingface_hub import snapshot_download
    hr(f"downloading {repo_id} -> {dest}")
    t0 = time.time()
    path = snapshot_download(repo_id=repo_id, local_dir=str(dest), allow_patterns=patterns)
    print(f"downloaded to {path} in {time.time() - t0:.1f}s")
    run(["bash", "-c", f"du -sh {dest}; ls -la {dest}"])
    return Path(path)


def download_and_merge_sharded(repo_id: str, dest: Path, out_file: Path):
    """Fetch a sharded HF checkpoint's small metadata files, then download
    and merge shards ONE AT A TIME, deleting each shard immediately after
    its tensor bytes are copied into out_file. This bounds peak
    /kaggle/working disk usage to roughly (one shard) + (merged-so-far),
    instead of (all shards) + (merged file) simultaneously — the latter is
    what filled the 20 GB /kaggle/working disk on kernel v1 (4 shards,
    ~14.2 GiB total, downloaded up front via snapshot_download, then the
    merge tried to write a second ~14.2 GiB file and hit ENOSPC). This is a
    disk-space fix only; it changes nothing about how cis2_ref itself
    reads/loads the resulting single model.safetensors file, so a later
    OOM inside cis2_ref is still real engine-memory evidence, not an
    artifact of this staging step.
    """
    from huggingface_hub import hf_hub_download

    hr(f"downloading metadata for {repo_id} -> {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    for fname in ["config.json", "tokenizer.json", "model.safetensors.index.json"]:
        p = hf_hub_download(repo_id=repo_id, filename=fname, local_dir=str(dest))
        print(f"  fetched {p}")

    index_path = dest / "model.safetensors.index.json"
    weight_map = json.loads(index_path.read_text())["weight_map"]
    shard_names = sorted(set(weight_map.values()))
    tensor_names = [n for n in weight_map if n != "__metadata__"]

    hr(f"merging {len(shard_names)} shards one at a time -> {out_file}")
    t0 = time.time()

    # Pass 1: fetch each shard just long enough to read its own safetensors
    # header (tiny), so we can compute the merged tensor layout up front.
    shard_local_headers = {}
    for name in shard_names:
        p = Path(hf_hub_download(repo_id=repo_id, filename=name, local_dir=str(dest)))
        with open(p, "rb") as fh:
            hlen = struct.unpack("<Q", fh.read(8))[0]
            header = json.loads(fh.read(hlen))
        shard_local_headers[name] = (header, 8 + hlen)
        # leave the file on disk; pass 2 (below) consumes it in shard order
        # and deletes it right after, so at most one extra shard is ever
        # resident beyond the one currently being merged.

    # cis3-0m FIX: the merged header's data_offsets are assigned in the order
    # tensors are written.  Pass 2 writes data grouped by (sorted) shard, so
    # the header MUST be built in that same shard-grouped order.  The old code
    # iterated weight_map (index.json) order here, which for Qwen2-7B
    # interleaves shards (lm_head.weight from shard 4 comes first), so 338 of
    # 339 tensors were mislabelled in the merged file.  See
    # tests/kaggle/runs/2026-09-19-cis3-0m-mergebug.md.
    write_order = [n for s in shard_names for n in tensor_names if weight_map[n] == s]
    assert sorted(write_order) == sorted(tensor_names)
    merged_header = {}
    tensor_plan_by_shard = {name: [] for name in shard_names}
    offset = 0
    for name in write_order:
        shard_name = weight_map[name]
        header, data_start = shard_local_headers[shard_name]
        info = header[name]
        start, end = info["data_offsets"]
        size = end - start
        merged_header[name] = {
            "dtype": info["dtype"],
            "shape": info["shape"],
            "data_offsets": [offset, offset + size],
        }
        tensor_plan_by_shard[shard_name].append((data_start + start, size))
        offset += size

    header_bytes = json.dumps(merged_header).encode("utf-8")
    pad = (-len(header_bytes)) % 8
    header_bytes += b" " * pad

    with open(out_file, "wb") as out:
        out.write(struct.pack("<Q", len(header_bytes)))
        out.write(header_bytes)
        for shard_name in shard_names:
            shard_path = dest / shard_name
            with open(shard_path, "rb") as fh:
                for data_offset, size in tensor_plan_by_shard[shard_name]:
                    fh.seek(data_offset)
                    remaining = size
                    while remaining > 0:
                        chunk = fh.read(min(1 << 20, remaining))
                        if not chunk:
                            raise SystemExit(f"short read merging {shard_name} at offset {data_offset}")
                        out.write(chunk)
                        remaining -= len(chunk)
            shard_path.unlink()  # free disk before fetching/merging the next shard
            run(["bash", "-c", f"df -h /kaggle/working"])

    print(f"merged {len(tensor_names)} tensors, {offset} bytes, in {time.time() - t0:.1f}s")
    # cis3-0m: self-check the merged header against every shard header (offsets only)
    _chk = json.loads(open(out_file, "rb").read(8 + struct.unpack("<Q", open(out_file, "rb").read(8))[0])[8:])
    _pos = 0
    for _s in shard_names:
        for _n in [n for n in tensor_names if weight_map[n] == _s]:
            _b, _e = _chk[_n]["data_offsets"]
            assert _b == _pos, f"merged header offset mismatch for {_n}: {_b} != {_pos}"
            _pos = _e
    print(f"merged header self-check OK: {len(_chk)} tensors contiguous in write order")
    print(f"merge peak RSS so far: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024} MB")
    return dest


def stage_weights_dir(model_dl_dir: Path, weights_dir: Path, merged_file: Path = None):
    weights_dir.mkdir(parents=True, exist_ok=True)
    for f in ["config.json", "tokenizer.json"]:
        run(["cp", "-L", str(model_dl_dir / f), str(weights_dir / f)])
    if merged_file is not None:
        run(["ln", "-sf", str(merged_file), str(weights_dir / "model.safetensors")])
    else:
        run(["cp", "-L", str(model_dl_dir / "model.safetensors"), str(weights_dir / "model.safetensors")])


def run_cis2_ref(binary: Path, weights_dir: Path, gen_toks: int, label: str, layer_digests: bool = False):
    """Runs cis2_ref under `/usr/bin/time -v` (captures peak RSS / VmHWM
    of the child directly, independent of what else has run in this
    kernel), returns (CompletedProcess, elapsed, digest_or_None,
    killed_by_signal_or_None, peak_rss_kb_or_None). Never raises on
    OOM-kill: a negative returncode from subprocess means the child was
    killed by that signal (e.g. -9 == SIGKILL, the Linux OOM killer's
    usual weapon). Note: if the OOM killer fires, `time -v`'s own summary
    line is often not printed (the child dies before `time` can report),
    so peak_rss may be None on a kill; the cgroup memory.events dump below
    still shows oom_kill=1 in that case."""
    inner = [str(binary), "--weights-dir", str(weights_dir), "--gen-toks", str(gen_toks)]
    if layer_digests:
        inner = inner + ["--layer-digests"]
    has_time_v = subprocess.run(["bash", "-c", "command -v /usr/bin/time"],
                                 capture_output=True, text=True).returncode == 0
    cmd = (["/usr/bin/time", "-v"] + inner) if has_time_v else inner
    hr(f"{label}: running cis2_ref (time -v={has_time_v})")
    run(["bash", "-c", "free -g"])
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(weights_dir.parent))
    dt = time.time() - t0
    run(["bash", "-c", "free -g"])
    print(p.stdout)
    print(p.stderr, file=sys.stderr)
    print(f"---- {label}: exit={p.returncode} elapsed={dt:.1f}s")
    digest = None
    for line in p.stdout.splitlines():
        if line.startswith("CIS2_REF"):
            for tok in line.split():
                if tok.startswith("digest="):
                    digest = tok.split("=", 1)[1]
    peak_rss_kb = None
    for line in p.stderr.splitlines():
        if "Maximum resident set size" in line:
            try:
                peak_rss_kb = int(line.strip().split(":")[-1].strip())
            except ValueError:
                pass
    if peak_rss_kb is not None:
        print(f"---- {label}: peak RSS (time -v) = {peak_rss_kb} KB = {peak_rss_kb / 1024 / 1024:.2f} GB")
    else:
        # fallback: RUSAGE_CHILDREN is a running max across all reaped
        # children so far in this process, not just this one invocation,
        # but is still an honest lower bound if `time -v` was unavailable
        # or the child was killed before it could report.
        rc = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        print(f"---- {label}: peak RSS (time -v) unavailable; "
              f"RUSAGE_CHILDREN running max so far = {rc} KB = {rc / 1024 / 1024:.2f} GB "
              f"(includes prior children, not just this one)")
    killed = -p.returncode if p.returncode is not None and p.returncode < 0 else None
    if killed:
        print(f"---- {label}: PROCESS KILLED BY SIGNAL {killed} (likely OOM if {killed}==9)")
    # best-effort OOM evidence from dmesg / cgroup memory events (may be
    # unavailable/unreadable inside the Kaggle container; report either way)
    for oom_cmd in (["dmesg"], ["cat", "/sys/fs/cgroup/memory.events"],
                    ["cat", "/sys/fs/cgroup/memory/memory.oom_control"]):
        op = subprocess.run(oom_cmd, capture_output=True, text=True)
        tail = "\n".join(op.stdout.splitlines()[-15:]) if op.stdout else "(no output)"
        print(f"---- {label}: {' '.join(oom_cmd)} (rc={op.returncode}):\n{tail}")
    return p, dt, digest, killed, peak_rss_kb


def main():
    hr("environment")
    run(["bash", "-c", "free -h; nproc; uname -a; df -h /kaggle/working; lscpu | grep -i flags | tr \" \" \"\\n\" | grep -Ei \"^(avx2|avx512|fma)\" | sort -u; echo ENGINE_COMMIT=c0a2c346430c34dd54c9c0adc78829beb8755d32"])

    engine_src = find_engine_src()
    install_rust()
    binary = build_engine(engine_src)

    results = {}

    # ---- 7B attempt ----
    hr("PHASE 1: Qwen/Qwen2-7B attempt")
    merged = WORK / "hf" / "qwen2-7b-merged.safetensors"
    q7_dl = download_and_merge_sharded("Qwen/Qwen2-7B", WORK / "hf" / "qwen2-7b", merged)
    q7_weights = WORK / "weights_qwen2_7b"
    stage_weights_dir(q7_dl, q7_weights, merged_file=merged)
    p7, dt7, digest7, killed7, peak7_kb = run_cis2_ref(binary, q7_weights, GEN_TOKS_7B, "7B", layer_digests=True)
    results["7b"] = {
        "returncode": p7.returncode,
        "elapsed_s": dt7,
        "digest": digest7,
        "killed_by_signal": killed7,
        "peak_rss_kb": peak7_kb,
        "peak_rss_gb": (peak7_kb / 1024 / 1024) if peak7_kb else None,
        "stdout_tail": "\n".join(p7.stdout.splitlines()[-40:]),
        "stderr_tail": "\n".join(p7.stderr.splitlines()[-40:]),
    }

    # Free the 7B merged weights (~14 GiB) before phase 2 so the 1.5B
    # download + cis2_ref's own f32 widening have headroom on the 20 GB
    # /kaggle/working disk. Deleting this after the 7B run (not before) is
    # what let kernel v1 hit ENOSPC during the 7B merge itself; this is a
    # disk-space fix, unrelated to whatever cis2_ref reports for the 7B
    # attempt above.
    run(["bash", "-c", f"rm -rf {WORK / 'hf' / 'qwen2-7b'} {merged}; df -h /kaggle/working"])

    # ---- 1.5B x2 ----
    hr("PHASE 2: Qwen/Qwen2-1.5B, run twice")
    q15_dl = hf_download(
        "Qwen/Qwen2-1.5B",
        WORK / "hf" / "qwen2-1.5b",
        patterns=["config.json", "tokenizer.json", "model.safetensors"],
    )
    q15_weights = WORK / "weights_qwen2_1_5b"
    stage_weights_dir(q15_dl, q15_weights, merged_file=None)

    p15a, dt15a, digest15a, killed15a, peak15a_kb = run_cis2_ref(binary, q15_weights, GEN_TOKS_1B, "1.5B run1")
    p15b, dt15b, digest15b, killed15b, peak15b_kb = run_cis2_ref(binary, q15_weights, GEN_TOKS_1B, "1.5B run2")
    match = (digest15a is not None) and (digest15a == digest15b)
    KNOWN_1_5B_DIGEST = "9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8"
    matches_llm4 = (digest15a == KNOWN_1_5B_DIGEST)
    results["1_5b_run1"] = {"returncode": p15a.returncode, "elapsed_s": dt15a, "digest": digest15a,
                             "peak_rss_kb": peak15a_kb}
    results["1_5b_run2"] = {"returncode": p15b.returncode, "elapsed_s": dt15b, "digest": digest15b,
                             "peak_rss_kb": peak15b_kb}
    results["1_5b_match"] = match
    results["1_5b_matches_llm4_known_digest"] = matches_llm4
    results["1_5b_known_digest_llm4"] = KNOWN_1_5B_DIGEST

    hr("SUMMARY")
    print(json.dumps(results, indent=2, default=str))
    (WORK / "llm5b_results.json").write_text(json.dumps(results, indent=2, default=str))

    print(f"\n7B outcome: returncode={p7.returncode} killed_by_signal={killed7} digest={digest7} "
          f"peak_rss_gb={results['7b']['peak_rss_gb']}")
    print(f"1.5B run1 digest: {digest15a}")
    print(f"1.5B run2 digest: {digest15b}")
    print(f"1.5B digests match (run1 vs run2): {match}")
    print(f"1.5B digest matches LLM-4 known digest ({KNOWN_1_5B_DIGEST}): {matches_llm4}")


if __name__ == "__main__":
    main()
