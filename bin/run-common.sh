#!/bin/bash

ENABLE_ADMIN=$(echo "$ENABLE_ADMIN" | tr '[:upper:]' '[:lower:]')

if [[ "$ENABLE_ADMIN" != "true" ]]; then
    python manage.py migrate --noinput
fi
