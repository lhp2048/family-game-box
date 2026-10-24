# Productized Game Box UI (console shell)

## Direction

Turn the Family Game Box home from a generic “competitive hall” grid into a **living-room game console** experience: bezel framing, HUD stats, spotlight daily tiles, and a horizontal **game library shelf** with cover art and keyboard focus.

## Before (main)

- Title kicker “竞技厅”; flat stat strip + split arena cards + small train grid.
- Games rendered as uniform small cards (`fgb-train-card`) without cover metaphor or shelf navigation.

## After (feat/productized-gamebox-ui)

- **Design tokens** in `web/css/fgb-theme.css`: `--console-*`, focus ring, motion tokens.
- **Console shell** on `web/index.html`: `body.fgb-console`, hero, clock, HUD tiles, spotlight rows, shelf.
- **Components**: `FGBShell.mountTopbar({ console: true })`, `web/js/fgb-home.js` for covers + arrow-key focus.
- Other shell pages keep existing theme; no API changes.

## Follow-ups (out of scope for PR 1)

- Apply console nav variant to daily / leaderboard pages.
- Per-game cover illustrations (SVG) instead of glyph gradients.
- Gamepad / TV remote D-pad navigation across spotlight + shelf.
