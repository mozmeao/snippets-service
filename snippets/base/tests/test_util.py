from nose.tools import eq_

from snippets.base.models import Snippet
from snippets.base.tests import SnippetFactory, TestCase
from snippets.base.util import first, get_object_or_none


class TestGetObjectOrNone(TestCase):
    def test_does_not_exist(self):
        """Return None if no matching object exists."""
        value = get_object_or_none(Snippet, name='Does not exist')
        eq_(value, None)

    def test_multiple_objects_returned(self):
        """Return None if multiple objects are returned."""
        SnippetFactory.create(data='{"multiple": 1}')
        SnippetFactory.create(data='{"multiple": 1}')
        value = get_object_or_none(Snippet, data='{"multiple": 1}')
        eq_(value, None)

    def test_exists(self):
        """If no exceptions occur, return the matched object."""
        video = SnippetFactory.create(name='exists')
        value = get_object_or_none(Snippet, name='exists')
        eq_(value, video)


class TestFirst(TestCase):
    def test_basic(self):
        items = [(0, 'foo'), (1, 'bar'), (2, 'baz')]
        eq_(first(items, lambda x: x[0] == 1), (1, 'bar'))

    def test_no_match(self):
        """Return None if the callback never passes for any item."""
        items = [(0, 'foo'), (1, 'bar'), (2, 'baz')]
        eq_(first(items, lambda x: x[0] == 17), None)
