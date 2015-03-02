import sys


from .base import *  # NOQA

# Load special settings for CI.
if os.environ.get('TRAVIS'):
    from .travis import *  # NOQA
elif os.environ.get('DOCKER'):
    from .docker import *  # NOQA
else:
    try:
        from .local import *  # NOQA
    except ImportError, exc:
        exc.args = tuple(['%s (did you rename settings/local.py-dist?)' % exc.args[0]])
        raise exc

TEST = len(sys.argv) > 1 and sys.argv[1] == 'test'
if TEST:
    try:
        from .test import *  # NOQA
    except ImportError:
        pass
