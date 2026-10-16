#!/usr/bin/env bash
# rust-4 job on box2 (payload dest <home>/rust4). Feed with no real CPUQuota (100% x cores) and MemoryMax per the bar. All phases: install, m2, m3.
# run.py measures an idle baseline of the foreign load before anything is timed (rust-1 rule R1, same formula and constants) and voids a repetition with more other load than baseline + margin.
export R4_FROZEN_PAYLOAD_SHA256=697610dd05e120a3cffceef1cc483aa4cb384676a06294201dfe763b63d67e94
exec python3 $HOME/rust4/run.py box2
