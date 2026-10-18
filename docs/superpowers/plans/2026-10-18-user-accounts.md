# User Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add personal username/password accounts on top of the family play-gate so playing games requires login, scores follow the user across devices, and same-device switching works, with optional one-time claim of old terminal nickname scores.

**Architecture:** New `app/users.py` mirrors `daily_admin` / `terminals` patterns: JSON/Turso document `users.json`, salted SHA-256 password hashes (same `_hash` style as admin/play-gate), HMAC-signed `fgb_user` session cookie. Middleware requires a valid user session for game play and score-writing paths (after play-gate when enabled). Scores and daily runs gain `userId`; leaderboards prefer username. Claim API migrates one terminal’s history once.

**Tech Stack:** FastAPI, existing `app.storage.load_json`/`save_json`, hashlib/hmac/secrets (no new dependencies), pytest + TestClient, static HTML/JS under `web/`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-18-user-accounts-design.md`
- Do not change Cloudflare tunnel DNS for `game.mx1024.com`
- Admin password model and play-gate settings stay separate and working
- Password plaintext never stored or logged
- Hall `/` and public leaderboards stay readable without personal login
- Playing `/games/*`, `/uploaded-games/*`, daily/yuwen play pages, and score/run write APIs require `fgb_user` (even if play-gate is disabled)
- Register must re-check family passphrase when play-gate is enabled; when disabled, register still works without family passphrase field validation against a missing secret (treat empty/disabled gate as “family check skipped”)
- Username uniqueness case-insensitive; display preserves original casing
- Chinese error messages for auth failures
- Prefer small commits; TDD for server modules

## File map

| File | Role |
|------|------|
| `app/users.py` | User store, register/login/logout/me, session cookie, claim-terminal |
| `app/play_gate.py` | Extend `needs_play` / `allowed` or add sibling user check used by middleware |
| `app/main.py` | Auth routes, pages, middleware order, wire score/daily to user |
| `app/scores.py` | Persist `userId` + username; lookup helpers for claim/leaderboard |
| `app/daily_runs.py` / `app/yuwen_daily.py` | Attach `userId` on new runs; claim migration hooks |
| `app/lobby.py` | Prefer user identity for “me” when session present |
| `web/login.html` / `web/register.html` | Auth UI |
| `web/js/fgb-client.js` / `web/js/fgb-ui.js` / `web/index.html` | Session-aware client, top bar |
| `web/css/fgb-theme.css` | Only if login/register need small shared styles |
| `tests/test_users.py` | Unit + API tests for auth and claim |
| `tests/test_play_gate.py` | Ensure play + user gate interaction |

---

### Task 1: User store and session cookie

**Files:**
- Create: `app/users.py`
- Create: `tests/test_users.py`
- Modify: none yet

**Interfaces:**
- Produces:
  - `normalize_username(value: str) -> str`
  - `register_user(username: str, password: str) -> dict` → `{userId, username, createdAt}`
  - `authenticate(username: str, password: str) -> dict` (raises `ValueError` with Chinese message)
  - `issue_user_cookie(user_id: str, now: int | None = None) -> str`
  - `user_cookie_ok(cookie: str | None, now: int | None = None) -> bool`
  - `user_id_from_cookie(cookie: str | None, now: int | None = None) -> str | None`
  - `get_user(user_id: str) -> dict | None`
  - `get_user_by_username(username: str) -> dict | None`
  - `USER_COOKIE = "fgb_user"`
  - Store shape: `{"version": 1, "users": {userId: {...}}, "usernameIndex": {lower: userId}, "sessionKey": str, "claimedTerminals": {terminalId: userId}}`

- [ ] **Step 1: Write failing unit tests**

```python
# tests/test_users.py
import time
import pytest
from app import users


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    yield


def test_register_and_authenticate():
    created = users.register_user("小明", "pass1234")
    assert created["username"] == "小明"
    assert "userId" in created
    me = users.authenticate("小明", "pass1234")
    assert me["userId"] == created["userId"]
    with pytest.raises(ValueError, match="口令"):
        users.authenticate("小明", "wrong")
    with pytest.raises(ValueError, match="已占用|已存在"):
        users.register_user("小明", "other")


def test_session_cookie_roundtrip():
    u = users.register_user("ada", "secret99")
    now = int(time.time())
    cookie = users.issue_user_cookie(u["userId"], now=now)
    assert users.user_cookie_ok(cookie, now=now)
    assert users.user_id_from_cookie(cookie, now=now) == u["userId"]
    assert users.user_cookie_ok("garbage", now=now) is False
```

- [ ] **Step 2: Run tests — expect fail (module missing)**

Run: `pytest tests/test_users.py -v`  
Expected: FAIL import or attribute errors

- [ ] **Step 3: Implement `app/users.py`**

Follow `app/daily_admin.py` hashing/HMAC cookie style:

- Username: strip, 1–16 chars, same character class as nickname (`_NICKNAME_RE` or shared)
- Password: min 6, max 128
- `passwordSalt` + `passwordHash` per user via `hashlib.sha256((salt + password).encode()).hexdigest()`
- Cookie payload: `userId.exp.generation` + HMAC with store `sessionKey`; TTL e.g. 30 days
- Case-insensitive username index

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_users.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/users.py tests/test_users.py
git commit -m "feat(auth): add user store and session cookie"
```

---

### Task 2: Auth HTTP API + register family-passphrase check

**Files:**
- Modify: `app/main.py` (models + routes + cookie set/clear)
- Modify: `tests/test_users.py` (API cases)
- Modify: `app/users.py` if register needs a thin wrapper that checks play-gate

**Interfaces:**
- Consumes: Task 1 functions; `app.daily_admin.issue_play_cookie` / play passphrase verify (reuse hash check: call `issue_play_cookie` only when gate enabled, or extract verify helper)
- Produces:
  - `POST /api/v1/auth/register` body `{username, password, passphrase?}` → sets `fgb_user`, returns me
  - `POST /api/v1/auth/login` `{username, password}` → sets cookie
  - `POST /api/v1/auth/logout` → clears cookie
  - `GET /api/v1/auth/me` → `{loggedIn, userId?, username?}`

- [ ] **Step 1: Write failing API tests**

```python
from fastapi.testclient import TestClient
from helpers import url
from app.main import app
from app import daily_admin as da

client = TestClient(app)


def test_register_requires_family_when_gate_on(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    da.clear_play_gate_cache()
    da.setup_password("adminpass")
    token = da.login("adminpass")["token"]
    client.put(
        url("/api/v1/admin/play-gate"),
        json={"enabled": True, "passphrase": "family"},
        headers={"X-Admin-Token": token},
    )
    bad = client.post(
        url("/api/v1/auth/register"),
        json={"username": "bob", "password": "pass1234", "passphrase": "nope"},
    )
    assert bad.status_code == 400
    ok = client.post(
        url("/api/v1/auth/register"),
        json={"username": "bob", "password": "pass1234", "passphrase": "family"},
    )
    assert ok.status_code == 200
    assert ok.json()["username"] == "bob"
    assert client.cookies.get("fgb_user")
    me = client.get(url("/api/v1/auth/me"))
    assert me.json()["loggedIn"] is True
```

Also cover login wrong password → 400 Chinese message; logout clears cookie.

- [ ] **Step 2: Run — expect fail (404 routes)**

Run: `pytest tests/test_users.py -k auth -v`

- [ ] **Step 3: Implement routes in `app/main.py`**

- Pydantic bodies for register/login
- On register when `play_gate_snapshot()["playGateEnabled"]`: verify passphrase (same check as unlock); else ignore passphrase
- `response.set_cookie(USER_COOKIE, …, httponly=True, samesite="lax", path=with_root("/") or "/")` matching play cookie options
- Map `ValueError` → HTTP 400 with `detail` as Chinese string

- [ ] **Step 4: Run — expect pass**

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/users.py tests/test_users.py
git commit -m "feat(auth): register/login/logout/me API"
```

---

### Task 3: Require user session to play and submit scores

**Files:**
- Modify: `app/play_gate.py` and/or `app/main.py` middleware
- Modify: `tests/test_play_gate.py` and/or `tests/test_users.py`

**Interfaces:**
- Consumes: `user_cookie_ok`, `USER_COOKIE`
- Produces: middleware behavior — for paths that need play identity (games HTML, daily play, score POST, daily run writes): require `fgb_user` (admin token may still bypass like play-gate)

Logic:

1. Existing play-gate check unchanged.
2. New check `needs_user(method, path)` ≈ same set as `needs_play` (games pages + score/daily write APIs). Leaderboard GETs and hall stay open.
3. If needs user and cookie invalid → redirect HTML to `/login?next=…` or 401 JSON for `/api/…`.

- [ ] **Step 1: Failing test**

```python
def test_score_requires_user_even_when_gate_off():
    client.cookies.clear()
    # register terminal only (legacy)
    tid = "11111111-1111-4111-8111-111111111111"
    client.post(url("/api/v1/terminals/register"), json={"terminalId": tid, "nickname": "旧号"})
    r = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal",
              "metrics": {"correct": 1, "total": 1, "timeMs": 1000}},
        headers={"X-Terminal-Id": tid},
    )
    assert r.status_code in (401, 403)
```

Plus: after login cookie, score succeeds.

- [ ] **Step 2: Run — expect fail (score still 200)**

- [ ] **Step 3: Implement middleware user check**

Keep play-gate first; then user check. Do not require user for `/login`, `/register`, `/api/v1/auth/*`, static css/js needed by login pages, leaderboards, `/`, health.

- [ ] **Step 4: Run full related tests**

Run: `pytest tests/test_users.py tests/test_play_gate.py tests/test_scores.py -v`  
Fix any intentional breakages in score tests by logging in first.

- [ ] **Step 5: Commit**

```bash
git add app/play_gate.py app/main.py tests/
git commit -m "feat(auth): require user session to play and score"
```

---

### Task 4: Attach `userId` to scores and daily runs; leaderboard display

**Files:**
- Modify: `app/scores.py`
- Modify: `app/daily_runs.py`
- Modify: `app/yuwen_daily.py`
- Modify: `app/main.py` (pass userId from cookie into submit/run handlers)
- Modify: tests for scores / daily / yuwen as needed

**Interfaces:**
- Consumes: `user_id_from_cookie`, `get_user`
- Produces: new entries include `userId` and `username`; leaderboard `nickname` field shows username when `userId` present (keep key name for UI compat) or add `username` alongside

- [ ] **Step 1: Failing test — score entry has userId after login**

```python
def test_score_stores_user_id():
    client.post(url("/api/v1/auth/register"), json={"username": "cara", "password": "pass1234"})
    tid = "22222222-2222-4222-8222-222222222222"
    client.post(url("/api/v1/terminals/register"), json={"terminalId": tid, "nickname": "cara"})
    r = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal",
              "metrics": {"correct": 1, "total": 1, "timeMs": 900}},
        headers={"X-Terminal-Id": tid},
    )
    assert r.status_code == 200
    assert r.json()["entry"]["userId"]
    assert r.json()["entry"]["nickname"] == "cara"  # or username field per chosen schema
```

- [ ] **Step 2: Implement**

- Resolve user from cookie inside route handlers (or dependency)
- `submit_score(..., user_id: str, username: str)` — still may keep terminalId for device analytics / claim linkage
- Daily/yuwen run create paths set `userId` + display name from user

- [ ] **Step 3: Run** `pytest tests/test_scores.py tests/test_daily_api.py tests/test_yuwen_daily.py tests/test_users.py -v`

- [ ] **Step 4: Commit**

```bash
git add app/scores.py app/daily_runs.py app/yuwen_daily.py app/main.py tests/
git commit -m "feat(auth): bind scores and daily runs to userId"
```

---

### Task 5: Claim terminal history

**Files:**
- Modify: `app/users.py` — `claim_terminal(user_id, terminal_id) -> dict`
- Modify: `app/scores.py` / daily modules — reassign `terminalId` entries’ `userId`/`nickname`
- Modify: `app/main.py` — `POST /api/v1/auth/claim-terminal` body `{terminalId}`
- Modify: `tests/test_users.py`

**Interfaces:**
- Consumes: scores/daily load-save
- Produces: `claim_terminal` marks `claimedTerminals[terminalId]=userId`; rejects if already claimed; updates historical entries missing or matching that terminal to this user

- [ ] **Step 1: Failing test**

```python
def test_claim_terminal_once():
    # create legacy scores under terminal only (bypass user gate in unit test via users.claim helpers)
    ...
    users.claim_terminal(user_id, tid)
    with pytest.raises(ValueError, match="已认领|认领"):
        users.claim_terminal(other_user_id, tid)
```

Prefer API-level test: seed score with terminal before user middleware era using direct `scores.submit_score` in unit test, then claim via API while logged in.

- [ ] **Step 2: Implement migration**

- For each score entry with `terminalId == tid`, set `userId`, set display name to current username
- Same for daily_runs / yuwen runs stores
- Record claim in `users.json`

- [ ] **Step 3: Run tests — pass**

- [ ] **Step 4: Commit**

```bash
git add app/users.py app/scores.py app/daily_runs.py app/yuwen_daily.py app/main.py tests/test_users.py
git commit -m "feat(auth): claim old terminal scores onto user"
```

---

### Task 6: Login / register pages and client shell

**Files:**
- Create: `web/login.html`, `web/register.html`
- Modify: `app/main.py` — serve `/login`, `/register`
- Modify: `web/js/fgb-client.js` — `FGB.authMe`, `FGB.login`, `FGB.register`, `FGB.logout`; on 401 from play APIs redirect to login
- Modify: `web/index.html` — replace nickname-only modal flow with: if not logged in show link to login/register; if logged in show username + logout; keep optional claim prompt after login when terminal has unclaimed history (`GET /api/v1/auth/me` can include `claimAvailable: bool`)
- Modify: `web/play-gate.html` — after unlock, `next` may land on login

**Interfaces:**
- Pages use `fgb-theme.css`, match play-gate card style
- Register form fields: username, password, confirm, family passphrase (show passphrase field always; server ignores when gate off)

- [ ] **Step 1: Add pages + routes (manual smoke)** — open `/register`, `/login` return 200

- [ ] **Step 2: Wire client + hall top bar**

- [ ] **Step 3: After login, if `claimAvailable`, confirm dialog via `fgb-ui` askConfirm → `claim-terminal`

- [ ] **Step 4: Commit**

```bash
git add web/login.html web/register.html web/js/fgb-client.js web/index.html web/play-gate.html app/main.py
git commit -m "feat(auth): login/register pages and hall session UI"
```

---

### Task 7: Lobby summary + regression pass

**Files:**
- Modify: `app/lobby.py` to accept optional `user_id` and resolve “me” from user scores/runs
- Modify: `tests/test_lobby_summary.py`
- Run full suite

- [ ] **Step 1: Update lobby to prefer userId when provided**

- [ ] **Step 2: Run** `pytest -q`  
Expected: all pass

- [ ] **Step 3: Manual checklist**

1. Gate on → unlock → register → play schulte → score appears under username  
2. Logout → same browser login other user → separate scores  
3. Second device login same user → sees continuity  
4. Claim once on old terminal device  
5. Admin login still works  

- [ ] **Step 4: Commit**

```bash
git add app/lobby.py tests/
git commit -m "feat(auth): lobby summary uses user identity"
```

- [ ] **Step 5: Open PR** summarizing Tasks 1–7 against `main` (do not touch CF tunnel DNS)

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Family gate outer door | 2, 3 (unchanged play-gate + register check) |
| Self-register with family passphrase | 2 |
| Login session `fgb_user` | 1, 2 |
| Play requires login | 3 |
| Hall/leaderboards public | 3 |
| Scores on userId | 4 |
| Claim terminal once | 5 |
| Login/register UI + top bar | 6 |
| Cloud + home same storage | uses `load_json`/`save_json` (Turso-backed) throughout |
| Admin unchanged | never touch admin password APIs except reading gate |

## Notes for implementers

- Match cookie flags to existing `play_gate_unlock` `set_cookie` in `main.py`.
- When updating old tests that POSTed scores without login, register+login in fixture or use `TestClient` cookie after `/api/v1/auth/register`.
- Do not add bcrypt dependency unless you must; stay consistent with admin SHA-256+salt.
