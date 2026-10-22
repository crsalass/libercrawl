# Libercrawl public edition — coding agent instructions

- Repo skill: `.agents/skills/libercrawl-ui-review/SKILL.md`.
- Preserve minimal dark, system-font UI with no CDN/fonts/tracking.
- Public edition intentionally contains **no personal-only UI or API export**. Do not add it, even behind flags.
- Never upload or modify runtime `engine/`, `data/`, `.venv`, `.env`, Docker volumes or secret keys.
- Test with `python -m pytest -q` and `node --check app/static/app.js`.
- Do not run Git commands that commit, push or set remotes without user approval.
