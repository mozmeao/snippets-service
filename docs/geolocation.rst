GeoLocation
===========

Some snippets target specific countries. For example a snippet about a
greek national holiday would target only browsers requesting snippets
from Greece.

To preserve user's privacy the geolocation happens on the browser
level and not on the service level. Snippet bundles contain a list of
targeted countries among the actual snippet data, the snippet weight
and other info.

The Browser pings a geolocation service to convert it's IP to a
country code. Upon successful request the result is cached for 30
days. Thus if a user travels from Greece to Italy for a week snippets
targeting Greece will be shown while the user is in Italy.

Currently browsers in the release channel ping a Mozilla owned service
called `GeoDude`_. Browsers is other channels (beta, aurora,
nightly) ping the new service offered by `Mozilla Location Service`_
(MLS).

The GeoTargeting code is part of the `JS included in the snippet bundle`_
and it's managed from the snippets service itself. It is not part of
Firefox.


.. _GeoDude: https://github.com/mozilla/geodude
.. _Mozilla Location Service: https://location.services.mozilla.com/
.. _JS included in the snippet bundle: https://github.com/mozilla/snippets-service/blob/master/snippets/base/templates/base/includes/snippet_js.html
