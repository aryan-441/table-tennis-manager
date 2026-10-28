# Table Tennis Manager

An ongoing Python application for maintaining player profiles and recording table-tennis games, matches, and tournaments. The current code also includes an Elo rating system and JSON-based player storage.

## Current implementation

- Player profile fields include grip, playing hand, and play style.
- Match/game code handles point events, undo, faults, scoring, and match results.
- Tournament classes and Elo-related logic are present in the source.
- Player data is serialized as JSON.

## Requirements and setup

Python 3; the reviewed source imports only Python standard-library modules. From the project directory, run `python table_tennis_app.py`.

## Status and limitations

This is a work in progress. Match-state correctness, tournament edge cases, input validation, persistence errors, and Elo/stat updates need focused review. Storage uses a relative `players.json` path, so run from the project directory. Planned features must be distinguished from implemented ones in future updates.

## Project date

No authored project date is stated in the script. Drive lists the source file as created 2025-12-27 and modified 2026-10-11; these are file metadata dates, not confirmed start/release dates.

No license has been selected.
