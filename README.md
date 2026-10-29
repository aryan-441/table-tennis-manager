# Table Tennis Manager

**Project date: 27 December 2025. Updated: 29 October 2026.**

An ongoing Python application for maintaining player profiles and recording table-tennis games, matches, and tournaments.

## Credits

- **Backend:** Developed by Aryan Arora; Codex assisted with backend bug fixes.
- **Frontend:** Planned with Codex assistance.

## Current implementation

- Player profiles have stable IDs and validated profile fields.
- The scoring backend supports 11-point and 21-point games, win-by-two and golden-point configurations, point events, undo, faults, lets, and service tracking.
- Matches support one-game and best-of formats, record match results, and update Elo and basic player statistics.
- Round-robin fixtures and standings, plus knockout progression and byes, are implemented.
- Player records can be saved to and loaded from JSON, with atomic saves and validation for malformed data.

## Remaining work

The backend is not complete yet. The project brief still calls for:

- Connecting player storage to the CLI and persisting/resuming matches and tournaments.
- Tournament draw import, preview, and organiser editing/overrides.
- Tournament audit history and full JSON plus CSV exports.
- Configurable standings tie-breaks and broader statistics derived from match events.
- Event timestamps and a separate, audited workflow for correcting faults and completed results.
- A Tkinter frontend that uses the backend scoring and tournament logic.

## Run

Requires Python 3 and uses only standard-library modules. From the project directory, run:

`python table_tennis_app.py`

The current entry point runs a sample match.