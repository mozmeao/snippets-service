Contributing
============

Docker Setup
------------

These instructions help you set up a copy of the site using `Docker`_ and
`fig`_.

1. `Install Docker <https://docs.docker.com/installation/#installation>`_.

2. `Install fig <http://www.fig.sh/install.html>`_.

3. Grab the source code using git::

    $ git clone --recursive git://github.com/mozilla/snippets-service.git
    $ cd snippets-service

.. note:: Make sure you use ``--recursive`` when checking the repo out! If you
   didn't, you can load all the submodules with ``git submodule update --init
   --recursive``.

4. Build the Docker containers using fig::

    $ fig build

5. Run the database migrations to set up the database::

    $ fig run web ./bin/run-migrations.sh

Once you've finished these steps, you should be able to start the site by
running::

    $ fig up

If you're running Docker directly (via Linux), the site should be available at
http://localhost:8000. If you're running `boot2docker`_, the site should be
available on port 8000 at the IP output by running::

    $ boot2docker ip

.. _Docker: https://docs.docker.com/
.. _fig: http://www.fig.sh/
.. _boot2docker: http://boot2docker.io/

Local Instance Setup
--------------------

These instructions will set up an instance of the website running on your
computer directly, and assume you have ``git`` and ``pip`` installed. If you
don't have ``pip`` installed, you can install it with ``easy_install pip``.

1. Start by getting the source::

    $ git clone --recursive git://github.com/mozilla/snippets-service.git
    $ cd snippets-service

.. note:: Make sure you use ``--recursive`` when checking the repo out! If you
   didn't, you can load all the submodules with ``git submodule update --init
   --recursive``.

2. Create a virtual environment for the libraries. Skip the first step if you
   already have ``virtualenv`` installed::

    $ pip install virtualenv
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements/dev.txt

.. note:: The adventurous may prefer to use virtualenvwrapper_ instead of
   manually creating a virtualenv.

3. Set up a local MySQL database. The `MySQL Installation Documentation`_
   explains this fairly well.

4. Configure your local settings by copying ``snippets/settings/local.py-dist``
   to ``snippets/settings/local.py`` and customizing the settings in it::

    $ cp snippets/settings/local.py-dist snippets/settings/local.py

   The file is commented to explain what each setting does and how to customize
   them.

5. Initialize your database structure::

    $ python manage.py syncdb
    $ python manage.py migrate

.. _virtualenvwrapper: http://www.doughellmann.com/projects/virtualenvwrapper/
.. _MySQL Installation Documentation: http://dev.mysql.com/doc/refman/5.6/en/installing.html


Once you've followed the steps above, you can launch the development server
like so::

    $ python manage.py runserver
