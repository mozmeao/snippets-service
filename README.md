# snippets service

[![What's Deployed?](https://img.shields.io/badge/What's_Deployed-%3F-yellow.svg)](https://whatsdeployed.io/s-088) [![Documentation RTFM](https://img.shields.io/badge/Documentation-RTFM-blue.svg)](http://abouthome-snippets-service.readthedocs.org/)

The root of all messaging.

## Develop using Docker

0. Make sure you have [docker](https://docker.io) and [docker-compose](https://github.com/docker/compose)
1. `docker-compose up`
2. `docker-compose run web bash`
3. `python manage.py migrate`
4. `python manage.py createsuperuser` (enter any user/email/pass you wish)
5. Navigate to https://localhost:8443/admin and log in with the admin account created in step #4



## Run the tests

 `$ ./manage.py test --parallel`


## Install Therapist

[Therapist](https://github.com/rehandalal/therapist) is a smart pre-commit hook
for git to ensure that committed code has been properly linted.

Install the hooks by running:

 `$ therapist install`
