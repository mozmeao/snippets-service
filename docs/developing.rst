Developing a Snippet Template
=============================

The following document explains how to develop and test a snippet template for
use in the Snippets Service. It is assumed that you've already filed a bug in
the `Snippets Campaign`_ component in Bugzilla to inform the snippets team that
you want to create a snippet template.

.. _Snippets Campaign: https://bugzilla.mozilla.org/enter_bug.cgi?product=Snippets&component=Campaign

Setting up your development environment
---------------------------------------

In order to develop a snippet template you need to setup have a snippets server.
You can either setup the full Snippets Service or the `Simple Snippets Server
for Template Development`_. The latter is strongly recommended and it will be
all you'll need for template development. It needs no configuration and the code
served to the browsers is the same the original Snippets Service serves. The
major difference is that all the Client Matching rules are ignored. All snippets
are served all the time and on every request which makes this ideal for template
development.

.. _Simple Snippets Server for Template Development: https://github.com/mozilla/snippets-service/tree/master/simple_template_server

Template or snippet?
--------------------

A snippet is an individual piece of code that is displayed on about:home to
users. Snippets are, in turn, generated from templates, which contain code
shared between multiple snippets. Templates are useful for snippets where you
want an admin to be able to substitute different text for localization or other
customization purposes. Templates are written in the Jinja2_ template language.

.. _Jinja2: http://jinja.pocoo.org/


How are snippets loaded?
------------------------

When a user requests snippets from the snippets service, the service finds all
snippets that match the user's client, generates the code for each snippet, and
concatenates all of the code together, along with some default CSS and
JavaScript.

When the user views `about:home`, this chunk of code is injected into the page.
The default CSS hides all tags with the class ``snippet``. Once injected, the
default JavaScript selects a snippet to show and un-hides the hidden tag.
Finally, a ``show_snippet`` event is triggered on the ``snippet`` tag to signal
to the snippet that it is being displayed.

Snippet requirements
--------------------

- All snippets must have an outermost tag with the class ``snippet``, and no
  tags outside of that except ``style`` or ``script`` tags:

  .. code-block:: html

     <div class="snippet">
       <img class="icon" src="some-data-uri" />
       <p>Foo bar baz biz</p>
     </div>

- Snippet code must be valid XML. This includes:

  - Closing all tags, and using self-closing tags like ``<br />``.
  - Avoiding HTML entities; use their numeric entities instead, e.g.
    ``&#187;`` instead of ``&raquo;``.
  - Using ``CDATA`` comments within all ``script`` tags:

    .. code-block:: html

       <script>
         // <![CDATA[
         alert('LOOK BEHIND YOU');
         // ]]>
       </script>

- Avoid loading remote resources if possible. For images and other media that
  you must include, use data URIs to include them directly in your snippet
  code.

- Due to performance concerns, avoid going over 500 kilobytes in filesize for
  a snippet. Snippets over 500 kilobytes large must be cleared with the
  development team first.

Helpers
-------

Accessing snippet id
^^^^^^^^^^^^^^^^^^^^
To get the snippet id within a snippet template use `snippet_id` Jinja2 variable like this:

  .. code-block:: html

     <div class="snippet">
       This is snippet id {{ snippet_id }}.
     </div>

The syntax in a snippet is slightly different and uses square brackets `[[snippet_id]]`.  Here is an example that uses the `Raw Template`:

  .. code-block:: html

     <div class="snippet">
       This is snippet id [[snippet_id]].
     </div>

  .. warning:: Beware that in this case spacing matters and `[[ snippet_id ]]` will not work.


Custom Metric Pings
^^^^^^^^^^^^^^^^^^^

Snippet events can be captured and sent to our metrics server. By
default snippet impressions get captured and sent to our metrics
server tagged as `impression`. Clicks on `<a>` elements with defined
`href` get captured too and get sent back as `click`.

Snippet developers can customize the metric name of clicks by setting
the `metric` data attribute on the link. For example clicking on the
link of the following snippet:

  .. code-block:: html

     <div class="snippet">
       <p class="message">
         Click this <a href="http://example.com" data-metric="custom-click">link!</a>
       </p>
     </div>

will send back a `custom-click` ping instead of a `click` ping.

.. warning::
  Avoid setting up event listeners on links for click events and
  manually sending metric pings, or pings may get sent *both* by your
  click handler and the global click handler resulting in inaccurate
  numbers.

In addition to impressions and clicks snippet developers can send
custom pings to capture interactions using the `sendMetric` function
like this:

  .. code-block:: html

     <!-- Use Raw Template to try this out -->
     <div class="snippet" id="ping-snippet-[[snippet_id]]">
       <p class="message">Foo!</p>
     </div>
     <script type="text/javascript">
       //<![CDATA[
       (function() {
         var snippet = document.getElementById('ping-snippet-[[snippet_id]]');
         snippet.addEventListener('show_snippet', function() {
           (function () {
             var callback = function() {
               alert('Success!');
             };
             var metric_name = 'success-ping-[[snippet_id]]';
             sendMetric(metric_name, callback);
           })();
         }, false);
       })();
     //]]>
     </script>

  .. note:: Callback function is optional.

.. note:: Only 10% of the pings reach the server. We sample at the browser level. See `sendMetric`_ function for implementation details.


Using MozUITour
^^^^^^^^^^^^^^^
Snippets and snippet templates can use `MozUiTour`_ to interact with the browser. Developer can directly use the following MozUITour functions:

* Mozilla.UITour.showHighlight
* Mozilla.UITour.hideHighlight
* Mozilla.UITour.showMenu
* Mozilla.UITour.hideMenu
* Mozilla.UITour.getConfiguration
* Mozilla.UITour.setConfiguration

For example to determine whether Firefox is the default browser can you use the following function in a snippet:

  .. code-block:: javascript

     function isDefault (yesDefault, noDefault) {
         Mozilla.UITour.getConfiguration('appinfo', function(config) {
             if (config && config.defaultBrowser === true) {
                 firefoxIsDefault();
             } else if (config && config.defaultBrowser === false) {
                 firefoxIsNotDefault();
             } else {
                 firefoxIsDefault();
             }
         });
     }

You can even use the low level MozUITour functions:

* _sendEvent
* _generateCallbackID
* _waitForCallback

to trigger more events. For example to trigger Firefox Accounts:

  .. code-block:: javascript

     var fire_event = function() {
         var event = new CustomEvent(
             'mozUITour',
             { bubbles: true, detail: { action:'showFirefoxAccounts', data: {}}}
         );
         document.dispatchEvent(event);
     };


Snippet Block List
^^^^^^^^^^^^^^^^^^

Snippets can be prevented from showing using a block list. By default the block list is empty and the intention is to allow users to block specific snippets from showing by taking an action. Snippet service automatically assigns the block functionality to all elements of snippet with class `block-snippet-button`. For example a disruptive snippet can include a special `Do not display again` link that adds the snippet into the block list:

  .. code-block:: html

     <!-- Use Raw Template to try this out -->
     <div class="snippet" id="block-snippet-[[snippet_id]]">
       Foo! <a href="#" class="block-snippet-button">Do not show again</a>
     </div>


If you need more control you can directly access the low-level function `addToBlockList`:

  .. code-block:: html

     <!-- Use Raw Template to try this out -->
     <div class="snippet" id="block-snippet-[[snippet_id]]">
       Foo! <a href="#" id="block-snippet-link">Do not show again</a>
     </div>
     <script type="text/javascript">
       //<![CDATA[
       (function() {
         var snippet = document.getElementById('block-snippet-[[snippet_id]]');
         snippet.addEventListener('show_snippet', function() {
           (function () {
             var link = document.getElementById('block-snippet-link');
             link.onclick = function() {
               addToBlockList([[snippet_id]]);
               window.location.reload();
             }
           })();
         }, false);
       })();
     //]]>
     </script>

  .. note::
     In this case we don't utilize the special `block-snippet-button` class.

More low level functions are `popFromBlockList` and `getBlockList`.

In bug `1172579`_ close button assets are provided to build a image
button in your snippet. Refer to the `simple snippet`_ code on how to
do this.



.. _testing:

Testing
-------

Once your snippet is done and ready for testing, you can use the
`snippet-switcher add-on <https://github.com/Osmose/snippet-switcher>`_ to set
the host for your `about:home` snippets to point to
``https://snippets.allizom.org`` or ``http://localhost:8000``, depending on
which server you are using for development.

Alternatively to using the add-on you can change the
`browser.aboutHomeSnippets.updateUrl` perf from `about:config` to point to your
server. For example

``http://localhost:8000/%STARTPAGE_VERSION%/%NAME%/%VERSION%/%APPBUILDID%/%BUILD_TARGET%/%LOCALE%/%CHANNEL%/%OS_VERSION%/%DISTRIBUTION%/%DISTRIBUTION_VERSION%/``

If you are using the staging server, the developer who set up your account and
snippet should give you instructions on a Name value to use in the add-on's
settings in order to view your snippet specifically.

With the add-on installed or the perf change made, your `about:home` should load
the latest snippet code from your local snippets instance (after a short delay).
If the code doesn't seem to update, try force-refreshing with Cmd-Shift-R or
Ctrl-Shift-R and deleting local snippet storage by typing in a web console:

``gSnippetsMap.clear()``

What versions of Firefox should I test?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Depending on the complexity of your snippet, you should choose the oldest
reasonable version of Firefox you want to support for your snippet, and test
roughly every other version from that up until the latest released Firefox, and
probably Nightly as well.

So, for example, if you wanted to support Firefox 26 and up, and the latest
version was Firefox 30, you'd test Firefox 26, 28, 30, and Nightly.

What should I test for?
^^^^^^^^^^^^^^^^^^^^^^^

- Basic functionality of your snippet. Make sure it works as you expect it to
  do.
- Ensure that your snippet does not interfere with other snippets. The staging
  server has a normal text+icon snippet that is sent to *all* clients, which
  will help you ensure that the normal snippet can be shown without being
  altered by your snippet.
- Ensure that your snippet can run alongside multiple instances of itself.
- Ensure that the normal `about:home` functionality, such as the search box,
  links at the bottom, and session restore function properly.

Code review
-----------

There is a `snippets Github repo`_ that keeps track of the code for snippets
we've run. Once your snippet is finished, you should submit a pull request to
the snippets repo adding your snippet or template code for a code review. A
snippets developer should respond with a review or direct your PR to the right
person for review. If your snippet is already on the staging server, include
the URL for editing it to make it easier for the reviewer to test it.

.. _snippets Github repo: https://github.com/mozilla/snippets
.. _1172579: https://bugzilla.mozilla.org/show_bug.cgi?id=1172579
.. _simple snippet: https://github.com/mozilla/snippets/blob/master/templates/simple-snippet.html
.. _MozUITour: https://hg.mozilla.org/mozilla-central/file/tip/browser/components/uitour/UITour-lib.js
.. _sendMetric: https://github.com/mozilla/snippets-service/blob/master/snippets/base/templates/base/includes/snippet_js.html
.. _
