Developing a Snippet
====================

The following document explains how to develop and test a snippet for use in
the Snippets Service. It is assumed that you've already filed a bug in the
`Snippets Campaign`_ component in Bugzilla to inform the snippets team that you
want to create a snippet.

.. _Snippets Campaign: https://bugzilla.mozilla.org/enter_bug.cgi?product=Snippets&component=Campaign

Using the staging server
------------------------

In order to develop a snippet properly, you must add your snippet to a test
instance of the snippet service. You may either user the staging instance of
snippets at https://snippets.allizom.org, or you may set up a local instance of
the snippets service using the :ref:`installation documentation <install>`.

To get access to the staging server, ask the snippets team via the bug you've
filed in Bugzilla.

Template or snippet?
--------------------

A snippet is an individual piece of code that is displayed on about:home to
users. Snippets are, in turn, generated from templates, which contain code
shared between multiple snippets. Templates are useful for snippets where you
want an admin to be able to substitute different text for localization or other
customization purposes. Templates are written in the Jinja2_ template language.

The admin interface can be reached at http://localhost:8000/admin/. Within it
you will find a section for creating templates and creating snippets. If you
intend to create a single snippet instead of a reusable template, you will have
to create a "Raw" template for your code that contains a single variable:

.. code-block:: jinja2

   {{ code|safe }}

You can then use this template for creating your snippet by dumping all of your
HTML into the ``code`` variable.

.. _Jinja2: http://jinja.pocoo.org/

Creating the snippet in the admin
---------------------------------

When creating or editing the snippet in the admin interface, you'll want to
check the following fields:

**Disabled**
   This must be unchecked or the snippet will not be served.
**Product channels**
   Controls which release channels the snippet goes to. Make sure all of them
   are checked.
**Locales**
  Controls which locales the snippet goes to. Make sure all locales are moved
  to the "Chosen locales" box (the "Choose all" link at the bottom can help).

Once you've saved the snippet, there will be a "View on site" button in the top
right of the editing page, which will show your snippet in a mock `about:home`
page. This page is really useful for initial development, but once you're ready
for final testing, you should read the :ref:`testing` section below for how to
test on a real `about:home` page.

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

- Globally unique things, such as tags with specific IDs or global JavaScript
  variables, should be avoided as much as possible. Prefer classes instead of
  IDs in HTML, and surround your JavaScript code with a function to avoid
  polluting the global scope. If absolutely necessary, this rule can be broken
  for snippets that will not ever show up more than once in the snippet bundle
  sent to the user.

  A common technique is to use the ``show_snippet`` event to get a reference to
  the individual snippet being shown, and to select elements based on their
  class from that element:

  .. code-block:: html

     <div class="snippet message-snippet" data-bound="0">
       <p class="message">Foo!</p>
     </div>
     <script>
       // <![CDATA[
       var snippets = document.getElementsByClassName('message-snippet');
       for (var k = 0; k < snippets.length; k++) {
         var snippet = snippets[k];

         // Only bind the handler if we haven't yet, in case there's multiple
         // message snippets.
         if (snippet.dataset['bound'] == '0') {
           snippet.dataset['bound'] = '1';
           snippet.addEventListener('show_snippet', function(e) {
             snippet.getElementsByClassName('message')[0].innerHTML = 'Bar!';
           }, false);
         }
       }
       // ]]>
     </script>

  .. note:: This will be made more sane in the future, trust me!

- Avoid loading remote resources if possible. For images and other media that
  you must include, use data URIs to include them directly in your snippet
  code.
- Due to performance concerns, avoid going over 200 kilobytes in filesize for
  a snippet. Snippets over 200 kilobytes large must be cleared with the
  development team first.

.. _testing:

Testing
-------

Once your snippet is done and ready for testing, you can use the
`snippet-switcher add-on <https://github.com/Osmose/snippet-switcher>`_ to set
the host for your `about:home` snippets to point to
``https://snippets.allizom.org`` or ``http://localhost:8000``, depending on
which server you are using for development.

If you are using the staging server, the developer who set up your account and
snippet should give you instructions on a Name value to use in the add-on's
settings in order to view your snippet specifically.

With the add-on installed, your `about:home` should load the latest snippet
code from your local snippets instance (after a short delay). If the code
doesn't seem to update, try force-refreshing with Cmd-Shift-R or Ctrl-Shift-R.

What versions of Firefox should I test?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Depending on the complexity of your snippet, you should choose the oldest
reasonable version of Firefox you want to support for your snippet, and test
roughly every other version from that up until the latest released Firefox, and
probably Nightly as well.

So, for example, if you wanted to support Firefox 26 and up, and the latest
version was Firefox 30, you'd test Firefo 26, 28, 30, and Nightly.

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
