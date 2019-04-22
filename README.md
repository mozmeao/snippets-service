# snippets service

[![What's Deployed?](https://img.shields.io/badge/What's_Deployed-%3F-yellow.svg)](https://whatsdeployed.io/s-088) [![Documentation RTFM](https://img.shields.io/badge/Documentation-RTFM-blue.svg)](http://abouthome-snippets-service.readthedocs.org/)

The root of all messaging.

## Develop using Docker

One time setup of your environment and database:

0. Make sure you have [docker](https://docker.io) and [docker-compose](https://github.com/docker/compose)
1. `$ docker-compose run --service-ports web bash`
2. `[docker]$ ./manage.py update_product_details`
   -  If you get an error connecting to the database, you probably need to wait
      for a few seconds for MariaDB to initialize and then re-try the command.
3. `[docker]$ ./manage.py migrate`
4. `[docker]$ ./manage.py createsuperuser` (enter any user/email/pass you wish. Email is not required.)
5. `[docker]$ ./manage.py shell -c 'from snippets.base.util import *; create_countries(); create_locales();'`
   - Create a list of Countries and Locales from Product Details info.

Start the development server:

1. `[docker]$ ./bin/run-dev.sh`
2. Navigate to `https://localhost:8443/admin` and log in with the admin account created in step #4. See an TLS Security Exception? Go to [TLS Certifcates](#tls-certificates) section.

### A note about using `run` instead of `up`

`docker-compose run` is more suitable for development purposes since you get a
shell and from there you can run the webserver command. This way you can debug
using `set_trace()` or restart the server when things go bad. The trick here is
to use `--service-ports` flag to make docker compose map the required ports.

The project is configured for `docker-compose up` if that's your preference.


## TLS Certificates

Firefox communicates with the snippets service only over secure HTTPS
connections. For development, the `runserver_plus` command as executed in
[`./bin/run-dev.sh`](https://github.com/mozmeao/snippets-service/blob/master/bin/run-dev.sh)
generates and uses a self-signed certificate.

You'll need to permanently accept the certificate, to allow Firefox to fetch
Snippets from your development environment.

## Run the tests

 `$ ./manage.py test --parallel`


## Rebuild your Docker Compose Envinronment

To rebuild your docker compose environment, first remove current images and
containers and then run the `build` command.

```shell
$ docker-compose kill
$ docker-compose rm -f
$ docker-compose build

```


## Install Therapist

[Therapist](https://github.com/rehandalal/therapist) is a smart pre-commit hook
for git to ensure that committed code has been properly linted.

Install the hooks by running:

 `$ therapist install`
