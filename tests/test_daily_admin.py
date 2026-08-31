import pytest

from app import daily_admin as da


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def test_setup_login_and_status():
    st = da.admin_status(None)
    assert st == {"hasPassword": False, "authenticated": False}
    out = da.setup_password("secret123")
    assert out["token"]
    assert da.admin_status(out["token"])["authenticated"] is True
    with pytest.raises(ValueError):
        da.setup_password("again")
    tok2 = da.login("secret123")["token"]
    assert da.admin_status(tok2)["authenticated"] is True
    with pytest.raises(ValueError):
        da.login("wrong")


def test_template_default_and_put():
    t = da.get_template()
    assert len(t["stages"]) == 8
    assert t["stages"][0]["tier"] == "normal"
    da.put_template([{"gameId": "schulte", "tier": "hard"}, {"gameId": "sudoku", "tier": "simple"}])
    assert da.get_template()["stages"][0]["gameId"] == "schulte"
    with pytest.raises(ValueError):
        da.put_template([])
    with pytest.raises(ValueError):
        da.put_template([{"gameId": "nope", "tier": "normal"}])
