#!/usr/bin/env bash
# rust-4 job on box4 (payload dest <home>/rust4). Feed with no real CPUQuota (100% x cores) and MemoryMax per the bar. All phases: install, m2, m3.
# run.py measures an idle baseline of the foreign load before anything is timed (rust-1 rule R1, same formula and constants) and voids a repetition with more other load than baseline + margin.
export R4_FROZEN_PAYLOAD_SHA256=ea2b972e09cf0ab84f26e0ff0462c7aff2dc82c01a265a83caa1ac2132d14b85
exec python3 $HOME/rust4/run.py box4
