import pytest

from tools.lexicon.scoring import KEEP, LIKELY_DELETE, LIKELY_KEEP, REVIEW, Thresholds, suggest, zipf_from_per_million


@pytest.mark.parametrize("per_million, zipf", [(1, 3.0), (1000, 6.0), (0.2, 2.3), (0, 0.0)])
def test_zipf_scale(per_million, zipf):
    assert zipf_from_per_million(per_million) == zipf


@pytest.mark.parametrize("zipf, has_own_definition, expected", [
    (5.7, False, KEEP),
    (3.5, False, KEEP),
    (2.6, False, LIKELY_KEEP),
    (2.3, True, REVIEW),
    (0.0, True, REVIEW),
    (0.0, False, LIKELY_DELETE),
])
def test_suggestions(zipf, has_own_definition, expected):
    assert suggest(zipf, has_own_definition) == expected


def test_thresholds_are_configurable():
    assert suggest(3.0, False, Thresholds(auto_keep_zipf=3.0)) == KEEP
