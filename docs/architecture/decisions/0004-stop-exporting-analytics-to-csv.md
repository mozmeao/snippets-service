# 4. Stop Exporting Analytics to CSV

Date: 2020-01-16

## Status

Accepted

## Context

As part of `2. Export ASRSnippet Metadata for Snippet Metrics
Processing` we started exporting Snippet Metadata to CSVs stored in
S3.

The Dashboards consuming the CSVs have been long decomissioned and
there's no other consumer of the data.


## Decision

We decide to stop exporting metadata to CSVs for Metrics Dashboards
and remove related code and exports.

## Consequences

No consequences to how Snippets Service operates. Metrics analysis and
Dashboards happens with Jupyter Notebooks currently.
