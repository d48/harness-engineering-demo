---
name: article-to-repo
description: Turn an article into a new GitHub repository containing a self-contained slide deck and a runnable, real demo of its concepts. Use when the user gives an article URL (or pasted text) and asks to turn it into a repo, deck, slides, or demo — e.g. "/article-to-repo <url>", "make slides and a demo from this article".
---

# Article to Repo

Given an article, produce a new GitHub repo with:
1. a self-contained HTML slide deck summarizing it, and
2. one or more small, *real* (not mocked/printed) demos that make its key
   ideas tangible,

deployed so the deck is viewable at a public URL.

This repo (`harness-engineering-demo`) is itself a reference example produced
by this exact workflow, from Lilian Weng's "Harness Engineering for
Self-Improvement" article. When in doubt about shape, tone, or file layout,
look at `README.md`, `slides/harness-slides.html`, `demo/`, and
`.github/workflows/pages.yml` in this repo and match their conventions.

Make a todo list for the steps below and work through them in order.

## 1. Digest the article

Fetch the URL with WebFetch. Extract:
- Title, author, publication date/venue.
- The core thesis in 1-2 sentences.
- 4-8 major sections/concepts, each with the concrete mechanism it describes
  (not just the label — what actually happens, what the moving parts are).

If the fetch fails (paywall, JS-rendered, blocked), ask the user to paste the
article text rather than guessing at content.

## 2. Plan the narrative and demos

- Pick a repo name: kebab-case, derived from the article's topic, suffixed
  `-demo` (e.g. `harness-engineering-demo`, `token-optimization-demo`).
- Map each major concept to one slide-worthy beat AND, where the concept
  describes a *mechanism* (a loop, a protocol, an algorithm, a tradeoff you
  can simulate), a corresponding demo. Not every concept needs a demo —
  aim for 2-5 demos total, each mapped to a specific section.
- For each demo, prefer something **real**: actual file I/O, actual
  subprocesses, actual test runs, actual threads/parallelism, actual before/
  after measurements — over a script that just prints narration. It's fine
  for a "model" or data source inside a demo to be scripted/deterministic
  (for reproducibility on stage), as long as the harness/mechanism around it
  is genuine. See `demo/mini_harness/` in this repo for the pattern: a small
  real harness (tools, loop, trace output) wrapping a swappable scripted
  model.
- Each demo should end with a short "takeaway" that ties back to its slide.

## 3. Confirm scope with the user before creating anything

Creating a GitHub repo is visible and only cheaply reversible (deleting a
repo people may have already seen/starred is not free). Before calling any
creation tool, confirm with AskUserQuestion:
- Proposed repo name (let them override).
- Visibility: public (needed for GitHub Pages to be free/simple) or private.
- The planned demo list (one line each), so they can drop/add before you
  build.

Skip this confirmation only if the user already specified all of the above
explicitly in their request.

## 4. Create and bring the repo into scope

1. `mcp__github__create_repository` — create under the user's account (not
   an org, unless they said otherwise), with a short description derived
   from the article title, auto-init with a README.
2. Add it to the session: the `add_repo` tool (owner/repo), then
   `register_repo_root` once cloned, so you can work with normal file tools
   and `git` instead of one-file-at-a-time API calls.
3. Clone it locally (the `add_repo` tool result gives you the clone
   command).

## 5. Scaffold the repo

Match this repo's layout:

```
README.md
package.json                 # thin npm wrapper if demos are Python (see this repo's)
slides/
  <slug>-slides.html          # self-contained deck, no external deps
  index.html                  # meta-refresh + JS redirect to <slug>-slides.html
demo/
  run.py (or run.js/...)      # interactive menu: run one / run all / --fast smoke flag
  demoN_<name>.<ext>          # one file per demo
scripts/
  open-slides.js              # cross-platform "open the deck" helper (optional but nice)
.github/workflows/pages.yml   # deploy slides/ to GitHub Pages on push to main
.gitignore
```

Use whatever language fits the article's subject matter and the demos you
planned — Python is this repo's choice because it needed no dependencies;
pick what makes each demo runnable with zero or minimal setup.

### Slide deck

Build `slides/<slug>-slides.html` as a **single self-contained HTML file**:
no CDN links, no build step, no external fonts/JS. Copy the CSS/JS engine
(slide switching, arrow-key nav, `N` for speaker notes, `O` for an overview
grid, `--scale` responsive sizing) from `slides/harness-slides.html` in this
repo as a starting template, then replace the content: one slide per
narrative beat from step 2, using inline SVG for any diagrams. Keep the dark
theme and typography variables unless the article's subject strongly
suggests otherwise. `slides/index.html` just redirects to the real file (copy
this repo's verbatim, swapping the filename/title).

### Demos

For each demo:
- A short module-level docstring/comment: what it demonstrates and which
  article section it maps to.
- Real, observable behavior — printed trace of what's actually happening
  (files written, subprocess exit codes, thread results), not a canned
  narration.
- A `TAKEAWAY` at the end.
- Support a fast/smoke mode (env var or flag) that skips any deliberate
  pauses, so it can be tested non-interactively.

`demo/run.py` (or equivalent): menu of demos, `run.py N` for one, `run.py
all` for all, `all --fast` for a smoke test.

### GitHub Pages workflow

Copy `.github/workflows/pages.yml` from this repo verbatim (path trigger on
`slides/**`, `upload-pages-artifact` + `deploy-pages`). It only deploys; the
one-time "Settings → Pages → Source → GitHub Actions" step still has to be
done by the user in the GitHub UI — call this out at the end, don't claim
it's live yet.

### README

Structure: one-paragraph description + article link and citation, quick
start (how to run demos, zero-setup if possible), public URL section
(explain the one-time Pages setup step), a table mapping each demo to its
article concept, repo layout, and a suggested presentation flow. Use this
repo's `README.md` as the template.

## 6. Test before pushing

- Run every demo end-to-end in fast/smoke mode; fix anything that errors.
- Open the slide HTML in the pre-installed Chromium (Playwright, see
  environment notes — `executablePath: '/opt/pw-browsers/chromium'`) and
  check it renders without console errors and every slide is reachable via
  arrow keys.
- Sanity-check `npm run demo` / `npm run slides` equivalents actually work
  if you added them.

## 7. Commit and push

Commit to the new repo's default branch (`main`) directly — this is a fresh
scaffold, not a change to existing shared work, so no PR is needed unless
the user asks for one. Push with `git push -u origin main`.

## Wrap up

Report to the user:
- The repo URL.
- The demo list with one-line descriptions.
- That GitHub Pages needs the one-time manual "Source: GitHub Actions" step
  before the deck is publicly reachable, and what the URL will be once it's
  on (`https://<owner>.github.io/<repo>/`).
- Any article content you couldn't fetch/verify and had to take on faith.
