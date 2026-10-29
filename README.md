# Table Tennis Manager

**Project date: 27 December 2025. Updated: 29 October 2026.**

A Python application for managing player profiles, table-tennis matches, and tournaments.

## Credits

- **Backend:** Fully developed by Aryan Arora.
- **Frontend:** Assisted by Codex.

## Backend status

The backend is implemented and covered by the test suite. It includes:

- Validated player profiles with stable IDs.
- Configurable 11-point and 21-point games, win-by-two and golden-point rules, service rotation, and point-level event history.
- Fault and let recording, audited fault correction, and point undo with a required reason.
- Best-of match scoring, walkovers, retirements, result correction, Elo updates, and player statistics.
- Round-robin fixtures, configurable tie-breaks, knockout brackets and byes, imported bracket progression, and manual advancement for interrupted rounds.
- Audited tournament roster, seed, schedule, and status changes.
- Versioned JSON persistence, validation, atomic saves, recoverable backups, and restore.
- Tournament draw import preview for JSON and CSV, player mapping, and tournament exports in JSON and CSV.

Run the backend and CLI from the project directory:

`python table_tennis_app.py`

Run the backend test suite:

`python -m unittest -v`

## Frontend preview

The React, TypeScript, and Vite frontend lives in `frontend/`. It provides the Rallydesk workspace, player directory, single-match setup and scoring, round-robin and knockout tournaments, statistics, imports/exports, settings, and About/support pages. New workspaces are empty; organisers add their own names and club details.

Run the browser preview from the frontend directory:

```powershell
pnpm install
pnpm run dev
```

Create a production build with `pnpm run build`. The current frontend is a local browser preview stored in `localStorage`; Firebase Authentication, Firestore, legal/consent flows, and production hardening are not connected. See `frontend/UX-CONTRACT.md` for interaction rules and `frontend/QA_RESULTS.md` for the latest browser acceptance results and remaining checks.
