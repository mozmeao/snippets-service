#!/bin/bash

TDIR=`mktemp -d`
virtualenv $TDIR
. $TDIR/bin/activate

cd service_tests
pip install -r requirements.txt
py.test
