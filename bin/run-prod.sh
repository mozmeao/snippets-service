#!/bin/sh

./bin/run-common.sh

echo "$GIT_SHA" > static/revision.txt

exec gunicorn snippets.wsgi.app --config snippets/wsgi/config.py
