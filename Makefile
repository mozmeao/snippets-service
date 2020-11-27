DC = docker-compose

all: help

compile-requirements: requirements.txt
	${DC} run web pip-compile --generate-hashes --reuse-hashes > requirements.txt
	${DC} run web bash -c 'cd redirector && pip-compile --generate-hashes --reuse-hashes > requirements.txt'

build:
	${DC} build --pull --parallel $(app)

push:
	${DC} push $(app)

pull:
	${DC} pull $(app)

test: test-web test-redirector

test-web:
	${DC} run test-web ./manage.py test --parallel

test-redirector:
	${DC} run test-redirector pytest test.py

lint:
	${DC} run web flake8 snippets redirector

check-migrations:
	docker-compose run test-web bash -c './manage.py makemigrations  | grep "No changes detected"'

clean:
# Docker compose images
	${DC} rm
#	python related things
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
#	test related things
	-rm -f .coverage
#	docs files
	-rm -rf docs/_build/
#	state files
	-rm -f .make.*

djshell:
	${DC} run web ./manage.py shell_plus


help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  build                - build docker images for dev"
	@echo "  pull                 - pull the latest production images from Docker Hub"
	@echo "  compile-requirements - compile requirements.in to requirements.txt"
	@echo "  djshell                - open a bash shell in the running app"
	@echo "  clean                - remove all build, test, coverage and Python artifacts"
	@echo "  lint                 - check style with flake8, jshint, and stylelint"
	@echo "  test                 - run tests against local files"

.PHONY: all build push pull test test-web test-redirector lint check-migrations clean
