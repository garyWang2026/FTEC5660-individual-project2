#!/bin/zsh
cd "${0:A:h}" || exit 1
./.venv/bin/python reproduction/setup_key.py
read -k 1 "?Press any key to close this window..."
