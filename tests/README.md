# Tests for Snippets

Automated tests for the Snippets web app.

## How to run the tests

By default, the tests will run against the **staging** environment.

You can run the tests using [Docker][]:
```bash
  $ cd tests
  $ docker build -t snippets-tests .
  $ docker run -it snippets-tests
  ```

To run the tests against the **production** or another environment, change the last command as shown:

```bash
  $ docker run -t snippets-tests pytest --base-url=https://snippets.mozilla.com
```

License
-------
This software is licensed under the [MPL] 2.0:

    This Source Code Form is subject to the terms of the Mozilla Public
    License, v. 2.0. If a copy of the MPL was not distributed with this
    file, You can obtain one at http://mozilla.org/MPL/2.0/.

[Docker]: https://www.docker.com
[MPL]: http://www.mozilla.org/MPL/2.0/
