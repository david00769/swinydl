# AGENTS.md

Use this file in this repository to connect it to Buildshop's Codex-native skill library.

## Core Rules
- Always check `/Users/davidsiroky/Documents/memory-system/shared-agent-library/skills/` before creating new process instructions.
- Reference skills by exact markdown filename.
- Structured skills use their folder path plus `SKILL.md`.
- Prefer Buildshop skills first; add local project rules only when no shared skill fits.
- Use shared Buildshop skills in place by default; do not vendor or copy generic Buildshop skills into this repo unless customization is required.
- If a local customization is necessary, keep it thin and explicit: wrap, symlink, or fork only the specific skill that needs project-specific behavior.
- Use absolute paths when instructions depend on local workspace layout.
- Default to solo-dev velocity: prioritize rapid prototyping and avoid enterprise-heavy CI/CD unless explicitly requested.
- For Apple-platform repos, never leave the iOS deployment target as an inherited scaffold default. Make one repo-owned source of truth, prefer the latest installed major iOS release when the project wants `latest iOS`, and add a fast-fail sync/check script so project settings and docs cannot drift.
- For repos that use local Hugging Face models or processors inside the memory-system workspace, default to one shared workspace cache root:
  - `XDG_CACHE_HOME=/Users/davidsiroky/Documents/memory-system/.cache`
  - `HF_HOME=/Users/davidsiroky/Documents/memory-system/.cache/huggingface`
  - `HF_HUB_CACHE=/Users/davidsiroky/Documents/memory-system/.cache/huggingface/hub`
  - `HUGGINGFACE_HUB_CACHE=/Users/davidsiroky/Documents/memory-system/.cache/huggingface/hub`
  - `TRANSFORMERS_CACHE=/Users/davidsiroky/Documents/memory-system/.cache/huggingface/transformers`
  - `MODEL_CACHE_DIR=/Users/davidsiroky/Documents/memory-system/.cache/datalab/models`
  Do not create repo-local duplicate model caches unless isolated benchmarking or sandboxing is intentional.

## Session Bootstrap (Optional, Run Once Per Repo)
1. `Use skill: connect-to-buildshop`
2. `Use skill: codebase-skill-recommender`
3. `Use skill: high-level-intent-router`
4. Log completion:
   - `/Users/davidsiroky/Documents/memory-system/shared-agent-library/optional-tools/workflow-log.sh mark onboarding-buildshop done "bootstrap skills run"`
5. Skip bootstrap if already done:
   - `/Users/davidsiroky/Documents/memory-system/shared-agent-library/optional-tools/workflow-log.sh is-done onboarding-buildshop`

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

## High-Level Prompting
- You can give high-level intent; the agent should map to the right Buildshop skills and fill in details.
- Example prompts:
  - `Abstract this task and execute with Buildshop skills`
  - `Use the high-level-intent-router skill`
  - `Recommend the top Buildshop skills for this repo and start with the highest impact`

## Suggested Skills By Need
1. `documentation-and-hints.md` to keep installer/docs + agent hints aligned with the current packaging path.
2. `testing-and-ci.md` and `testing-strategy.md` for CLI + macOS/Safari regression coverage.
3. `sosumi-apple-docs/SKILL.md`, `swiftui/SKILL.md`, and `simulator-utils/SKILL.md` for Apple-platform app or extension work.
4. `yttranscribe/SKILL.md` when transcript pipeline work overlaps with local media ingestion.
5. `compound-learnings.md` after significant work to update Buildshop permanently.

## Project Hints
- Canonical root: `/Users/davidsiroky/Documents/memory-system/personal-projects/echo360`
- Main Python package is `swinydl`; CLI entrypoint is `swinydl`.
- Use `./install.sh` for first-run setup from a copied DMG folder.
- Use `./scripts/build_app.sh` for local Safari app/extension builds.
- Use `./scripts/package_release.sh` for release DMG packaging.
- Use `./run.sh` or `uv run app.py` only when you intentionally need the older fallback flow.
- Safari extension and Apple-platform shell live under `safari/` and `swift/`; keep the transcript-first macOS workflow aligned with the CLI/runtime path.
- Primary docs live in `README.md` and `docs/`.

## Reference
- Master rules: `/Users/davidsiroky/Documents/memory-system/shared-agent-library/codex-rules.md`
