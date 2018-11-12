# snippets service

[![What's Deployed?](https://img.shields.io/badge/What's_Deployed-%3F-yellow.svg)](https://whatsdeployed.io/s-088) [![Documentation RTFM](https://img.shields.io/badge/Documentation-RTFM-blue.svg)](http://abouthome-snippets-service.readthedocs.org/)

The root of all messaging.

## Develop using Docker

0. Make sure you have [docker](https://docker.io) and [docker-compose](https://github.com/docker/compose)
1. `docker-compose up`
2. `docker-compose run web bash`
3. `python manage.py createsuperuser` (enter any user/email/pass you wish)
4. Navigate to https://localhost:8443/admin and log in with the admin account created in step #4. See an TLS Security Exception? Go to [TLS Certifcates](#tls-certificates) section.


## TLS Certificates

Firefox communicates with the snippets service only over secure HTTPS
connections. For development, the `runserver_plus` command as executed in
[`./bin/run-dev.sh`](https://github.com/mozmeao/snippets-service/blob/master/bin/run-dev.sh)
generates and uses a self-signed certificate.

You'll need to permanently accept the certificate, to allow Firefox to fetch
Snippets from your development environment.

## Run the tests

 `$ ./manage.py test --parallel`


## Install Therapist

[Therapist](https://github.com/rehandalal/therapist) is a smart pre-commit hook
for git to ensure that committed code has been properly linted.

Install the hooks by running:

 `$ therapist install`
