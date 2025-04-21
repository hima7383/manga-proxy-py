#!/usr/bin/env bash
# build.sh

# Install dependencies
pip install -r requirements.txt

# Install playwright browsers
playwright install --with-deps
