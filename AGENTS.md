# AI Agent Playbook

## Mission
- Deliver fast, safe iterations on the Google Drive Face Organizer
- Keep FastAPI backend, React frontend, and automation helpers aligned
- Surface risks early and document every non-trivial decision

## Core Surfaces
- `backend/main.py`: FastAPI entry point, middleware, and router wiring
- `backend/helper/process_photos_enhanced.py`: primary job pipeline
- `backend/core/`: configuration (`config.py`) and logging (`logger.py`, `logging_config.yaml`)
- `backend/routers/organizer_router.py`: `/api/organize` and `/api/status/{job_id}` endpoints
- `frontend/src/`: React status UI consuming backend APIs
- `plan/backend-improvement-roadmap.md`: long-form roadmap; skim for context before major changes

## Agent Roles
### Planner
- Triage incoming asks, restate scope, flag dependencies
- Review roadmap and existing docs before proposing architecture changes
- Produce lightweight implementation outline with entry points and testing notes
### Developer
- Follow `.cursorrules` (functional style, type hints, FastAPI best practices)
- Read relevant modules end-to-end before modifying; avoid duplicating helper logic
- Keep logging structured (`get_logger`) and respect `Settings` defaults
- Update docs when behavior or configuration changes
### Reviewer / QA
- Validate diff against plan and coding standards
- Run targeted checks (`pytest`, linting) when feasible; call out gaps when not
- Verify logging, error handling, and configuration wiring remain consistent

## Default Workflow
1. **Clarify**: Confirm acceptance criteria, success metrics, and data sources
2. **Investigate**: Inspect existing modules, configs, and logs relevant to the change
3. **Design**: Draft a brief plan (inputs, outputs, failure paths, tests)
4. **Implement**: Code in small, reviewable commits; prefer pure functions and FastAPI DI
5. **Test**: Run `pytest` from `backend/` or focused scripts; note skipped checks
6. **Document**: Update README, roadmap, or inline docstrings when behavior shifts
7. **Hand-off**: Summarize impact, risks, and follow-up work in the final message

## Environment & Tooling
- **Backend setup**
  - `cd backend`
  - `python3 -m venv venv && source venv/bin/activate`
  - `pip install -r requirements.txt`
  - Dev server: `uvicorn main:app --reload`
- **Frontend setup**
  - `cd frontend`
  - `npm install`
  - Dev server: `npm start`
- **Database**: defaults to SQLite (`face_organizer.db`); expects migrations handled manually today
- **Secrets**: store Google OAuth credentials locally (`credentials.json`, `token.pickle`); never commit

## Testing Notes
- Prefer `pytest` (there is `backend/test_multi_face.py` as a reference entry point)
- For exploratory runs, call helper functions with controlled inputs; log interim metrics via `logger`
- Capture sample outputs under `backend/organized_photos/` for manual verification

## Observability & Logging
- Logging initializes in `backend/main.py` via `setup_logging()`
- Structured logging configs live in `backend/core/logging_config.yaml`
- Use job metadata (`jobs` dict in `organizer_router.py`) for progress tracking; keep keys stable

## Coordination Tips
- Surface blocking issues (e.g., Google API quota, missing credentials) immediately
- When touching both backend and frontend, lock API contracts first
- Record open questions and assumptions in PR summaries or task notes
- Prefer incremental upgrades; log TODOs in roadmap for larger rewrites

## When In Doubt
- Re-read `.cursorrules` for coding expectations
- Review `UPGRADE_GUIDE.md` and `README.md` for setup nuances
- Ask for clarification instead of guessing about Google Drive behaviors or photo datasets

