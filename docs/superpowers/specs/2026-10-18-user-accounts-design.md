# User accounts (家庭口令 + 个人账号) — Design

Date: 2026-10-18  
Status: approved for planning  
Product: family-game-box  
Related: play-gate (`fgb_play`), terminals/nicknames, daily + yuwen daily scores

## Goal

Add a personal user module on top of the existing family play-gate:

1. Family passphrase remains the outer door.
2. After the gate, members self-register with username + personal password (family passphrase checked again at register).
3. Playing games requires personal login (cross-device continuity + same-device account switching).
4. First login can optionally claim this device’s old terminal/nickname scores onto the new account.

Out of scope for this version: OAuth, admin-created-only users, invite codes, UI visual redesign of game pages, changing admin password model.

## Current state (baseline)

- **Play-gate:** optional family passphrase → cookie `fgb_play`; middleware guards games, daily pages, and score APIs.
- **Terminals:** per-device `terminalId` + nickname (no personal password). Scores and daily runs hang off `terminalId`.
- **Admin:** separate admin password / token; unchanged by this design.

## Approach

**A — User accounts + session cookie (chosen)**

Register/login issue a signed session cookie `fgb_user`. Game routes and score-writing APIs require a valid user session (in addition to play-gate when enabled). Hall and leaderboards stay publicly readable.

Rejected:

- **B** Weak login (score-only): fails “must login to play” and same-device switching.
- **C** Third-party OAuth: too heavy for a family box.

## §1 Flow and gates

1. Family passphrase still controls the outer door (`fgb_play`). When play-gate is enabled, behavior matches today until unlocked.
2. Register/login pages are reachable only after the gate (same as other protected app pages, or explicitly allowlisted behind gate as needed).
3. **Register fields:** username, personal password, confirm password, family passphrase (re-validated against the configured play-gate secret).
4. **Login** sets `fgb_user` session cookie; **logout** clears it.
5. Unauthenticated access to `/games/*`, `/uploaded-games/*`, daily challenge play pages, and score/run-writing APIs redirects to `/login?next=…` (or returns 401 for API calls).
6. Hall (`/`), public leaderboards remain viewable without personal login.
7. Top bar shows username with switch-account / logout.

## §2 Data and migration

### User record

Store under Turso/JSON store (same persistence layer as other app docs), e.g. document `users`:

| Field | Notes |
|-------|--------|
| `userId` | Stable id |
| `username` | Unique, display name on boards |
| `passwordHash` | Never store plaintext |
| `createdAt` | ISO timestamp |

Sessions: signed cookie (preferred) or server-side session map keyed by opaque token; cookie name `fgb_user`.

### Scores and runs

- New scores / daily runs / yuwen runs attach to `userId`.
- Leaderboards display `username`.
- Existing `terminalId` nickname data is retained.

### Claim old terminal scores

- After first login (or from settings), offer **认领本机旧成绩**.
- Migrates historical scores/daily runs for this browser’s `terminalId` onto the current `userId`.
- Each terminal may be claimed **once**.
- User may skip; account starts fresh.

### Admin

Admin password / `require_admin` remains separate from personal accounts.

## §3 APIs and pages

### APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/auth/register` | Create user; body includes family passphrase |
| POST | `/api/v1/auth/login` | Issue `fgb_user` |
| POST | `/api/v1/auth/logout` | Clear session |
| GET | `/api/v1/auth/me` | Current user or anonymous |
| POST | `/api/v1/auth/claim-terminal` | Bind this terminal’s history to current user |

Error responses use clear Chinese messages: username taken, bad password, bad family passphrase, already claimed, etc.

### Pages / client

- `/login`, `/register` (styled with existing `fgb-theme`).
- Top bar login state on hall and related shells.
- `fgb-client` sends session cookie; score/daily helpers use authenticated user identity instead of treating bare terminal as identity.
- Password hashing on the server (e.g. bcrypt/argon2 or platform-appropriate KDF). No plaintext in logs or store.

### Middleware / gate interaction

Order of checks when play-gate is enabled:

1. Play-gate cookie for paths that `needs_play`.
2. For play/score paths: valid `fgb_user` (or admin token where already allowed).

When play-gate is disabled, personal login is still required for playing games.

## Success criteria

- New member can unlock with family passphrase, register, log in, and play on another device with the same username/password.
- Two people on one device can log out / log in and keep scores separate.
- Optional one-time claim moves old nickname scores to the account.
- Existing admin and play-gate admin settings keep working.
- Cloud (Vercel + Turso) and home install share the same behavior.

## Non-goals / later

- Email/phone recovery, MFA.
- Roles beyond admin vs player.
- Forcing login for hall browsing.
- Full visual redesign of per-game UIs (parked).

## Implementation note

Next step after this spec is approved in-repo: write an implementation plan via writing-plans (`docs/superpowers/plans/…`), then implement behind PRs without changing Cloudflare tunnel DNS for `game.mx1024.com`.
