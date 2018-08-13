#!/bin/sh

urlwait
./bin/run-common.sh
./manage.py runserver 0.0.0.0:8000
