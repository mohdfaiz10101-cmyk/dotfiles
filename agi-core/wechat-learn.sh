#!/usr/bin/env bash
# wechat-learn wrapper — 通过 nix-shell 提供 pycryptodome
exec nix-shell -p python3Packages.pycryptodome --run "python3 /home/charlie/agi/wechat-learn.py $*"
