# Interaction refactor (整套交互重构) — Design

Date: 2026-10-18  
Status: draft for user review  
Product: family-game-box  
Related: lobby-theme (2026-09-01), user-accounts (2026-10-18), game_common generators

## Goal

Phased, full-surface interaction refactor so the family box feels like one product: consistent chrome and flows, per-game skins with shared interaction rules, and comfortable touch use on tablets.

Success looks like:

- Members rarely get lost between gate → login → hall → play → results
- Shell pages and games share the same controls language; each game may keep a distinct skin
- Backend auth/scoring APIs stay as shipped on `main` (user accounts); this work is front-end interaction + presentation

## Non-goals

- SPA rewrite / introducing React/Vue (unless a later phase reopens this)
- Changing play-gate, user session, or score binding semantics
- Rewriting game *rules* / puzzle generators (logic stays; UI chrome and layout may change)
- Admin console information architecture overhaul (theme alignment only unless needed for shared chrome)
- New illustration asset pack as a blocker for phase 1

## Current baseline

- Vanilla multi-page HTML + shared `fgb-theme.css`, `fgb-client.js`, `fgb-ui.js`
- Shells: play-gate, login/register, hall, daily shells, leaderboards, admin
- Games: mostly Python-generated monolithic HTML under `web/games/*`; yuwen and 24points partially split
- Known debt: duplicated form CSS / `safeNext`, toast CSS outside theme, game pages without shared result chrome

## Approach (chosen)

**Shell-first, multi-page + shared modules**

1. Design system + shared shell JS/CSS  
2. Apply shell to gate/auth/hall/daily/leaderboards + straighten entry flow  
3. Game play UIs: shared interaction chrome; per-game skins; generator templates updated  
4. Touch / landscape polish  

Rejected:

- **SPA**: smoothest navigation, highest rewrite cost and risk to existing generators  
- **Theme-only restyle**: fastest, but does not fix flow duplication or game interaction inconsistency (user asked for full interaction + deep game UI)

## §1 Phased roadmap

| Phase | Deliverable | Notes |
|-------|-------------|--------|
| **P0** | Design system | Tokens, buttons, forms, top bar, toast/confirm consolidated into theme + thin JS helpers |
| **P1** | Shell pages + entry flow | play-gate, login, register, hall, daily shells, leaderboards; gate→login→hall→claim copy/links |
| **P2** | Game UI pass | Shared chrome (top bar, pause, result, play-again); per-game skins; regenerate via `game_common` |
| **P3** | Touch polish | Hit targets, safe areas, landscape bottom compress alignment with existing landscape spec |

Ship each phase to production when review-ready; do not block P0/P1 on finishing every game skin.

## §2 Design system

- Single source of tokens in `web/css/fgb-theme.css` (extend lobby-theme tokens; resolve “light header vs dark hall” inconsistency)
- Move toast/confirm styles from injected CSS in `fgb-ui.js` into the theme; keep JS behavior thin
- New shared module e.g. `web/js/fgb-shell.js`: render top bar (brand, back, username, logout), wire `safeNext` / auth redirects once
- Shared form patterns for gate/login/register (one stylesheet section or small partial pattern, not three copies)

## §3 Shell pages & entry flow

Keep multi-page URLs (bookmarkable, matches current middleware redirects).

Flow:

1. Optional family gate → unlock  
2. Login / register (register still requires family passphrase)  
3. Hall: session chip, daily cards, free-train grid, claim-terminal prompt  
4. Into daily shell or game → results → back to hall or leaderboard  

P1 acceptance:

- No hardcoded divergent auth links across shells  
- Claim prompt and “switch account” use the same shell chrome  
- Hall and public boards remain readable without personal login (unchanged product rule)

## §4 Game layer

**Shared interaction rules (all games):**

- Consistent top bar (title, back, optional pause)  
- Consistent result overlay (score summary, retry, hall, leaderboard when applicable)  
- Shared button sizes / focus / touch targets  

**Per-game skins:**

- Each game may define palette / decorative accents / board treatment within token constraints  
- Skins must not invent separate navigation or result patterns  

**Implementation:**

- Extend `games/common/game_common.py` (and yuwen/24points templates) to emit shared chrome hooks + skin class hooks  
- Prefer regenerating built-in game HTML over hand-editing each monolith  
- Play logic and scoring API calls stay; layout/DOM chrome may be restructured  

Pilot order for P2 (default unless changed later): schulte + one daily-embedded game, then remaining free-train games, then yuwen / 24points specifics.

## §5 Tech constraints

- Stay on vanilla multi-page + shared JS/CSS  
- No new frontend build step required for P0–P1; P2 continues existing Python game build  
- `FGB` client API surface unchanged unless a shell helper needs a thin wrapper  
- Vercel static serving of `web/` unchanged  

## §6 Risks

| Risk | Mitigation |
|------|------------|
| Generated game drift | Always regenerate from templates; CI or script check that committed `web/games` matches build |
| Scope creep into SPA | Hard gate: no router framework in P0–P2 |
| Breaking play-gate / auth redirects | Keep URL paths; reuse `fgb-client` session helpers; regression API checklist + smoke click path |
| Skin inconsistency | Document allowed skin variables; review checklist per game |

## Open decisions (deferrable)

- Exact pilot games for first P2 PR (default above)  
- Whether admin gets full shell chrome in P1 or only theme tokens  
- Whether daily challenge iframe games share the outer result chrome or only inner  

## Approval

User direction captured:

- Phased full refactor (visual + flow + touch over time)  
- Shell-first approach  
- Game UI deep change with **per-game skins** and **unified interaction rules**  
- Tech: multi-page + shared shell (recommended)
