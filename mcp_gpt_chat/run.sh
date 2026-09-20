#!/bin/sh
set -eu

exec gunicorn \
  --bind 0.0.0.0:8099 \
  --workers 1 \
  --timeout 300 \
  app:app