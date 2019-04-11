from collections import namedtuple

from bard.providers import merge_named_tuple


def test_merge_named_tuple():
    named = namedtuple('named', ('a', 'b', 'c'))

    x = named(1, 2, 3)
    y = named(4, 5, 6)

    assert merge_named_tuple(x, y, fields=['a', 'b', 'c']) == named(4, 5, 6)
    assert merge_named_tuple(x, y, fields=['a']) == named(4, 2, 3)
