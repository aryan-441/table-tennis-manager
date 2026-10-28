# Table Tennis Manager

**Project date: 27 December 2025. Updated: 11 October 2026.**

An ongoing Python application for maintaining player profiles and recording table-tennis games, matches, and tournaments. The program also includes an Elo rating system and JSON-based player storage.

## Current implementation

- Player profiles store grip, playing hand, and play style.
- Match and game code handles point events, undo, faults, scoring, and match results.
- Tournament classes and Elo-related logic are included.
- Player data is stored in JSON.

## Run

Python 3; the program uses only standard-library modules. From the project directory, run `python table_tennis_app.py`.

## Status

This is a work in progress. Match-state correctness, tournament edge cases, input validation, persistence errors, and Elo/stat updates still need attention. Storage uses a relative `players.json` path, so run the program from its project directory.
