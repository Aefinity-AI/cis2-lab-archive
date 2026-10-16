#!/usr/bin/env -S python3 -I
"""w6: build the Part B position list from the sv-5d windows file.
Takes windows in file order until N positions are reached (last window cut to
fit), writes one window per line (token ids only), prints counts and sha256.
usage: make_windows.py WINDOWS_JSONL N OUT_TXT"""
import hashlib, json, sys
src, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
raw = open(src, "rb").read()
sha = hashlib.sha256(raw).hexdigest()
PIN = "20c94006e05d6b86e52cf92443bc3118cc8c3c2c70cb98c2671823f7b5dafe61"
if sha != PIN:
    sys.exit("windows file sha256 %s differs from pin %s" % (sha, PIN))
tot = 0
nw = 0
with open(out, "w") as f:
    for line in raw.decode().splitlines():
        ids = json.loads(line)["ids"]
        take = ids[: n - tot]
        f.write(" ".join(map(str, take)) + "\n")
        tot += len(take)
        nw += 1
        if tot >= n:
            break
if tot < n:
    sys.exit("windows file too short")
print("windows=%d positions=%d windows_src_sha256=%s out_sha256=%s" % (
    nw, tot, sha, hashlib.sha256(open(out, "rb").read()).hexdigest()))
