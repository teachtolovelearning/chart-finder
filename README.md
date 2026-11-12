# Anchor Chart Club Chart Finder

A searchable guide to every Anchor Chart Club chart, with each chart's standards for any US state.

Live at **https://finder.anchorchartclub.com** (GitHub Pages, served from `docs/`). Saving a change to `docs/` on the `main` branch updates the live page within a minute or two.

## What's where

| Folder | What it holds |
|---|---|
| `docs/` | The live site: `index.html` plus `states/<ABBR>.json` (each state's matched standards, loaded when a teacher picks that state). `CNAME` sets the custom domain. |
| `src/` | The page template (`app.html`) and the logo and favicon it embeds. Edit the design here, not in `docs/index.html`. |
| `data/alln.json` | The 1,780 academic charts parsed from the six grade-level lookbooks (Google Sheets in Drive), with links and Common Core / NGSS / TEKS / Florida alignments. |
| `data/bonus.json` | The 78 SEL & Character and Classroom Management charts from the Kajabi product "Anchor Chart Club Bonuses" (ACC site 2147513805), marked grade K5 with no standards. |
| `std/state-standards-k5.json.gz` | K–5 standards for all 50 states + DC from the Learning Commons Knowledge Graph v1.16.0 (CC BY 4.0). |
| `std/final/<ABBR>.json` | Each state's chart-to-standard matches. |
| `llm/` | Reviewer rules (`INSTRUCTIONS.md`), the per-state plan (`plan.json`) and every reviewed match (`*.out.json`). |
| `research/state_standards.json` | Which standards each state uses and how they relate to Common Core / NGSS. |
| `scripts/` | The build and alignment scripts. |

## Rebuild the page

```
python3 -I scripts/build.py docs/index.html data/alln.json data/bonus.json
```

Run from the repository root. This rewrites `docs/index.html` and `docs/states/*.json`. Commit both.

Chart order matters: state files point at charts by position. Academic charts sort by grade then subject, and the K5 bonus charts sort after all of them, so adding bonus charts never shifts the academic ones. If academic charts are added or removed, re-run the state matching below for every state.

## Common updates

- **Fix a link or chart name:** edit `data/alln.json` or `data/bonus.json`, then rebuild.
- **Change the design or wording:** edit `src/app.html`, then rebuild.
- **New charts in the lookbooks:** export the sheet to xlsx, run `scripts/xlsx_to_text.py` and `scripts/parse_lookbook.py`, then `scripts/normalize.py`, rebuild `data/alln.json`, then match the new charts for each state (`scripts/prep_state.py <ABBR>` writes review packets; reviewers follow `llm/INSTRUCTIONS.md` and write `<packet>.out.json`; `scripts/finalize.py ALL` assembles `std/final/`), then rebuild.
- **New SEL or procedures charts in Kajabi:** read the Bonuses product (read only, ACC site only), add entries to `data/bonus.json` with links in the form `https://membership.anchorchartclub.com/products/anchor-chart-club-bonuses/categories/<category id>/posts/<post id>`, then rebuild.

Kajabi rule: only ever read from the Anchor Chart Club site (2147513805). Never mix it up with the Morning Meeting site.
