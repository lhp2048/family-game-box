# Interaction Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phased front-end interaction refactor so gate → login → hall → play → results feel like one product: shared design system and shell, straightened entry flow, then per-game skins with unified play chrome, then touch polish.

**Architecture:** Stay multi-page vanilla HTML/JS. Consolidate tokens and overlays into `fgb-theme.css`; add `fgb-shell.js` for top bar / auth chip / `safeNext`. Shell pages adopt the module first; games get shared chrome via `game_common` templates with per-game skin hooks. No SPA, no new framework, no auth/API semantics changes.

**Tech Stack:** Existing `web/` static assets, `games/common/game_common.py` generators, pytest for any tiny pure helpers if introduced, manual/browser smoke for UI.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-18-interaction-refactor-design.md`
- Do not change play-gate / `fgb_user` / score binding behavior
- Hall `/` and public leaderboards stay readable without personal login
- No React/Vue/router; no new frontend bundler required for P0–P1
- Per-game skins allowed; interaction rules (top bar, pause, result, play-again) must be shared
- Prefer regenerating `web/games/*` from Python templates over hand-editing monoliths
- Chinese UI copy; keep existing auth error messages
- Small commits; ship P0+P1 before starting every game skin

## File map

| File | Role |
|------|------|
| `web/css/fgb-theme.css` | Tokens, buttons, forms, top bar, toast/confirm, result overlay |
| `web/js/fgb-ui.js` | Toast/confirm behavior only (styles move to theme) |
| `web/js/fgb-shell.js` | **New** shared top bar + session chip + `safeNext` helpers |
| `web/js/fgb-client.js` | Reuse; only thin helpers if shell needs them |
| `web/play-gate.html` / `login.html` / `register.html` | Auth shells on shared form + shell chrome |
| `web/index.html` | Hall shell + claim prompt using shell |
| `web/daily.html` / `yuwen-daily.html` | Daily shells |
| `web/leaderboard.html` / `daily-leaderboard.html` / `yuwen-daily-leaderboard.html` | Boards |
| `web/admin.html` | Theme tokens only in P1 (optional full shell later) |
| `games/common/game_common.py` (+ yuwen/24points templates) | Emit shared chrome + skin class hooks |
| `web/games/**` | Regenerated output |
| `tests/` | Only if new pure JS isn’t testable; prefer API regression + checklist |

---

### Task 1: Design system — tokens + move overlays into theme

**Files:**
- Modify: `web/css/fgb-theme.css`
- Modify: `web/js/fgb-ui.js`
- Test: visual smoke on hall + one toast/confirm path

**Interfaces:**
- Consumes: existing lobby-theme tokens
- Produces: documented CSS classes for `.fgb-toast`, `.fgb-confirm`, `.fgb-btn`, `.fgb-field`, `.fgb-topbar` (names may match/extend current theme; do not invent a second parallel system)

- [ ] **Step 1: Inventory** current toast/confirm injected CSS in `fgb-ui.js` and duplicate form CSS in gate/login/register
- [ ] **Step 2: Move** overlay styles into `fgb-theme.css`; strip injected `<style>` from `fgb-ui.js` (keep behavior)
- [ ] **Step 3: Align** tokens so header/hall are one coherent dark-hall system (fix the light-vs-dark inconsistency noted in theme comments)
- [ ] **Step 4: Smoke** — open hall, trigger a confirm/toast from any existing caller; verify look
- [ ] **Step 5: Commit** `style(ui): consolidate toast/confirm into fgb-theme`

---

### Task 2: Shared shell module (`fgb-shell.js`)

**Files:**
- Create: `web/js/fgb-shell.js`
- Modify: `web/js/fgb-client.js` only if a tiny shared helper is clearly duplicated
- Test: load from a scratch HTML snippet or hall after Task 3; until then unit-free

**Interfaces:**
- Consumes: `FGB` from `fgb-client.js` (`me`, `logout`, `basePath` as already exist)
- Produces (exact names — adjust only if existing code already uses equivalents; document in commit):
  - `FGBShell.mountTopbar(rootEl, options)` where `options` may include `{ title, showBack, backHref, showUser }`
  - `FGBShell.safeNext(defaultPath)` — single implementation replacing per-page copies
  - `FGBShell.requireUserOrRedirect()` — thin wrapper around existing client session check if useful

- [ ] **Step 1: Write** `fgb-shell.js` with mountTopbar + safeNext (no framework)
- [ ] **Step 2: Document** in file header which pages should include it and script order (`fgb-client` → `fgb-ui` → `fgb-shell`)
- [ ] **Step 3: Commit** `feat(ui): add fgb-shell shared topbar helpers`

---

### Task 3: Auth pages on shared form + shell

**Files:**
- Modify: `web/play-gate.html`, `web/login.html`, `web/register.html`
- Modify: `web/css/fgb-theme.css` if form section needs one more class
- Test: manual — gate unlock → register → login → redirect `next`

**Interfaces:**
- Consumes: `FGBShell.safeNext`, theme form classes, existing `/api/v1/auth/*` and play-gate APIs
- Produces: pages without duplicated inline form CSS / `safeNext`

- [ ] **Step 1: Refactor** login.html to theme form classes + shell topbar (minimal brand bar OK if logged-out)
- [ ] **Step 2: Refactor** register.html the same way
- [ ] **Step 3: Refactor** play-gate.html the same way
- [ ] **Step 4: Smoke** gate on → register → login with `?next=` preserving target
- [ ] **Step 5: Commit** `feat(ui): unify gate/login/register chrome`

---

### Task 4: Hall + claim prompt on shell

**Files:**
- Modify: `web/index.html`
- Test: manual — logged-in chip, logout, claim prompt when unbound history exists

**Interfaces:**
- Consumes: `FGBShell.mountTopbar`, existing lobby summary / claim APIs
- Produces: hall using shared topbar; claim UI uses theme buttons/confirm

- [ ] **Step 1: Replace** ad-hoc hall header with `FGBShell.mountTopbar`
- [ ] **Step 2: Wire** claim prompt through `fgb-ui` confirm + theme
- [ ] **Step 3: Smoke** login → hall shows username; logout; claim once path if data available
- [ ] **Step 4: Commit** `feat(ui): hall uses fgb-shell`

---

### Task 5: Daily shells + leaderboards

**Files:**
- Modify: `web/daily.html`, `web/yuwen-daily.html`
- Modify: `web/leaderboard.html`, `web/daily-leaderboard.html`, `web/yuwen-daily-leaderboard.html`
- Test: manual navigation from hall cards into each shell/board and back

**Interfaces:**
- Consumes: `FGBShell.mountTopbar`, theme
- Produces: consistent back/title/user chip; no divergent auth links

- [ ] **Step 1: Apply** shell to daily + yuwen-daily
- [ ] **Step 2: Apply** shell to three leaderboard pages
- [ ] **Step 3: Grep** `web/*.html` for hardcoded `/login` / duplicate `safeNext`; eliminate leftovers on shell pages
- [ ] **Step 4: Smoke** hall → daily → board → back
- [ ] **Step 5: Commit** `feat(ui): daily and boards on shared shell`

---

### Task 6: P1 regression checklist (entry flow)

**Files:**
- Create or update: `.superpowers/sdd/` note or checklist in plan progress only — optional `docs/` not required
- Test: full manual + existing pytest suite green (no intentional API changes)

- [ ] **Step 1: Run** `pytest -q` — must stay green
- [ ] **Step 2: Manual checklist**
  - [ ] Gate unlock → register → login → hall
  - [ ] Logout → other user login on same device
  - [ ] `?next=` into a game URL after login
  - [ ] Hall + public leaderboard without login still viewable
  - [ ] Claim prompt appears only when appropriate; second claim blocked
- [ ] **Step 3: Commit** only if fixes needed; otherwise note “P1 complete” in PR description

---

### Task 7: Game chrome hooks in `game_common`

**Files:**
- Modify: `games/common/game_common.py` (and any shared template partials it uses)
- Modify: yuwen / 24points templates if they bypass `game_common`
- Test: regenerate one game (schulte) and open locally

**Interfaces:**
- Consumes: theme CSS path, `fgb-shell.js` / `fgb-client.js` script tags with correct `basePath`
- Produces: generated HTML with:
  - shared top bar mount point
  - shared result overlay markup/classes
  - body/root `data-game-skin="schulte"` (or class) for per-game skin

- [x] **Step 1: Design** minimal DOM contract for result overlay (retry / hall / leaderboard links)
- [x] **Step 2: Implement** hooks in `game_common` without changing score submit logic
- [x] **Step 3: Regenerate** schulte; fix until play + submit still works
- [x] **Step 4: Commit** `feat(games): shared chrome hooks in game_common`

---

### Task 8: Pilot skins — schulte + one daily-embedded game

**Files:**
- Modify: skin CSS section in theme or per-game skin block emitted by generator
- Regenerate: schulte + chosen daily-embedded game page
- Test: play through + score submit

- [ ] **Step 1: Pick** second pilot (default: whatever daily embeds first — often schulte/stroop/etc.; document choice in commit)
- [ ] **Step 2: Implement** schulte skin variables within token constraints
- [ ] **Step 3: Implement** second pilot skin
- [ ] **Step 4: Smoke** both end-to-end
- [ ] **Step 5: Commit** `feat(games): pilot skins for schulte + <name>`

---

### Task 9: Remaining free-train games

**Files:**
- Regenerate: remaining `web/games/*` via build scripts
- Test: smoke each game launch + one score path where applicable

- [ ] **Step 1: List** remaining games from hall grid
- [ ] **Step 2: Regenerate** all with shared chrome; add light per-game skin accents
- [ ] **Step 3: Smoke** each opens and returns to hall
- [ ] **Step 4: Commit** `feat(games): apply shared chrome to remaining free-train games`

---

### Task 10: yuwen + 24points specifics

**Files:**
- Modify: `web/games/yuwen/*`, `web/games/24points/*` templates/sources
- Test: yuwen daily + 24points play/library smoke

- [ ] **Step 1: Port** yuwen play shell to shared chrome + skin
- [ ] **Step 2: Port** 24points play + library chrome (library can be lighter)
- [ ] **Step 3: Smoke**
- [ ] **Step 4: Commit** `feat(games): yuwen and 24points shared chrome`

---

### Task 11: Touch / landscape polish (P3)

**Files:**
- Modify: `fgb-theme.css`, shell/game chrome as needed
- Related prior art: `docs/superpowers/specs/2026-09-02-landscape-bottom-compress-design.md`
- Test: tablet-width DevTools + real device if available

- [ ] **Step 1: Audit** hit targets (<44px) on shell + result overlays
- [ ] **Step 2: Align** landscape bottom compress with shared chrome
- [ ] **Step 3: Smoke** portrait/landscape on hall + one game
- [ ] **Step 4: Commit** `fix(ui): touch and landscape polish`

---

### Task 12: Whole-branch review + PR

**Files:**
- PR from `feat/interaction-refactor` → `main`
- Test: pytest green; P1+P2 checklist in PR body

- [ ] **Step 1: Run** `pytest -q`
- [ ] **Step 2: Self-review** against spec §1–§4
- [ ] **Step 3: Push** and open PR with phased notes (what shipped vs follow-ups)
- [ ] **Step 4: Do not merge** until user asks to deploy

---

## Execution notes

- Prefer shipping **Tasks 1–6** as first PR if P2 threatens to balloon
- Tasks 7–11 may be a second PR on the same branch or `feat/interaction-refactor-games`
- Never force-push; never change API auth rules “for convenience”
