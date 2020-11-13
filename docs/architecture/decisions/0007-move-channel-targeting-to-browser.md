# 7. Move Channel targeting to browser.

Date: 2020-11-12

## Status

Accepted

## Context

We want to be able to create more complex Targets, specifically targets that
will evaluate to true for Profiles older than X weeks with X being different for
each channel.

The requirement comes from an initiative to reduce the number of active Jobs per week and thus reduce the programming and analyzing time required. With this change we will be able to schedule one Job for multiple channels while maintaining different targeting for each channel.


## Decision

We decide to move Channel targeting from the server to the browser. To accomplish this we will take advantage of `browser.update.channel` JEXL attribute to target snippets based on channel and remove any server side code that does channel targeting.

We will generate one bundle for each locale, instead of one bundle for each locale, channel combination. 

This ADR replaces 0006 since all Jobs for locale will be included in all channels.


## Consequences

CDN traffic is expected to increase since bundles are going to include Job from all channels of a locale. The increase is not expected to be significant because traditionally most Jobs are on Release channel and it's the Release that generates from of the traffic.
