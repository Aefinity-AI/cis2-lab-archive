#!/usr/bin/env python3
"""cis3-0k: diff LAYER_DIGEST lines between box1 raw log and Kaggle raw log."""
import re
import sys

BOX1_LOG = "box1-7b-layerdigests.log"
KAGGLE_LOG = "cis3-0k-plain.log"

LAYER_RE = re.compile(r"^LAYER_DIGEST (\S+) ([0-9a-f]+)$")


def extract_layers(path):
    out = {}
    order = []
    with open(path, "r", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            m = LAYER_RE.match(line.strip())
            if m:
                label, digest = m.group(1), m.group(2)
                if label not in out:
                    order.append(label)
                out[label] = digest
    return out, order


def main():
    box1, box1_order = extract_layers(BOX1_LOG)
    kaggle, kaggle_order = extract_layers(KAGGLE_LOG)

    print(f"box1 LAYER_DIGEST count: {len(box1_order)}")
    print(f"kaggle LAYER_DIGEST count: {len(kaggle_order)}")

    if box1_order != kaggle_order:
        print("WARNING: label order/set differs between logs")
        print("box1 order:", box1_order)
        print("kaggle order:", kaggle_order)

    all_labels = box1_order if box1_order == kaggle_order else sorted(set(box1_order) | set(kaggle_order))

    first_diverge = None
    print(f"\n{'label':<14} {'status':<6} box1_digest / kaggle_digest")
    print("-" * 100)
    for label in all_labels:
        b = box1.get(label, "<missing>")
        k = kaggle.get(label, "<missing>")
        status = "MATCH" if b == k else "DIFF"
        if status == "DIFF" and first_diverge is None:
            first_diverge = label
        print(f"{label:<14} {status:<6} box1={b}")
        print(f"{'':<14} {'':<6} kagl={k}")

    print("\nFIRST_DIVERGING_LABEL:", first_diverge if first_diverge else "NONE (ALL MATCH)")


if __name__ == "__main__":
    sys.exit(main())
