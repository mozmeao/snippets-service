#!/usr/bin/env bash
set -euo pipefail

gunicorn main:app --config config.py
