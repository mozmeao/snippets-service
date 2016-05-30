Template Development Server
===================================

This is a simple Snippet Server for development of Snippet Templates. It ignores
the client configuration including locale, Firefox version and release channels
and just returns all the snippets to the requesting client. If you only care for
Snippet Template development this is the server for you.

Installation
------------
0. Make sure you're located in the `simple_template_server` directory, otherwise
   you'll be installing requirements for the full snippets service.

1. Create and activate a Python virtualenv

    ``` shell
    virtualenv venv
    . venv/bin/activate
    ```

2. Install the needed packages

    ``` shell
    pip install -r requirements.txt
    ```

Using the server
----------------

0. Make sure you're in `simple_template_server` directory.

1. Run the server

    ``` shell
    python webserver.py
    ```

    The server listens on *http://0.0.0.0:8000*

2. Add your templates in the `snippets/` directory ending with `.html`.

3. Most likely your template will have variables and you can add those in a YAML
   file under the same directory with the same base filename with `.yml`
   extension.

For demo purposes the `snippets/` directory already contains a
`snippet-one.html` and the corresponding `snippet-one.yml` variable file.

You can add as many snippets you want and *all* of them will be served to every
requesting browser. The server will auto-load the snippets on every request.

Detailed documentation on how to configure Firefox for development and on how to
build snippet templates can be found in
[Snippet Documentation](http://abouthome-snippets-service.readthedocs.org/en/latest/developing.html)
