import sys


from .base import *

# Load special settings for CI.
if os.environ.get('TRAVIS'):
    from .travis import *
elif os.environ.get('DOCKER'):
    from .docker import *
else:
    try:
        from .local import *
    except ImportError, exc:
        exc.args = tuple(['%s (did you rename settings/local.py-dist?)' % exc.args[0]])
        raise exc

TEST = len(sys.argv) > 1 and sys.argv[1] == 'test'
if TEST:
    try:
        from .test import *
    except ImportError:
        pass
