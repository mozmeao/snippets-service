Snippet-tests
=====================

Automated tests for the Snippets web app

Running Tests
-------------

___Running the tests against staging___

* [Install Tox](https://tox.readthedocs.io/en/latest/install.html)
* Run `tox`

___Running the tests against production___

* `export PYTEST_BASE_URL="https://snippets.mozilla.com"`
* `tox`

Or:

* Run `tox -- --base-url=https://snippets.mozilla.com`

License
-------
This software is licensed under the [MPL] 2.0:

    This Source Code Form is subject to the terms of the Mozilla Public
    License, v. 2.0. If a copy of the MPL was not distributed with this
    file, You can obtain one at http://mozilla.org/MPL/2.0/.

[MPL]: http://www.mozilla.org/MPL/2.0/
