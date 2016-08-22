#!/bin/sh

# install current version unless overridden by first command-line argument
VERSION=${1:-1.13.2}

# catch errors from here on out
set -e

# determine from whence to download the installer
PLATFORM=`uname | tr '[:upper:]' '[:lower:]'`
DEIS_INSTALLER=${DEIS_INSTALLER:-deis-cli-$VERSION-$PLATFORM-amd64.run}
DEIS_BASE_URL=${DEIS_BASE_URL:-https://s3-us-west-2.amazonaws.com/get-deis}
INSTALLER_URL=$DEIS_BASE_URL/$DEIS_INSTALLER

# download the installer archive to /tmp
curl -f -o /tmp/$DEIS_INSTALLER $INSTALLER_URL

# run the installer
sh /tmp/$DEIS_INSTALLER $INSTALLER_OPTS

# clean up after ourselves
rm -f /tmp/$DEIS_INSTALLER
