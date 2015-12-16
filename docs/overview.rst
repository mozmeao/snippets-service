Overview
========

This document describes the snippet service and how it relates to about:home,
the home page for Firefox.

What is a snippet?
------------------

about:home is the default home page in Firefox. When you visit about:home, you
normally see, among other things, a Firefox logo, a search bar, and a bit of
text and an icon below the search bar. This text and icon are what is called a
"snippet".

Snippets can be more than just text and an icon, though. Sometimes a snippet
can replace the Firefox logo with a larger image. A snippet could also pop up
a video for you to watch. Snippets are made of HTML, CSS, and JavaScript, and
can modify the homepage in interesting and fun ways.

.. figure:: img/snippet_example.png
   :align: center

   A snippet that replaced the Firefox logo with a larger, more detailed image.

The Snippets Service is a web service that serves the code for snippets.
Firefox downloads code from the Snippet Service and injects the code into
about:home. This allows administrators using the service to control which
snippets are being shown by Firefox without having to update Firefox itself.

How are snippets retrieved by Firefox?
--------------------------------------

.. digraph:: snippet_download_flow

   load_abouthome[label="User loads\nabout:home"];
   check_cache_timeout[label="Has it been\n4 hours since\nsnippets were fetched?" shape=diamond];
   load_cached_snippets[label="Retrieve snippets from\nIndexedDB" shape=rectangle];
   fetch_snippets[label="Fetch snippets from\nsnippets.mozilla.com" shape=rectangle];
   store_snippets[label="Store new snippets in\nIndexedDB" shape=rectangle];
   insert_snippets[label="Insert snippet HTML\ninto about:home"];

   load_abouthome -> check_cache_timeout;
   check_cache_timeout -> load_cached_snippets[label="No"];

   check_cache_timeout -> fetch_snippets[label="Yes"];
   fetch_snippets -> store_snippets;
   store_snippets -> load_cached_snippets;

   load_cached_snippets -> insert_snippets;

Firefox maintains a cache of snippet code downloaded from the Snippet Service
for at least 4 hours since the last download. The cache (and a few other
useful pieces of information) are stored in IndexedDB, and can be accessed by
code on about:home using a global JavaScript object named ``gSnippetsMap``.

When a user visits about:home, Firefox checks to see when it last downloaded
new snippet code. If it has been at least 4 hours, Firefox requests new
snippet code from the Snippet Service and stores it in the cache along with
the current time. After this, or if it hasn't been 4 hours, Firefox loads the
snippet code from the cache and injects it directly into about:home.

.. note:: All Firefox does is download snippet code from the service and inject
   it into the page. The rest of the logic behind displaying snippets is
   determined by the snippet code itself, as explained in the next section.

.. note:: Firefox for Android caches snippets for 24 hours.

.. seealso::

   `aboutHome.js <http://dxr.mozilla.org/mozilla-central/source/browser/base/content/abouthome/aboutHome.js>`_
      The JavaScript within Firefox that, among other things, handles
      downloading and injecting snippet code.

How are snippets displayed?
---------------------------

The snippet code downloaded from the Snippet Service consists of three parts:

- A small block of CSS that is common to all snippets. Among other things, this
  hides all the snippets initially so that only the one chosen to be displayed
  is visible to the user.
- The code for each individual snippet, surrounded by some minimal HTML.
- A block of JavaScript that handles displaying the snippets and other tasks.

.. note:: It's important to understand that all the code for every snippet a
   user might see is injected into the page. This means that any JavaScript or
   CSS that is included in a snippet might conflict with JavaScript or CSS from
   another snippet.

   For this reason it is important to ensure that snippet code is well-isolated
   and avoids overly-broad CSS selectors or the global namespace in JavaScript.

Once the code is injected, the included JavaScript:

- Identifies all elements in the snippet code with the ``snippet`` class as
  potential snippets to display.
- Filters out snippets that don't match the user's location. See
  :doc:`geolocation` for information on how we retrieve and store
  geolocation data.
- Filters out snippets that are only supposed to be shown to users without a
  Firefox account.
- Filters out snippets that are only supposed to be shown to users with a
  certain search provider.
- Chooses a random snippet from the set based on their "weight" (a higher
  weight makes a snippet show more often relative to snippets with lower
  weights).
- Displays the snippet.
- Triggers a ``show_snippet`` event on the ``.snippet`` element.
- Modifies all ``<a>`` tags in the snippet to add the snippet ID as a
  URL parameter.
- Logs an impression for the displayed snippet by sending a request to
  the snippets metrics server. These requests are sampled and only go
  out 10% of the time. See also :doc:`data_collection` chapter for more
  information on the data send to the metrics server.

If no snippets are available, the code falls back to showing default snippets
included within Firefox itself.
