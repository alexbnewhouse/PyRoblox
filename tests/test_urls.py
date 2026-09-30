import pytest

from robloxwrapper.urls import looks_like_id, parse_roblox_url


@pytest.mark.parametrize("raw,expected", [
    ("https://www.roblox.com/users/261/profile", ("user", 261)),
    ("http://roblox.com/users/261/profile", ("user", 261)),
    ("roblox.com/users/261", ("user", 261)),
    ("https://www.roblox.com/groups/7/Roblox", ("group", 7)),
    ("https://www.roblox.com/communities/7/Roblox", ("group", 7)),
    ("https://www.roblox.com/games/1818/Classic-Crossroads", ("game", 1818)),
    ("https://www.roblox.com/games/1818/Classic-Crossroads?privateServerLinkCode=1", ("game", 1818)),
    ("https://www.roblox.com/games/1818?x=1", ("game", 1818)),
    ("https://web.roblox.com/games/1818", ("game", 1818)),
    ("https://m.roblox.com/games/1818", ("game", 1818)),
    ("https://www.roblox.com/catalog/1029025/Classic-ROBLOX-Fedora", ("asset", 1029025)),
    ("https://www.roblox.com/library/168367449/Some-Model", ("asset", 168367449)),
    ("https://www.roblox.com/badges/14427263/Winner", ("badge", 14427263)),
    ("https://www.roblox.com/bundles/589/Duchess-of-the-Deep", ("bundle", 589)),
    ("user:261", ("user", 261)),
    ("GROUP:7", ("group", 7)),
    ("  https://www.roblox.com/users/261/profile  ", ("user", 261)),
])
def test_parse_roblox_url(raw, expected):
    assert parse_roblox_url(raw) == expected


@pytest.mark.parametrize("raw", [
    "",
    "   ",
    "https://t.me/foo",
    "https://www.roblox.com/",
    "https://www.roblox.com/discover",
    "https://www.roblox.com/users/abc/profile",
    "player:261",
    "roblox.com/users/",
    "just some text",
    "261",
])
def test_parse_roblox_url_rejects_junk(raw):
    with pytest.raises(ValueError):
        parse_roblox_url(raw)


def test_looks_like_id():
    assert looks_like_id("261")
    assert looks_like_id(" 261 ")
    assert not looks_like_id("Shedletsky")
    assert not looks_like_id("-1")
    assert not looks_like_id("")
