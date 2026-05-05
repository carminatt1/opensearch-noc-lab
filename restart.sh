#!/bin/bash
cd /home/carminatti/opensearch-lab
pkill -f forecasting.py || true
source .venv/bin/activate
nohup python3 scripts/forecasting.py > forecaster.log 2>&1 &
