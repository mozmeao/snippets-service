Data Collection
===============

The Snippets Service and the code that it embeds onto about:home collect data
about user interaction with snippets in order to help us determine the
effectiveness of certain types of snippets and measure whether a specific
snippet is successful. This document outlines the types of data we collect and
how it is handled.


Retrieving Snippets
-------------------

The :doc:`overview` document describes how Firefox retrieves snippets. The
actual URL that Firefox uses for fetching snippets can be found under the
`about:config`_ preference ``browser.aboutHomeSnippets.updateUrl`` and defaults
to::

   https://snippets.cdn.mozilla.net/%STARTPAGE_VERSION%/%NAME%/%VERSION%/%APPBUILDID%/%BUILD_TARGET%/%LOCALE%/%CHANNEL%/%OS_VERSION%/%DISTRIBUTION%/%DISTRIBUTION_VERSION%/

The names surrounded by ``%`` symbols are special values that Firefox replaces
with information about the user's browser.

``STARTPAGE_VERSION``
   A hard-coded number within Firefox specifying which version of about:home is
   retrieving snippets. We sometimes increase this when about:home changes in a
   way that may break certain snippets.

   Example: ``1``
``NAME``
   The name of the product being used.

   Example: ``Firefox``
``VERSION``
   The Firefox version number currently being used.

   Example: ``29.0.1``
``APPBUILDID``
   A string uniquely identifying the build of Firefox in use, usually in the
   form of the date the build occurred with a number appended.

   Example: ``2007083015``
``BUILD_TARGET``
   A string describing the platform and configuration used when building
   Firefox.

   Example: ``Darwin_x86-gcc3``
``LOCALE``
   The locale that the current Firefox was built for. We use this for showing
   snippets in different languages only to users who can read that language.

   Example: ``en-US``
``CHANNEL``
   The release channel for the current Firefox. This is typically one of
   ``release``, ``beta``, ``aurora``, or ``nightly``.

   Example: ``aurora``
``OS_VERSION``
   A string describing the operating system that this Firefox was built for.

   Example: ``Darwin%208.10.1``
``DISTRIBUTION``
   A string used to describe custom distributions of Firefox, such as when
   providing custom builds with partners. This is set to ``default`` for most
   instances of Firefox.

   Example: ``default``
``DISTRIBUTION_VERSION``
   Version of the customized distribution. This is also ``default`` for most
   instances of Firefox.

   Example: ``default``

.. _about:config: http://kb.mozillazine.org/About:config


Metrics
-------

Snippet code, which is executed on about:home, sends HTTP requests to a server
located at https://snippets-stats.moz.works and / or
https://snippets-stats.mozilla.org whenever an event occurs that we would like
to measure. These requests are sampled at a rate of 1%, meaning that only 1% of
the time an event occurs will a request be made.

Requests sent to snippets-stats.mozilla.org contain the following data (sent as
URL parameters in the query string) in addition to the normal data available
from an HTTP request:

Snippet Name
   Unique name referring to the snippet that was being viewed when the request
   was sent.
Locale
   The locale of the current Firefox instance (the same locale value described
   in the snippet URL from the previous section).
Country
   The country code corresponding to the country the user is currently located
   in. This is determined via the user's IP address and is cached locally within
   Firefox for 30 days. This value may be empty in cases where we can't retrieve
   the user's country.
Metric
   A string describing the type of event being measured, such as a snippet
   impression or a link click.
Campaign
   A string describing the snippet campaign this snippet is related to. We use
   this to help group metrics across multiple snippets related to a single
   campaign. This value may be empty.


Types of Metrics Gathered
-------------------------

The following is a list of the types of events that we collect data for as
described in the previous section:

Impressions
~~~~~~~~~~~

An impression is whenever a user is shown a specific snippet.

Snippet Clicks
~~~~~~~~~~~~~~

Whenever a link in a snippet is clicked, we trigger an event that notes which
particular link was clicked. This includes links that may trigger an action
besides opening up a new page, such as links that trigger browser menus.

Video Plays, Pauses, Replays
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some snippets allow users to view videos. Some of these snippets trigger events
when the video is played or paused, when the end of the video is reached, or
when the user replays the video after it finishes.

Social Sharing
~~~~~~~~~~~~~~

Some snippets contain popup windows to share content on social networks, such as
Facebook or Twitter. Most of these snippets trigger an event when the user
launches the popup window.

Default Browser
~~~~~~~~~~~~~~~

Some snippets trigger an event that tracks whether Firefox is the default
browser on the user's system. These snippets also trigger an event when the user
makes Firefox their default browser by either clicking a link in the snippet or
by setting the default outside of the browser.

Browser UI Events
~~~~~~~~~~~~~~~~~

Some snippets trigger events when the user clicks specific buttons in the
Firefox user interface (as opposed to the in-page snippet). Examples of the
elements that can be tracked this way include:

* The "Email", "Copy Link", and "Start Conversation" buttons within the Firefox
  Hello dialog.


Google Analytics
----------------

The `snippets statistics server <https://google.com>`_ may proxy data to Google
Analytics, with stripped IP information and with a unique to every request,
randomly generated UID. Google Analytics is never loaded within about:home. Some
Mozilla websites use Google Analytics to collect data about user behavior so
that we can improve our sites.
