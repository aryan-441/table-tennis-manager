# Rallydesk frontend acceptance results

Updated 29 October 2026. These checks used fresh, isolated browser profiles against the local Vite preview; they did not modify the user's browser data.

## Passed

- Fresh workspace opens without a club, player, match, or tournament seeded. User-entered player profiles and tournament setup work.
- Single-match setup opens the scoring screen. Service changes after the expected two-point interval in an 11-point game. At 10–10, the game does not end; 11–10 is not enough, and 12–10 can be confirmed.
- Lets and faults are visible in the event timeline. Undoing a fault restores the point score and correct previous server while preserving a correction entry.
- A two-player round robin completes, updates the event standings and completion state, and updates the club statistics summary.
- A five-entrant knockout shows three byes, creates its opening match, and advances after that match is confirmed.
- 21-point single-game scoring: service changed after five points; 20–20 and 21–20 did not end the game; 22–20 was confirmed as the result.
- JSON draw import accepted a valid fixture after keyboard mapping a duplicated player name to the intended roster ID. A same-round duplicate participant was blocked before import.
- Paused knockout browser acceptance: resuming a completed Round 2 generated exactly one Round 3 fixture, recorded both audit events, and returned the tournament to Running. Resuming a paused completed final correctly kept one fixture, marked the tournament Completed, and generated no extra round.
- Editing an upcoming tournament field rebuilds its pending draw, requires a reason, and records the decision. The edit control is disabled after a match starts.
- An invalid CSV draw with a player scheduled twice in one round is blocked. A valid CSV is previewed before confirmation. Imported draws and schedule changes appear in the audit log.
- Duplicate display names remain separate roster entries; import marks the name as ambiguous and requires choosing the intended entrant.
- Pending match rescheduling updates time/table and records the organiser's reason. Tournament package and workspace JSON downloads start successfully.
- Valid backup restore previews record counts; cancel preserves the workspace; confirmation restores it. Malformed JSON is rejected without changing saved records.
- Settings backup round-trip: downloaded the current workspace, cleared it, selected that exact file in Restore, and recovered the same player record. Backup export and restore now share the same versioned wrapper.
- Reset cancel preserves records; confirmed reset clears them.
- Browser-storage write failure is caught and shown as a clear local-preview status; the app renders without a page exception.
- All eight main pages were checked at 360, 390, 768, 1024, and 1440 pixels. No page-level horizontal overflow remained; the Matches table scrolls inside its own panel.
- Scrollable tables announce themselves as labeled regions, show a mobile scroll hint, and accept keyboard scrolling.
- Dialog focus stays inside the dialog, the background becomes inert and page scrolling locks, Escape closes it, and focus and prior scroll state return to their original values. The mobile navigation drawer receives focus, traps Tab, closes with Escape, and restores focus to its menu button.
- Overview and Matches set distinct browser document titles; the global thin scrollbar token is present in the rendered app.
- A rendered contrast scan of all eight core pages found no remaining text pairs below the WCAG AA 4.5:1 normal-text / 3:1 large-text thresholds after the shared palette correction.
- Edge accessibility-tree inspection found no unnamed button, link, textbox, combobox, checkbox, or tab controls across the eight core pages (144 controls inspected). This is semantic-tree evidence, not a substitute for an actual screen-reader session.
- Desktop visual inspection at 1440px showed one clear Rallydesk page title and a separate “Your club desk” section heading with no page-level overflow.
- No browser page errors occurred in the feature-flow checks.
- `pnpm run build` passes (`tsc -b && vite build`); strict premium audit reports zero findings; required native-dialog/semantic-click searches are clean; `git diff --check` passes.

## Still to check

- Complete a keyboard-only end-to-end pass through every form and submit/cancel path. Keyboard mapping during JSON import, modal Tab/Escape/focus restoration, and mobile drawer keyboard behavior passed; every form has not yet received a full keyboard-only run.
- Validate screen-reader output with a real assistive technology session (for example NVDA). Edge accessibility-tree names were checked, but no screen reader was run.
- Review the build on the intended hosting/staging environment before release.
- Firebase, privacy/terms/cookie consent, account deletion, security rules, and deployment hardening belong to later project phases and are not part of this local-preview check.

## Method note

The configured Python Playwright module and Playwright Chromium binary were unavailable in this environment. Browser checks used the bundled Node Playwright package with the installed Microsoft Edge Chromium executable in headless mode. No automated test suite was added to the project in this pass.
