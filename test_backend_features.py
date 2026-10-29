import csv
import json
import tempfile
import unittest
from pathlib import Path

from table_tennis_app import (
    Player,
    rrt,
    StorageManager,
    StatisticsService,
    TournamentDrawService,
    export_tournament_package,
)


def make_players():
    return [
        Player("Aryan", "shakehand", "right", "attacker"),
        Player("Maya", "penhold", "left", "defender"),
        Player("Sam", "shakehand", "right", "all-rounder"),
    ]


def make_config():
    return {
        "points_per_game": 11,
        "deuce_enabled": True,
        "golden_point_enabled": False,
        "games_needed_to_win": 1,
    }


def make_draw(players):
    return {
        "schema_version": 1,
        "tournament": {
            "name": "Imported Open",
            "format": "round_robin",
            "game_config": make_config(),
            "tie_break_settings": ["match_wins", "game_difference"],
        },
        "entrants": [
            {"participant_id": "seed-a", "player_id": players[0].player_id, "seed": 1},
            {"participant_id": "seed-b", "player_id": players[1].player_id, "seed": 2},
        ],
        "matches": [
            {
                "match_id": "external-1",
                "round": 1,
                "slot": 1,
                "player_one": "seed-a",
                "player_two": "seed-b",
            }
        ],
    }


class BackendFeatureTests(unittest.TestCase):
    def test_versioned_state_round_trip_includes_tournament_and_events(self):
        players = make_players()
        tournament = rrt("League", players[:2], make_config())
        tournament.generate_matches()
        match = tournament.matches[0]
        match.status = "in_progress"
        match.current_game = match.create_game(match.player_one)
        match.current_game.add_point(match.player_one, match.player_one.player_id)

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StorageManager(state_filename=Path(temp_dir) / "state.json")
            manager.save_state({p.player_id: p for p in players}, [tournament])
            loaded_players, loaded_tournaments, loaded_matches = manager.load_state()

        loaded = loaded_tournaments[0]
        loaded_match = loaded.matches[0]
        self.assertEqual(loaded_players[players[0].player_id].name, "Aryan")
        self.assertEqual(loaded_match.status, "in_progress")
        self.assertEqual(len(loaded_match.current_game.events), 1)
        self.assertEqual(loaded_match.current_game.current_game_score[players[0].player_id], 1)
        self.assertEqual(loaded_match.current_game.match_id, loaded_match.match_id)
        self.assertEqual(loaded_match.current_game.events[0]["game_id"], loaded_match.current_game.game_id)
        self.assertEqual(loaded_match.current_game.events[0]["match_id"], loaded_match.match_id)
        self.assertEqual(loaded_matches, [])

    def test_draw_preview_is_non_mutating_and_requires_confirmation(self):
        players = make_players()
        preview = TournamentDrawService.preview_json(make_draw(players), players)
        self.assertTrue(preview["valid"])
        self.assertEqual(len(preview["matches"]), 1)
        with self.assertRaises(ValueError):
            TournamentDrawService.apply_preview(preview, players, confirmed=False)
        tournament = TournamentDrawService.apply_preview(
            preview, players, confirmed=True
        )
        self.assertEqual(tournament.matches[0].match_id, "external-1")
        self.assertEqual(tournament.seeds[players[0].player_id], 1)

    def test_import_reports_unknown_and_ambiguous_participants(self):
        players = make_players()
        draw = make_draw(players)
        draw["entrants"][0]["player_id"] = "missing-player"
        preview = TournamentDrawService.preview_json(draw, players)
        self.assertFalse(preview["valid"])
        self.assertTrue(preview["errors"])

    def test_knockout_preview_rejects_duplicate_round_participation(self):
        players = make_players()
        draw = make_draw(players)
        draw["tournament"]["format"] = "knockout"
        draw["matches"].append({
            "match_id": "external-2", "round": 1, "slot": 2,
            "player_one": "seed-a", "player_two": "seed-b",
        })
        preview = TournamentDrawService.preview_json(draw, players)
        self.assertFalse(preview["valid"])
        self.assertTrue(any("more than once" in error for error in preview["errors"]))

    def test_invalid_tie_break_entries_return_validation_error(self):
        players = make_players()
        with self.assertRaises(ValueError):
            rrt("Invalid rules", players[:2], make_config(), tie_break_settings=[["bad"]])

    def test_manual_tournament_changes_are_audited(self):
        players = make_players()
        tournament = rrt("League", players[:2], make_config())
        tournament.generate_matches()
        match = tournament.matches[0]
        tournament.set_match_order(match.match_id, 2, 3, reason="Court schedule changed")
        tournament.set_match_status(match.match_id, "postponed", reason="Table unavailable")
        tournament.set_seed(players[0].player_id, 7, reason="Organizer reseeded")
        self.assertEqual((match.round_number, match.slot_number), (2, 3))
        self.assertEqual(match.status, "postponed")
        self.assertEqual(tournament.seeds[players[0].player_id], 7)
        self.assertEqual(len(tournament.audit_log), 3)
        self.assertTrue(all(entry["reason"] for entry in tournament.audit_log))

    def test_result_correction_reconciles_cached_wins_and_elo(self):
        players = make_players()
        tournament = rrt("League", players[:2], make_config())
        tournament.generate_matches()
        match = tournament.matches[0]
        initial_ratings = {
            match.player_one.player_id: match.player_one.elo_rating,
            match.player_two.player_id: match.player_two.elo_rating,
        }
        match.match_winner = match.player_one
        match.match_finished = True
        match.status = "completed"
        match.rating_before = dict(initial_ratings)
        match.rating_updated = True
        match.player_one.matches_won += 1
        match.player_two.matches_lost += 1
        match.records_updated = True
        from table_tennis_app import EloSystem
        EloSystem.update_score(match.player_one, match.player_two, match.player_one)

        tournament.correct_match_result(match.match_id, match.player_two.player_id,
                                        reason="Score sheet was reversed")

        self.assertEqual(match.player_one.matches_won, 0)
        self.assertEqual(match.player_two.matches_won, 1)
        self.assertEqual(match.player_one.matches_lost, 1)
        self.assertEqual(match.player_two.matches_lost, 0)
        self.assertEqual(match.player_one.elo_rating, 988)
        self.assertEqual(match.player_two.elo_rating, 1012)

    def test_blank_audit_reason_does_not_mutate_tournament(self):
        players = make_players()
        tournament = rrt("League", players[:2], make_config())
        with self.assertRaises(ValueError):
            tournament.add_entrant(players[2], "  ")
        self.assertEqual(len(tournament.players), 2)

    def test_statistics_derive_points_and_serve_return_from_events(self):
        players = make_players()
        tournament = rrt("League", players[:2], make_config())
        tournament.generate_matches()
        match = tournament.matches[0]
        game = match.create_game(match.player_one)
        game.add_point(match.player_one, match.player_one.player_id)
        game.add_point(match.player_two, match.player_one.player_id)
        game.undo_last_point("wrong point entry")
        match.games.append(game)

        stats = StatisticsService.player_statistics(players[0].player_id, [match])
        self.assertEqual(stats["points_won"], 1)
        self.assertEqual(stats["points_on_serve_won"], 1)
        self.assertEqual(stats["points_return_won"], 0)
        self.assertEqual(stats["point_sample_size"], 1)

    def test_export_package_contains_json_csv_event_data_and_manifest(self):
        players = make_players()
        tournament = rrt("League", players[:2], make_config())
        tournament.generate_matches()
        match = tournament.matches[0]
        game = match.create_game(match.player_one)
        game.add_point(match.player_one, match.player_one.player_id)
        match.games.append(game)

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = export_tournament_package(tournament, temp_dir)
            self.assertTrue(all(Path(path).exists() for path in paths.values()))
            data = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 1)
            self.assertEqual(len(data["matches"][0]["games"][0]["events"]), 1)
            with Path(paths["matches_csv"]).open(encoding="utf-8", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 1)
            self.assertIn("schema_version", Path(paths["manifest"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

