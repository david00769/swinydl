# AGENTS.md

This file connects this repository to Buildshop's shared skill library.

## Core Rules

- Always check `/Users/david/Documents/memory-system/shared-agent-library/skills/` before creating new process instructions. That directory is a standalone clone of the shared library.
- Reference skills by exact markdown filename.
- Structured skills use their folder path plus `SKILL.md`.
- Prefer Buildshop skills first; add local project rules only when no shared skill fits.
- Use shared Buildshop skills in place by default; do not vendor or copy generic Buildshop skills into this repo unless customization is required.
- If a local customization is necessary, keep it thin and explicit: wrap, symlink, or fork only the specific skill that needs project-specific behavior.
- For non-trivial implementation, use `critique-plan-and-land/SKILL.md`: challenge the plan before coding, then verify function and design through the repository's existing landing gates before closeout.
- Use absolute paths when instructions depend on local workspace layout.
- Default to solo-dev velocity: prioritize rapid prototyping and avoid enterprise-heavy CI/CD unless explicitly requested.
- Solo-developer mode: commit and push directly on `master`, this repository's default branch. Feature branches and pull requests are not the default; use a branch or worktree only when it actually helps (parallel work on the same surface, or a change you may abandon), then fold it into `master` and delete it. Local checks and `critique-plan-and-land` gate the commit instead of a PR review.

## Model Weights

- SWinyDL's own CoreML models are not in a Hugging Face cache. `swinydl bootstrap-models` downloads them with `huggingface_hub.snapshot_download(local_dir=...)` into `vendor/parakeet-tdt-0.6b-v3-coreml` and `vendor/speaker-diarization-coreml` in the SWinyDL folder or checkout; run it from that folder. At runtime the backend reads them from `vendor/` next to the `swinydl` package. Both paths are gitignored.
- To use models stored elsewhere, set `ECHO360_PARAKEET_COREML_DIR` and `ECHO360_DIARIZER_COREML_DIR`. Keep the `vendor/` default for the DMG and for users; the installer and doctor depend on it.
- Any other downloaded model weights used while working on this repo belong in the per-Mac shared cache described in memory-system `docs/ai-model-cache.md`: `HF_HOME=~/Developer/.ai-models/huggingface` (the hub is `~/Developer/.ai-models/huggingface/hub`). Do not point `XDG_CACHE_HOME` at it and do not set `TRANSFORMERS_CACHE`. Do not create other repo-local model caches unless isolated benchmarking is intentional.

## Session Bootstrap (Optional, Run Once Per Repo)

1. `Use skill: connect-to-buildshop`
2. `Use skill: codebase-skill-recommender`
3. `Use skill: high-level-intent-router`
4. Log completion:
   - `/Users/david/Documents/memory-system/shared-agent-library/optional-tools/workflow-log.sh mark onboarding-buildshop done "bootstrap skills run"`
5. Skip bootstrap if already done:
   - `/Users/david/Documents/memory-system/shared-agent-library/optional-tools/workflow-log.sh is-done onboarding-buildshop`

## Multi-Agent Safety (Required If >1 Agent)

- If more than one agent is active, start with `Use skill: multi-agent-coordination`.
- Create or use one backlog board as the source of truth before autonomous work starts.
- Every intended autonomous scope must have a backlog ticket before dispatch or launch.
- Do not create floating scopes; if new work is discovered mid-flight, write it onto the backlog board before continuing.
- Every agent must set a unique `AGENT_ID` and register before editing files.
- No writes without a lock for the target scope.
- Release locks immediately when work is done.
- Any active scope must produce a same-day handoff in `.buildshop/coordination/handoffs/YYYY-MM-DD/`.
- Every handoff must include machine-readable `Ticket`, `Outcome`, and `Lock Action` fields.
- Before commit, check for lock collisions:
  - `AGENT_ID="<agent-id>" /Users/david/Documents/memory-system/shared-agent-library/optional-tools/check-active-locks.sh`
- Register, lock and release with `/Users/david/Documents/memory-system/shared-agent-library/optional-tools/agent-lock.sh` (`register`, `acquire`, `heartbeat`, `release`).

## High-Level Prompting

- You can give high-level intent; the agent should map to the right Buildshop skills and fill in details.
- Example prompts:
  - `Abstract this task and execute with Buildshop skills`
  - `Use the high-level-intent-router skill`
  - `Recommend the top Buildshop skills for this repo and start with the highest impact`

## Suggested Skills By Need

1. `documentation-and-hints.md` to keep `README.md`, `docs/` and these hints aligned with the code and the packaging path.
2. `testing-and-ci.md` and `testing-strategy.md` for CLI and macOS/Safari regression coverage.
3. `sosumi-apple-docs/SKILL.md` and `swiftui/SKILL.md` for the Safari app and extension.
4. `yttranscribe/SKILL.md` when transcript pipeline work overlaps with local media ingestion.
5. `compound-learnings.md` after significant work to update Buildshop permanently.

## Project Hints

- Intended local home: `/Users/david/Documents/memory-system/personal-projects/echo360`. This is a standalone publish repository; memory-system ignores it. `/Users/david/Documents/memory-system` is the memory-system canonical root.
- Python package: `swinydl`. CLI entry point: `swinydl` (`swinydl.main:main`), run as `uv run swinydl ...`. Subcommands: `inspect`, `process`, `download`, `process-manifest`, `transcribe`, `bootstrap-models`, `doctor`.
- `inspect`, `process` and `download` require one cookie source: `--cookies-from-browser {safari,chrome,chromium,firefox,edge,brave}` or `--cookies FILE`. Only unexpired cookies the course URL's host would receive (its own and parent domains) are kept (`swinydl/auth.py`). `process-manifest` gets its cookies from the job manifest the Safari extension writes. There is no Selenium or Chrome automation path.
- `./install.sh` is first-run setup and repair for a copied DMG folder. It needs a prebuilt `SWinyDLSafariApp.app` unless you pass `--build-from-source`. See `./install.sh --help`.
- `./scripts/build_app.sh` builds the Safari app and extension from source (needs `xcodegen` and Xcode command line tools).
- `./scripts/package_release.sh [vX.Y.Z]` builds the runtime-only DMG into `dist/`.
- Releases: push a `v*` tag. That runs `.github/workflows/release-dmg.yaml`, which runs `scripts/package_release.sh` and attaches the DMG to the GitHub release. The tag sets the DMG name and the app version. `swinydl/version.py` and `safari/SWinyDLSafariExtension/Resources/WebExtension/manifest.json` also hold the version; keep them in step with the tag.
- `docs/release-install.md` and `docs/user-guide.md` ship inside the DMG as `README.md` and `USER-GUIDE.md`, so links in them must be absolute URLs.
- `./run.sh` runs the CLI from a pip-installed virtualenv in `_swinydlvenv/`. It is an alternative to `uv run`, not a separate workflow.
- Tests: `uv run pytest`.
- Safari app and extension sources live under `safari/`; the CoreML runner Swift package lives under `swift/ParakeetCoreMLRunner/`.
- Primary docs: `README.md` and `docs/`.

## Reference

- Master rules: `/Users/david/Documents/memory-system/shared-agent-library/codex-rules.md`
