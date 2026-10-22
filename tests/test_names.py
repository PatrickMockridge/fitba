from fitba.normalize.names import (
    normalize_name,
    slugify,
    team_slug,
    titlecase_club_name,
)
from fitba.normalize.teams import TeamRegistry


def test_normalize_abbreviations_and_punctuation():
    assert normalize_name("Airdrie Utd") == "airdrie united"
    assert normalize_name("St. Mirren") == "st mirren"
    assert normalize_name("Queen's Park") == "queens park"
    assert normalize_name("Raith Rvs") == "raith rovers"


def test_registry_resolves_source_names():
    registry = TeamRegistry()
    expected = {
        "Aberdeen": "sco:aberdeen",
        "Airdrie Utd": "sco:airdrieonians",
        "Dundee United": "sco:dundee-united",
        "Hearts": "sco:heart-of-midlothian",
        "Inverness C": "sco:inverness-caledonian-thistle",
        "Morton": "sco:greenock-morton",
        "Partick": "sco:partick-thistle",
        "Queen of Sth": "sco:queen-of-the-south",
        "Queens Park": "sco:queens-park",
        "Raith Rvs": "sco:raith-rovers",
        "Stirling": "sco:stirling-albion",
        "Spartans": "sco:the-spartans",
    }
    for raw, team_id in expected.items():
        assert registry.resolve(raw) == team_id


def test_registry_rejects_unknown():
    registry = TeamRegistry()
    assert registry.resolve("Not A Real Club") is None
    assert registry.provisional("Not A Real Club") == "sco:provisional-not-a-real-club"


def test_slug_helpers():
    assert slugify("St. Mirren") == "st-mirren"
    assert team_slug("sco:aberdeen") == "aberdeen"


def test_club_display_capitalisation():
    registry = TeamRegistry()
    assert registry.display_name("ST Johnstone") == "St Johnstone"
    assert registry.display_name("ST Mirren") == "St Mirren"
    assert registry.display_name("St johnstone") == "St Johnstone"
    assert titlecase_club_name("ST johnstone") == "St Johnstone"
    assert titlecase_club_name("FC ST. Gallen") == "FC St. Gallen"
    assert titlecase_club_name("fc st. gallen") == "FC St. Gallen"
    assert titlecase_club_name("ST MIRREN") == "St Mirren"
    assert titlecase_club_name("HJK HELSINKI") == "HJK Helsinki"
    assert titlecase_club_name("St. Louis City") == "St. Louis City"
    assert titlecase_club_name("1. FC KAISERSLAUTERN") == "1. FC Kaiserslautern"
    assert titlecase_club_name("ADO den Haag") == "ADO Den Haag"
    assert titlecase_club_name("Free Agent") == "Free agent"
    assert registry.display_name_for_id("sco:free-agent", "Free Agent") == "Free agent"
