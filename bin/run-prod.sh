#!/bin/sh

./bin/run-common.sh

exec gunicorn snippets.wsgi.app --config snippets/wsgi/config.py
