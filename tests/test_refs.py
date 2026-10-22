import pytest

from ks.refs import parse_ref


@pytest.mark.parametrize("s", ["KS-12", "ks-12", "KS 12", " KS-12 "])
def test_parse_ref_variants(s):
    assert parse_ref(s) == ("KS", 12)


@pytest.mark.parametrize("s", ["twelve", "", "KS-", "12", "KS-1-2"])
def test_parse_ref_rejects(s):
    with pytest.raises(ValueError, match="not an issue reference"):
        parse_ref(s)
