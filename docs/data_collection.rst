Data Collection
===============

This document describes how snippets data is collected, stored and used.

Snippets follows Mozilla's established best practices for data collection
and storage of personally identifiable information.

Data Collection: Impressions
----------------------------

Immpression data is sampled at a rate of ~10%. For a tracked impression the following
information is sent to the stats server.

.. code-block:: json

    snippet_name
    locale
    country
    metric
    campaign


This information is sent via ajax request to https://snippets-stats.mozilla.org/ . Metric for the above
will always be `impression`.


Data Collection: Clicks & Events
--------------------------------

Snippets may contain a link to a Mozilla destination. When they do the link may be constructed
with UTM parameters that are used in Google Analytics. The site they land on (example: mozilla.org)
reports these parameters to Google.

This link when clicked sends the information to Google. An example links is:

.. code-block:: json

    https://www.mozilla.org/firefox/sync/?utm_source=desktop-snippet&utm_medium=snippet&utm_content=sync&utm_term=5274&utm_campaign=desktop&sample_rate=0.1&snippet_name=5274

Snippets may also send specific events to our data warehouse. An example use is capturing that a
user clicked "play" on a video. The format of this request is the same as for impressions,
the `metric` value being the custom event. This data is sampled at ~0.1% (confirm).


.. note:: The following is proposed:

All href's contained in a Snippet will automatically send tracking information
to our data warehouse when cicked. This information is not sampled and will contain the
following data:

.. code-block:: json

    snippet_name
    locale
    country
    metric
    campaign


Metric for the above will always be `click`.

.. note:: End of proposal.

Data Storage & Processing
-------------------------

Impression & Event data is stored in our "data warehouse". Tableau is used as a graphical front-end
for the data, but it does not store the data.

The data warehouse stores the following:

.. code-block:: json

    date
    user agent family
    user agent major version
    OS family
    country code
    snippet ID
    locale
    metric
    user_country
    impression count

Impression count is the aggregated count of all the records that matched all the other fields.

In addition to the above the logs from snippets-stats contain IP addresses. The PII
for this data is stored according to the following rules:

1. IP address is kept for min 15 days max 60 days
2. Daily IP address is anonymized to countries, this is kept for 60 days


Google Analytics
----------------

Snippets and about:home do not report to Google Analytics directly. No JS from Google Analytics
is loaded.
