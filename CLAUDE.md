# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Prep materials for the 静岡県 (Shizuoka Prefecture) 調理師試験 (cooking-license exam): a 虎の巻 (cheat sheet, `toranomaki/`) and a self-contained study web app (`site/index.html`). Full background — exam rules, why Shizuoka's own past exams are the only reliable source material, scoring thresholds, study plan — is in [静岡県調理師試験_対策プロジェクト_引き継ぎ資料.md](静岡県調理師試験_対策プロジェクト_引き継ぎ資料.md); read it before making content decisions.

**Not a git repository** — there is no version-control safety net here. Be careful with destructive edits (no easy revert), and prefer additive/reversible changes.

## Data pipeline

Everything flows one direction, PDF → JSON → generated site. Each stage's script lives in `data/` and is run manually with `python3` (no test suite, no build system, no package manifest — dependencies `pypdf` and `markdown` are just expected to be installed in whatever Python environment is active):

1. `python3 data/extract_questions.py` — parses the official past-exam PDFs in `info/` (令和5-7年度, problems + answer keys) into `data/questions.json` (180 questions, 60/year) and `data/questions_review.txt` (for manual proofreading of the regex-based PDF extraction). Question numbers 1-60 map to the 6 subjects via fixed ranges (`SUBJECT_RANGES`); known PDF-extraction glitches that can't be fixed generically are patched via `MANUAL_FIXUPS` keyed by question id (e.g. `"R5-16"`).
2. `python3 data/merge_explanations.py` — merges `data/explanations_*.json` (per-subject explanation content, one file per subject, presumably produced by separate agent/LLM passes) into `data/questions.json`, filling each question's `theme`/`explanation`/`choiceNotes` fields. Asserts every question across all 8 explanation files gets merged and the total is exactly 180.
3. `python3 data/build_toranomaki.py` — converts the 6 chapter files in `toranomaki/*.md` (plain Markdown with a `{{practice:テーマ名}}` macro that becomes a link into the site's practice mode for that theme) into `data/toranomaki.json`.
4. `python3 data/build_site.py` — the final assembly step. Takes `site/index.template.html`, inlines `data/questions.json`, `data/toranomaki.json`, and base64-encodes the 7 PNGs in `images/` (mapping in `IMAGE_FILES`), and writes the fully self-contained `site/index.html` (~3.5MB, no external requests at runtime).

**When editing `site/index.template.html` or any `data/*.json`, rerun `python3 data/build_site.py` afterward** — `site/index.html` is a generated artifact, never hand-edit it directly. The build is idempotent/deterministic from its inputs.

`toranomaki/*.md` chapter files follow a fixed structure that `build_toranomaki.py` parses positionally: one `# ` H1 (chapter title), optional intro prose before the first `## `, then `## ` sections (topics) each rendered as its own card, with `### ` allowed inside as subheadings.

## Site architecture (`site/index.template.html`)

Single HTML file, vanilla JS (IIFE, no framework/bundler), roughly 1200 lines: `<style>` block, then three `<script type="application/json">` data islands (`quiz-data`, `toranomaki-data`, `images-data`) that the app script parses at load. Structure:

- **State**: a single `state` object persisted to `localStorage` under key `chorishi-v1` (`loadState`/`saveState`) — tracks per-question answer history (`state.answers`), mock exam results (`state.mocks`), study streak, and theme. There is a backup/restore overlay (`renderBackupOverlay`/`wireBackupOverlay`) since state lives only in the browser's localStorage with no server sync.
- **Routing**: hand-rolled, no History API — `route` is an in-memory object (`{tab, ...params}`) and `nav(tab, params)` re-renders synchronously via `render()`. Tabs: home, practice (一問一答), mock exam (模擬試験, 120-min timed), review (間違えた問題の復習), toranomaki (虎の巻 viewer with search).
- **Question model**: each question has `format` (`正誤` plain true/false-style, `空欄補充` fill-in-the-blank with a `passage`, or `組合せ` combination-of-blanks with an `optionHeader`) — rendering logic (`renderPracticeQuestion`, `renderBlanks`) branches on this field.
- Icons are hand-authored inline SVG (`ICONS` object) — no icon library or emoji, by design.
