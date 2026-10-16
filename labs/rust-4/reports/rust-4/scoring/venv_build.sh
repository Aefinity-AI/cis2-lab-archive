#!/usr/bin/env bash
set -eu
cd ~/scratch-score/rust4
rm -rf venv
python3 -m venv venv
venv/bin/pip install --no-index --find-links <home>/feed-payload/rust4/p/wheelhouse --require-hashes --disable-pip-version-check -q -r <home>/feed-payload/rust4/p/requirements.lock
echo INSTALL_RC=$?
