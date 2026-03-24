#!/usr/bin/env bash

set -e

python3 -m venv venv

source venv/bin/activate

pip install .

sudo ln -s $PWD /opt/nvda_ticker
sudo ln -s $PWD/nvda-ticker.service /etc/systemd/system/nvda-ticker.service

sudo systemctl daemon-reload
sudo systemctl enable --now nvda-ticker.service