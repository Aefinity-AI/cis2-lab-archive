"""cis3-0n: byte-identical merge, cross-host 7B witness .

Supersedes cis3-0m's merge (which fixed the tensor/offset mislabelling but
still produced a *different* weights_sha256 than box1, because the merged
safetensors HEADER was serialised in a different key order and with
different json.dumps formatting than box1's scripts/merge_shards.py). This
kernel ports merge_shards.py's header-construction line-for-line:
  - entries are built by iterating shards in sorted(shard filename) order,
    and WITHIN each shard iterating that shard's OWN header dict in its own
    on-disk key order (hdr.items()) -- NOT filtered from index.json's
    weight_map order (cis3-0m's bug: index.json key order is not guaranteed
    to equal a shard's own internal header order).
  - merged header starts with {"__metadata__": {"format": "pt"}} as the
    first key (merge_shards.py line 37), then one entry per tensor in
    write order.
  - header bytes = json.dumps(merged, separators=(",", ":")).encode("utf-8")
    (no sort_keys, default ensure_ascii=True) -- cis3-0m omitted the
    separators arg entirely (default has spaces), which alone breaks byte
    equality.
  - padding: hb += b" " * ((8 - len(hb) % 8) % 8), 8-byte align.
Before running cis2_ref, this kernel computes sha256 of the merged file and
compares it to box1's weights_sha256 (13200c88e7482d83ed9a2bb23a01b515e46
663ab57dba853389587d4173dcfa3); on mismatch it prints MERGE_BYTES_MISMATCH
and exits WITHOUT running the engine, per the cis3-brief hard rule (never
paper over a mismatch by rerunning weights through a numerically-live
engine when the artefact itself is already known to differ).

Original LLM-5b docstring (recipe lineage), preserved for context:
LLM-5b Kaggle scale leg: acceptance test for cis2-fp PR #12
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
import hashlib
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


EXPECTED_MERGED_SHA256 = "13200c88e7482d83ed9a2bb23a01b515e46663ab57dba853389587d4173dcfa3"


def download_and_merge_sharded(repo_id: str, dest: Path, out_file: Path):
    """Fetch a sharded HF checkpoint's small metadata files, then download
    and merge shards, producing a merged model.safetensors that is
    BYTE-IDENTICAL to box1's scripts/merge_shards.py output (not just
    tensor-content-identical). This ports merge_shards.py line-for-line:

      for sh in sorted(shards):                 # merge_shards.py line 23-25
          hdr, ds = read_header(shard_path)      # merge_shards.py line 14-18
          for name, meta in hdr.items():          # <-- SHARD'S OWN header
              if name == "__metadata__": continue  #     key order, not
              entries.append((name, ..., sh, ds+b, ds+e))  # index.json order

      merged = {"__metadata__": {"format": "pt"}}  # merge_shards.py line 37
      for name, ... in entries:                     # insertion order == entries order
          merged[name] = {...}

      hb = json.dumps(merged, separators=(",", ":")).encode("utf-8")  # line 41
      hb += b" " * ((8 - len(hb) % 8) % 8)                             # line 42

    cis3-0m's bug: it built write_order by filtering weight_map (index.json)
    order per shard, which is NOT guaranteed to equal each shard's own
    internal header key order, and it called json.dumps() WITHOUT
    separators=(",", ":") (default has spaces after "," and ":"). Both
    differences change header bytes -> different weights_sha256 -> different
    witness, even with numerically-identical tensor bytes. See
    tests/kaggle/runs/2026-09-19-cis3-0m-witness-note.md.

    Disk-space handling (v1 -> v2 fix, unrelated to the byte-match logic
    above): v1 pre-downloaded all 4 shards in full just to read their
    headers, then only deleted them after the separate streaming pass
    finished -- peak disk = 4 shards + merged output resident at once,
    which exceeded /kaggle/working's 20GB and killed the run with
    OSError: [Errno 28] No space left on device before MERGED_SHA256 was
    ever computed (2026-09-19 v1 run, ~168s, see
    tests/kaggle/runs/2026-09-19-cis3-0n-kernel.log). v2: headers are read
    via a small ranged HTTP GET (no shard bytes downloaded for the header
    pass at all), and the streaming pass downloads, streams, and deletes
    exactly one shard at a time, so peak disk is ~1 shard + the growing
    merged output.
    """
    from huggingface_hub import hf_hub_download, hf_hub_url
    import requests

    hr(f"downloading metadata for {repo_id} -> {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    for fname in ["config.json", "tokenizer.json", "model.safetensors.index.json"]:
        p = hf_hub_download(repo_id=repo_id, filename=fname, local_dir=str(dest))
        print(f"  fetched {p}")

    index_path = dest / "model.safetensors.index.json"
    weight_map = json.loads(index_path.read_text())["weight_map"]
    shards = sorted(set(weight_map.values()))  # merge_shards.py line 23

    hr(f"reading headers for {len(shards)} shards via HTTP range GET (sorted shard order, no full download)")
    t0 = time.time()

    # cis3-0n disk-space fix: cis3-0n v1 pre-downloaded ALL shards fully in
    # this loop (to read their headers) and only deleted them AFTER the
    # later streaming loop finished -- peak disk = 4 full shards + the full
    # merged output resident at once (~30GB > /kaggle/working's 20GB),
    # which killed the run with OSError: [Errno 28] No space left on device
    # before MERGED_SHA256 was ever computed. Fix: read each shard's header
    # via a small ranged HTTP GET (headers are a few KB, not the whole
    # multi-GB shard) so no shard bytes are downloaded in this pass at all.
    entries = []
    RANGE_BYTES = 1 << 20  # 1 MiB is far more than any single shard's header
    for sh in shards:
        url = hf_hub_url(repo_id=repo_id, filename=sh)
        rng = RANGE_BYTES
        while True:
            resp = requests.get(url, headers={"Range": f"bytes=0-{rng - 1}"}, allow_redirects=True, timeout=60)
            resp.raise_for_status()
            data = resp.content
            if len(data) < 8:
                raise SystemExit(f"header range GET for {sh} returned only {len(data)} bytes")
            hlen = struct.unpack("<Q", data[:8])[0]
            if 8 + hlen <= len(data):
                break
            rng *= 4  # header bigger than the range fetched so far; widen and retry
        hdr = json.loads(data[8:8 + hlen].decode("utf-8"))
        ds = 8 + hlen  # merge_shards.py read_header() return: data_start offset
        for name, meta in hdr.items():  # <-- shard's OWN header key order
            if name == "__metadata__":
                continue
            if weight_map.get(name) != sh:
                raise SystemExit(f"index/shard mismatch for {name}: index says {weight_map.get(name)}, found in {sh}")
            b, e = meta["data_offsets"]
            entries.append((name, meta["dtype"], meta["shape"], sh, ds + b, ds + e))
        print(f"  {sh}: header read via range GET ({8 + hlen} bytes fetched, {len(hdr) - (1 if '__metadata__' in hdr else 0)} tensors)")
    if len(entries) != len(weight_map):
        raise SystemExit(f"tensor count mismatch: shards have {len(entries)}, index lists {len(weight_map)}")

    # merged header: tensors in entries order (shard order, then each
    # shard's own header order), contiguous data offsets. merge_shards.py
    # lines 36-40.
    merged, off = {"__metadata__": {"format": "pt"}}, 0
    for name, dtype, shape, sh, b, e in entries:
        merged[name] = {"dtype": dtype, "shape": shape, "data_offsets": [off, off + (e - b)]}
        off += e - b

    hb = json.dumps(merged, separators=(",", ":")).encode("utf-8")  # merge_shards.py line 41
    hb += b" " * ((8 - len(hb) % 8) % 8)  # merge_shards.py line 42, 8-byte align
    print(f"merged header: {len(entries)} tensors, header_json_len={len(hb)} bytes")
    print(f"merged header first 200 bytes: {hb[:200]!r}")

    hr(f"streaming {len(entries)} tensors -> {out_file} (merge_shards.py byte order)")
    h = hashlib.sha256()
    tmp = str(out_file) + ".part"
    with open(tmp, "wb") as fo:
        pre = struct.pack("<Q", len(hb)) + hb
        fo.write(pre)
        h.update(pre)
        cur = None
        for name, dtype, shape, sh, b, e in entries:
            if cur is None or cur[0] != sh:
                if cur:
                    cur[1].close()
                    Path(cur[2]).unlink(missing_ok=True)  # free disk before the next shard
                    print(f"shard {cur[0]}: streamed + deleted", flush=True)
                    run(["bash", "-c", "df -h /kaggle/working"])
                # download exactly one shard at a time (peak disk = 1 shard + growing merged file)
                t_dl = time.time()
                local = hf_hub_download(repo_id=repo_id, filename=sh, local_dir=str(dest))
                print(f"shard {sh}: downloaded in {time.time() - t_dl:.1f}s -> {local}; streaming", flush=True)
                cur = (sh, open(local, "rb"), local)
            f = cur[1]
            f.seek(b)
            left = e - b
            while left:
                buf = f.read(min(1 << 26, left))
                if not buf:
                    raise SystemExit(f"short read in {sh} at tensor {name}")
                fo.write(buf)
                h.update(buf)
                left -= len(buf)
        if cur:
            cur[1].close()
            Path(cur[2]).unlink(missing_ok=True)
            print(f"shard {cur[0]}: streamed + deleted", flush=True)
    os.replace(tmp, str(out_file))
    run(["bash", "-c", "df -h /kaggle/working"])

    size = os.path.getsize(out_file)
    merged_sha256 = h.hexdigest()
    print(f"merged {len(entries)} tensors -> {out_file} size={size} bytes in {time.time() - t0:.1f}s")
    print(f"MERGED_SHA256={merged_sha256}")
    print(f"merge peak RSS so far: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024} MB")

    # self-check: merged header offsets are contiguous in entries order
    _chk_hlen = struct.unpack("<Q", open(out_file, "rb").read(8))[0]
    with open(out_file, "rb") as _fh:
        _fh.seek(8)
        _chk = json.loads(_fh.read(_chk_hlen).decode("utf-8"))
    _pos = 0
    for name, dtype, shape, sh, b, e in entries:
        _b, _e = _chk[name]["data_offsets"]
        assert _b == _pos, f"merged header offset mismatch for {name}: {_b} != {_pos}"
        _pos = _e
    print(f"merged header self-check OK: {len(_chk) - 1} tensors contiguous in entries order")

    if merged_sha256 != EXPECTED_MERGED_SHA256:
        print(f"MERGE_BYTES_MISMATCH expected={EXPECTED_MERGED_SHA256} got={merged_sha256}")
        raise SystemExit("MERGE_BYTES_MISMATCH: merged file does not match box1's byte layout; "
                          "not running cis2_ref (see cis3-brief hard rule 3: never paper over a "
                          "mismatch by re-running a numerically-live engine on a known-divergent artefact).")
    print(f"MERGE_BYTES_MATCH: merged_sha256 == box1 weights_sha256 == {EXPECTED_MERGED_SHA256}")
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
