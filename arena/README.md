# Oracle-Q Arena — Publishing Guide

The mobile-friendly spectator page lives at `arena/index.html`. It is a **static preview**, not a live trading terminal.

## Publish a real scorecard

1. Obtain a scorecard produced by `research.challenger_score.score_shadow_league` from independently reviewed, complete-window prospective paper evidence.
2. Run from the repository root:
   ```sh
   python -m research.publish_arena --scorecard /path/to/reviewed-scorecard.json --out arena/arena-feed.json
   ```
3. Inspect the output. It must state `"live": false`, `"orders_enabled": false`, and `"edge_proven": false`.
4. Host the `arena/` directory as static files on a reviewed publishing branch or deployment. The browser requests `./arena-feed.json` and offers manual refresh.

Do **not** substitute sample, historical backtest, or synthetic returns into the public feed. Without a reviewed scorecard, leave the feed absent: the page correctly displays **NO VERIFIED LIVE FEED**.

## Deployment safety

This PR does not enable GitHub Pages, create a public deployment, or add a write-capable workflow. Public hosting should be configured after code review and explicit approval of the publication source and privacy boundaries.

## Future live mode

A live feed needs an independently validated timestamped observation publisher, bounded refresh cadence, source-health indicators, immutable evidence references, and reconciliation checks. A page refresh alone is not proof of live or profitable trading.

## Build a preview without deploying

From the GitHub Actions tab, manually run **Oracle-Q Arena Static Preview** on the reviewed branch. It validates the HTML, rejects a checked-in unreviewed feed, and produces a downloadable seven-day static-site artifact. This is **not** a public website or live feed. Hosting requires a separate reviewed deployment configuration.
