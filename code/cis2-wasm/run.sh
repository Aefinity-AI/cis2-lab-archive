#!/usr/bin/env bash
# usage: run.sh <label> <dir> <idsfile> <toks> <expected>
set -u; cd "$(dirname "$0")"
s=$(date +%s.%N)
systemd-run --user --scope -q -p MemoryMax=2500M -p CPUWeight=60 nice -n 10 node cis2_host_node.js --weights-dir "$2/weights" --ids "$3" --gen-toks "$4" >runs/$1.out 2>runs/$1.err; rc=$?
e=$(date +%s.%N)
dg=$(grep '^CIS2_REF' runs/$1.out | sed 's/.*digest=\([0-9a-f]*\).*/\1/')
v=DIVERGE; [ "$dg" = "$5" ] && v=MATCH
printf "%s rc=%s wall=%.1fs digest=%s expected=%s %s\n" "$1" "$rc" "$(echo "$e-$s"|bc)" "${dg:-none}" "$5" "$v" | tee -a runs/summary.txt
