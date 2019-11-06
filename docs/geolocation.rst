GeoLocation
===========

Some snippets target specific countries. For example a snippet about a
greek national holiday would target only browsers requesting snippets
from Greece.

To preserve user's privacy the geolocation happens on the browser
level and not on the service level. Snippet bundles contain a list of
targeted countries among the actual snippet data, the snippet weight
and other info.

The Browser pings `Mozilla Location Service`_ (MLS) to convert it's IP
to a country code. Upon successful response the result is cached for 30
days. Thus if a user travels from Greece to Italy for a week snippets
targeting Greece will be shown while the user is in Italy.

For current Firefox versions the Geo-Targeting code is part of `Activity
Stream`_ as the rest of the decision engine.

For pre-Quantum versions the Geo-Targeting code is part of the `JS included in
the snippet bundle`_ and it's managed from the snippets service itself. It is
not part of Firefox.



.. _GeoDude: https://github.com/mozilla/geodude
.. _Mozilla Location Service: https://location.services.mozilla.com/
.. _JS included in the snippet bundle: https://github.com/mozilla/snippets-service/blob/master/snippets/base/templates/base/includes/snippet_js.html
.. _Activity Stream: https://github.com/mozilla/activity-stream/
