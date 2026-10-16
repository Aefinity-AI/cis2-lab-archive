#!/usr/bin/env bash
# rust-5 timing job on box2 (payload dest <home>/rust5; payload ~/feed-payload/rust5).
# Feed with no real CPUQuota (>= 100% x cores) and MemoryMax per the bar. run.sh exits with "RESULT: FAIL host busy" if another feeder job runs on the host.
exec bash $HOME/rust5/run.sh box2
