# 2. Export ASRSnippet Metadata for Snippet Metrics Processing

Date: 2019-02-25

## Status

Accepted

## Context

Data Engineers are building performance dashboards for Snippets using the
metrics we collect from Firefox Telemetry. Telemetry pings include only basic
information about the Snippet, like Snippet ID.

For better to understand and more complete dashboards, we want to enhance the
Telemetry received information with more Snippet metadata, like campaign
information, included URL, main message used and others.

To achieve this we will export the metadata from the Snippets Service in a
machine readable format and make the file available in a Cloud Storage Provider.
Then Data Engineers will import the metadata and combine them Telemetry data in
unified dashboards.

GitHub Issue: [#887](https://github.com/mozmeao/snippets-service/issues/887)

## Decision

 - Export in CSV format.
 - Create a cron job to export and upload resulting file to S3.
 - The job will run daily, on early morning UTC hours.
 - The job will be monitored using Dead Man's Snitch and report to the usual
   notification channels that project developers follow.


## Consequences

### Risks:

 - Cron job failures will lead to outdated CSV which in turn will provide a
   lesser experience to the dashboard users. This behavior will only cause
   inconvenience and not data loss. The attached monitor will notify developers
   that something is broken.

 - The implemented export mechanism may need refinement as the number of
   Snippets to be exported grows. Failure to do so may result in excessive
   resource usage in the snippet-admin.cron pods.
