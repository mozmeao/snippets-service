# 5. Frequency Capping

Date: 2020-01-15

## Status

Accepted

## Context

Frequency Capping allows Content Managers to limit the number of
impressions or interactions users have with content. Is a widely
available tool in Publishing Platforms.

It's usually developed on the server side where the system can decide
how many times to serve the content to the requesting users which we
call "Global Frequency Capping". Additionally the system may be able
to limit the number of impressions per user which we call "Local" or
"User Frequency Capping".

For example a Content Piece can be set to 1,000,000 Global Impressions
and 1 Impression per User, thus indirectly driving 1,000,000 different
users to this Content.

This functionality has been lacking from the Snippet Service due to
technical limitations imposed by the way metrics were collected and
content selection was handled on the client side. The latest
developments in Firefox Messaging Center and the Firefox Telemetry
Pipeline unblock this capability. [0]


## Decision

We decide to implement the Frequency Capping functionality into our
platform to allow Content Managers to limit the number of Impressions,
Clicks and Blocks per Job.

Local or User Frequency Capping will be handled on the Browser level
by the Firefox Messaging Platform. The later supports only Impression
Frequency Capping.

The Snippets Service will provide an interface (UI) for the Content
Managers to set upper limits on the number of Impressions a Job gets
per Hour, Day, Week, Fortnight, Month or for the complete Browser
Profile Lifetime. This information is included in the JSON generated
for each Job.

For Global Frequency Capping the Snippets Service will provide an
interface (UI) for the Content Managers to set the limits on total
worldwide number of Impressions, Clicks and Blocks per Job.

Snippets Service will query Mozilla's Redash for Telemetry data every
ten minutes and will fetch current impressions, clicks, blocks for
each Job with set limits.

When the reported numbers exceed the set limits then, the Job will be
marked COMPLETE and will be pulled out of the Bundles on the next run
of `update_jobs` cron job.

The Frequency Capping functionality is additional to the Date
Publishing controls, therefore a Job can end on a specific Date and
Time or when its Global Frequency Capping Limits are met.


### Monitoring and Handling of Errors

Since Global Frequency Capping depends on an external system for
Metrics (Redash / Telemetry) it is possible that the latest numbers are
not always available to the Snippets Service to make a decision. Such
cases include scheduled or unplanned service interruptions or network
errors.

In co-ordination with Snippet Content Owner we decided that for cases
where the Snippets Service cannot get the latest numbers for more than
24 hours, Jobs with Global Frequency Capping will get canceled. The
cancellation reason will state that the Jobs where prematurely
terminated due to missing metrics.

The cron job responsible for fetching the Data from Telemetry is
monitored by a Dead Man's Snitch.


## Consequences

With this ADR implemented Snippets Service supports Global and Local
Frequency Capping.

Current implementation of Global Frequency Capping does go above any
set limits due to:

 1. The four hour interval that Browsers update Bundles.
 2. The time needed by Browsers to report to Telemetry and the
    Telemetry Pipeline to make data available for consumption by the
    Snippets Service which is calculated to be about 30'.

This was discussed with Snippet Content Managers and we agreed that a
5%, 10% or even 20% excess above the set limits is acceptable for now.
This number may be re-evaluated when Content Managers switch to using
more this functionality instead of setting Start and End Datetime
limits.

The excess percentage can be limited by bringing down the interval the
Browsers update. Browsers can request Bundles every one hour without
significant changes in the infrastructure supporting Snippets Service
but with an additional cost for more CDN traffic and more active
Kubernetes pods. Those changes will be decided in co-ordination with
the Content Managers when requested.

Local capping is not affected by the limitations above and should not
go above set limits.


[0] Related Snippets Telemetry Bug: https://bugzilla.mozilla.org/show_bug.cgi?id=1433214
