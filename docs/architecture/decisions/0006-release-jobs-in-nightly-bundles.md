# 6. Release Jobs in Nightly Bundles

Date: 2020-03-31

## Status

Accepted

## Context

The JEXL evaluation engine in Firefox Message Router needs to be
tested and performance measured. The best test input are Release Jobs
tested against the current development version, i.e. Nightly.


## Decision

Jobs published in Release Bundles for each locale will be also
included in the Nightly Bundles. To avoid actually displaying those to
Nightly users, their JEXL experssions will be appended with the
expression ` && false` to force them to always evaluate to false.

Firefox Messaging team will develop tests and automation to measure
performance and catch regressions.

This functionality is controlled by the `NIGHTLY_INCLUDES_RELEASE`
enviroment variable of snippets-service.


## Consequences

Nightly Bundles increase in size but, due to the small -relative to
Release- number of Nightly users this will not have significant impact
to CDN costs.


## Links

 - https://github.com/mozmeao/snippets-service/issues/1308
