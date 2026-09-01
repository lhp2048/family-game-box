import pytest

from app import difficulty as diff


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def test_get_defaults_has_eight_games():
    data = diff.get_difficulty()
    for gid in ("24points", "schulte", "stroop", "cancel", "simon", "spot-diff", "maze", "sudoku"):
        assert gid in data["games"]
        assert "normal" in data["games"][gid]["tiers"]


def test_put_schulte_and_get():
    diff.put_difficulty(
        {"schulte": {"tiers": {"normal": {"size": 6, "reverse": True, "label": "普通*"}}}}
    )
    g = diff.get_difficulty("schulte")
    assert g["games"]["schulte"]["tiers"]["normal"]["size"] == 6
    assert g["games"]["schulte"]["tiers"]["intro"]["size"] == 3


def test_put_invalid_sudoku_rejects():
    with pytest.raises(ValueError):
        diff.put_difficulty(
            {"sudoku": {"tiers": {"intro": {"size": 5, "givens": 3, "label": "x"}}}}
        )


def test_reset_one_game():
    diff.put_difficulty({"maze": {"tiers": {"intro": {"size": 7, "label": "入门"}}}})
    diff.reset_difficulty("maze")
    assert diff.get_difficulty("maze")["games"]["maze"]["tiers"]["intro"]["size"] == 9


def test_24points_cuts_and_range():
    diff.put_difficulty(
        {
            "24points": {
                "cuts": [0.1, 0.2, 0.4, 0.6, 0.8, 1.01],
                "tiers": {"intro": {"minNum": 1, "maxNum": 9, "label": "入门", "desc": ""}},
            }
        }
    )
    t = diff.get_difficulty("24points")["games"]["24points"]
    assert t["cuts"][0] == 0.1
    assert t["tiers"]["intro"]["maxNum"] == 9
