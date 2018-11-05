#!/bin/sh

urlwait
./bin/run-common.sh
./manage.py runserver_plus --cert-file .runserver-ssl.crt --extra-file .env 0.0.0.0:8443
