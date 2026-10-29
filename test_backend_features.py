import csv
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from table_tennis_app import (
    Game,
    Match,
    Player,
    kot,
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
    def test_sample_json_template_is_valid_knockout_progression(self):
        players = make_players() + [Player("Ira", "shakehand", "right", "attacker")]
        template = TournamentDrawService.sample_json_template()
        for row, player in zip(template["entrants"], players):
            row["player_id"] = player.player_id

        preview = TournamentDrawService.preview_json(template, players)

        self.assertTrue(preview["valid"], preview["errors"])
        self.assertEqual(len(preview["matches"]), 3)
        self.assertEqual(preview["matches"][-1]["winner_of"], ["semi-1", "semi-2"])

    def test_knockout_replacement_updates_unplayed_bracket_and_blocks_stale_progression(self):
        players = make_players() + [Player("Ira", "shakehand", "right", "attacker")]
        tournament = kot("Cup", players[:3], make_config())
        first_round = Match(players[0], players[1], make_config())
        first_round.round_number = 1
        first_round.slot_number = 1
        tournament.matches = [first_round]
        tournament.draw_metadata = {
            "rounds": [{"round": 1, "entrant_ids": [p.player_id for p in players[:3]],
                        "bye_player_id": players[2].player_id,
                        "bye_player_ids": [players[2].player_id], "completed": False}],
            "byes": [{"round": 1, "match_id": "bye-1", "player_id": players[2].player_id}],
            "match_plans": [{"match_id": "final", "player_one_id": players[0].player_id}],
        }

        tournament.replace_entrant(players[0].player_id, players[3], "Corrected roster")

        self.assertEqual(first_round.player_one, players[3])
        self.assertIn(players[3].player_id, tournament.draw_metadata["rounds"][0]["entrant_ids"])
        self.assertEqual(tournament.draw_metadata["match_plans"][0]["player_one_id"], players[3].player_id)

        first_round.status = "completed"
        first_round.match_finished = True
        with self.assertRaisesRegex(ValueError, "after bracket results"):
            tournament.replace_entrant(players[3].player_id, players[0], "Too late")

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

    def test_state_backup_restore_validates_then_restores_saved_data(self):
        players = make_players()
        player_map = {p.player_id: p for p in players}
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StorageManager(state_filename=Path(temp_dir) / "state.json")
            manager.save_state(player_map, [])
            backup_path = manager.list_state_backups()
            self.assertEqual(backup_path, [])
            from table_tennis_app import backup_file
            backup = backup_file(manager.state_filename)
            players[0].name = "Changed after backup"
            manager.save_state(player_map, [])
            restored_path = manager.restore_state_backup(backup)
            restored_players, _, _ = manager.load_state()
        self.assertEqual(restored_path, str(Path(temp_dir) / "state.json"))
        self.assertEqual(restored_players[players[0].player_id].name, "Aryan")

    def test_invalid_backup_does_not_replace_current_state(self):
        players = make_players()
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StorageManager(state_filename=Path(temp_dir) / "state.json")
            manager.save_state({p.player_id: p for p in players}, [])
            from table_tennis_app import backup_file
            backup = backup_file(manager.state_filename)
            Path(backup).write_text("not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                manager.restore_state_backup(backup)
            restored_players, _, _ = manager.load_state()
        self.assertEqual(restored_players[players[0].player_id].name, "Aryan")

    def test_malformed_state_is_backed_up_before_load_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            state_path.write_text("{broken", encoding="utf-8")
            manager = StorageManager(state_filename=state_path)
            with self.assertRaisesRegex(ValueError, "backed up"):
                manager.load_state()
            self.assertEqual(len(manager.list_state_backups()), 1)

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

    def test_import_mapping_resolves_ambiguous_names_by_participant_id(self):
        players = make_players()
        duplicate = Player("Aryan", "penhold", "left", "defender")
        all_players = players + [duplicate]
        draw = make_draw(players)
        draw["entrants"][0] = {
            "participant_id": "seed-a", "name": "Aryan", "seed": 1,
        }
        unresolved = TournamentDrawService.preview_json(draw, all_players)
        self.assertFalse(unresolved["valid"])
        mapped = TournamentDrawService.preview_json(
            draw, all_players, player_mapping={"seed-a": players[0].player_id}
        )
        self.assertTrue(mapped["valid"])

    def test_csv_preview_rejects_blank_participants_and_accepts_valid_rows(self):
        players = make_players()
        header = "player_one_id,player_two_id,round,slot\n"
        invalid = TournamentDrawService.preview_csv(
            header + f"{players[0].player_id},,1,1\n",
            players, "CSV", "round_robin", make_config(),
        )
        self.assertFalse(invalid["valid"])
        valid = TournamentDrawService.preview_csv(
            header + f"{players[0].player_id},{players[1].player_id},1,1\n",
            players, "CSV", "round_robin", make_config(),
        )
        self.assertTrue(valid["valid"])
        external_ids = "player_one_id,player_two_id,round,slot\next-a,ex-b,1,1\n"
        mapped = TournamentDrawService.preview_csv(
            external_ids, players, "Mapped CSV", "round_robin", make_config(),
            player_mapping={"ext-a": players[0].player_id, "ex-b": players[1].player_id},
        )
        self.assertTrue(mapped["valid"], mapped["errors"])
        duplicate_headers = TournamentDrawService.preview_csv(
            "player_one_id,player_one_id,round,slot\na,b,1,1\n",
            players, "CSV", "round_robin", make_config(),
        )
        self.assertFalse(duplicate_headers["valid"])

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

    def test_imported_knockout_bracket_uses_actual_prior_round_winners(self):
        players = make_players() + [Player("Lee", "shakehand", "right", "attacker")]
        draw = {
            "schema_version": 1,
            "tournament": {
                "name": "Seeded Cup", "format": "knockout",
                "game_config": make_config(),
            },
            "entrants": [
                {"participant_id": f"seed-{i + 1}", "player_id": player.player_id, "seed": i + 1}
                for i, player in enumerate(players)
            ],
            "matches": [
                {"match_id": "semi-a", "round": 1, "slot": 1,
                 "player_one": "seed-1", "player_two": "seed-4"},
                {"match_id": "semi-b", "round": 1, "slot": 2,
                 "player_one": "seed-2", "player_two": "seed-3"},
                {"match_id": "final", "round": 2, "slot": 1,
                 "winner_of": ["semi-a", "semi-b"]},
            ],
        }
        preview = TournamentDrawService.preview_json(draw, players)
        self.assertTrue(preview["valid"], preview["errors"])
        tournament = TournamentDrawService.apply_preview(preview, players, confirmed=True)
        self.assertEqual(len(tournament.matches), 2)

        def award_first_player(match):
            match.match_winner = match.player_one
            match.match_finished = True
            match.status = "completed"

        with patch("table_tennis_app.run_match", side_effect=award_first_player):
            tournament.run_round()
            semifinal_winners = [match.match_winner.player_id for match in tournament.matches]
            tournament.run_round()

        final = next(match for match in tournament.matches if match.match_id == "final")
        self.assertEqual(
            {final.player_one.player_id, final.player_two.player_id},
            set(semifinal_winners),
        )

    def test_imported_knockout_plan_survives_save_and_resume(self):
        players = make_players() + [Player("Lee", "shakehand", "right", "attacker")]
        draw = {
            "schema_version": 1,
            "tournament": {
                "name": "Resumable Cup", "format": "knockout",
                "game_config": make_config(),
            },
            "entrants": [
                {"participant_id": f"seed-{i + 1}", "player_id": player.player_id}
                for i, player in enumerate(players)
            ],
            "matches": [
                {"match_id": "semi-a", "round": 1, "slot": 1,
                 "player_one": "seed-1", "player_two": "seed-4"},
                {"match_id": "semi-b", "round": 1, "slot": 2,
                 "player_one": "seed-2", "player_two": "seed-3"},
                {"match_id": "final", "round": 2, "slot": 1,
                 "winner_of": ["semi-a", "semi-b"]},
            ],
        }
        preview = TournamentDrawService.preview_json(draw, players)
        tournament = TournamentDrawService.apply_preview(preview, players, confirmed=True)

        def award_first_player(match):
            match.match_winner = match.player_one
            match.match_finished = True
            match.status = "completed"

        with patch("table_tennis_app.run_match", side_effect=award_first_player):
            tournament.run_round()
        expected_finalists = [match.match_winner.player_id for match in tournament.matches]
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StorageManager(state_filename=Path(temp_dir) / "state.json")
            manager.save_state({p.player_id: p for p in players}, [tournament])
            _, loaded_tournaments, _ = manager.load_state()
            resumed = loaded_tournaments[0]
            with patch("table_tennis_app.run_match", side_effect=award_first_player):
                resumed.run_round()
        final = next(match for match in resumed.matches if match.match_id == "final")
        self.assertEqual(
            {final.player_one.player_id, final.player_two.player_id},
            set(expected_finalists),
        )

    def test_knockout_import_cannot_drop_a_prior_round_winner(self):
        players = make_players() + [Player("Lee", "shakehand", "right", "attacker")]
        draw = {
            "schema_version": 1,
            "tournament": {"name": "Incomplete Cup", "format": "knockout",
                           "game_config": make_config()},
            "entrants": [
                {"participant_id": f"seed-{i + 1}", "player_id": player.player_id}
                for i, player in enumerate(players)
            ],
            "matches": [
                {"match_id": "semi-a", "round": 1, "slot": 1,
                 "player_one": "seed-1", "player_two": "seed-4"},
                {"match_id": "semi-b", "round": 1, "slot": 2,
                 "player_one": "seed-2", "player_two": "seed-3"},
                {"match_id": "final", "round": 2, "slot": 1,
                 "winner_of": ["semi-a", "semi-a"]},
            ],
        }
        preview = TournamentDrawService.preview_json(draw, players)
        self.assertFalse(preview["valid"])
        self.assertTrue(preview["errors"])

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
        self.assertTrue(all(entry["actor"] for entry in tournament.audit_log))

    def test_setting_walkover_reconciles_player_result_counters(self):
        players = make_players()
        tournament = rrt("League", players[:2], make_config())
        tournament.generate_matches()
        match = tournament.matches[0]
        tournament.mark_walkover(match.match_id, players[1].player_id, "Player withdrew")
        self.assertEqual(players[1].matches_won, 1)
        self.assertEqual(players[0].matches_lost, 1)
        self.assertFalse(match.rating_updated)
        tournament.set_match_status(match.match_id, "reopened", "Correction required")
        self.assertEqual(players[1].matches_won, 0)
        self.assertEqual(players[0].matches_lost, 0)

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

    def test_service_rotation_uses_point_count_at_both_deuce_boundaries(self):
        players = make_players()
        for target, points_each, first_rotation in ((11, 10, 2), (21, 20, 5)):
            config = dict(make_config(), points_per_game=target)
            game = Game(players[0], players[1], config, True, players[0])
            servers = []
            for _ in range(points_each):
                servers.append(game.server_id_for_next_point())
                game.add_point(players[0])
            for _ in range(points_each):
                servers.append(game.server_id_for_next_point())
                game.add_point(players[1])
            self.assertEqual(servers[0], players[0].player_id)
            self.assertEqual(servers[first_rotation], players[1].player_id)
            self.assertEqual(game.current_game_score, {
                players[0].player_id: target - 1,
                players[1].player_id: target - 1,
            })
            self.assertEqual(game.server_id_for_next_point(), players[0].player_id)
            game.add_point(players[0])
            self.assertEqual(game.events[-1]["server_id"], players[0].player_id)
            self.assertEqual(game.server_id_for_next_point(), players[1].player_id)

    def test_fault_correction_is_logged_and_replayed_into_score_and_stats(self):
        players = make_players()
        match = Match(players[0], players[1], make_config())
        game = match.create_game(players[0])
        game.add_fault(players[1])
        fault = next(event for event in game.events if event["type"] == "FAULT")
        self.assertEqual(game.current_game_score[players[0].player_id], 1)
        game.correct_fault(fault["event_id"], "Fault was called in error", None)
        self.assertEqual(game.current_game_score[players[0].player_id], 0)
        game.correct_fault(fault["event_id"], "Award point to receiver", players[1].player_id)
        self.assertEqual(game.current_game_score[players[1].player_id], 1)
        self.assertEqual(len([e for e in game.events if e["type"] == "FAULT_CORRECTION"]), 2)
        stats = StatisticsService.player_statistics(players[1].player_id, [match])
        self.assertEqual(stats["points_won"], 1)
        self.assertEqual(stats["points_return_won"], 1)

    def test_next_game_server_alternates_from_previous_game(self):
        players = make_players()
        match = Match(players[0], players[1], make_config())
        match.server = players[0]
        first_game = match.create_game(players[0])
        match.games.append(first_game)
        self.assertIs(match.next_game_server(), players[1])

    def test_knockout_cancelled_match_requires_and_allows_manual_advance(self):
        players = make_players()
        tournament = kot("Cup", players[:2], make_config())
        match = Match(players[0], players[1], make_config())
        match.round_number = 1
        match.slot_number = 1
        match.status = "cancelled"
        tournament.matches.append(match)
        tournament.draw_metadata["rounds"] = [{
            "round": 1, "entrant_ids": [p.player_id for p in players[:2]],
            "bye_player_id": None, "match_ids": [match.match_id], "completed": False,
        }]
        with patch("table_tennis_app.run_match") as run_match:
            with self.assertRaisesRegex(RuntimeError, "manually advance"):
                tournament.run_round()
            run_match.assert_not_called()
        tournament.pause_progression("Organizer review")
        with self.assertRaises(RuntimeError):
            tournament.run_round()
        winners = tournament.advance_round_manually(
            {match.match_id: players[0].player_id}, "Opponent withdrew"
        )
        self.assertEqual([p.player_id for p in winners], [players[0].player_id])
        self.assertEqual(tournament.round_number, 2)
        self.assertEqual(match.status, "walkover")
        self.assertTrue(tournament.draw_metadata["rounds"][0]["completed"])

    def test_postponed_round_robin_fixture_cannot_be_silently_skipped(self):
        players = make_players()
        tournament = rrt("League", players[:2], make_config())
        tournament.generate_matches()
        match = tournament.matches[0]
        match.status = "postponed"
        with patch("table_tennis_app.run_match") as run_match:
            with self.assertRaisesRegex(RuntimeError, "postponed"):
                tournament.run_tournament()
            run_match.assert_not_called()

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

    def test_export_preserves_in_progress_game_and_does_not_mutate_tournament(self):
        players = make_players()
        tournament = rrt("League", players[:2], make_config())
        tournament.generate_matches()
        match = tournament.matches[0]
        game = match.create_game(match.player_one)
        game.add_point(match.player_one)
        before = json.dumps(tournament.to_dict(), sort_keys=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = export_tournament_package(tournament, temp_dir)
            payload = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
            with Path(paths["matches_csv"]).open(encoding="utf-8", newline="") as stream:
                row = next(csv.DictReader(stream))
            with Path(paths["events_csv"]).open(encoding="utf-8", newline="") as stream:
                event_rows = list(csv.DictReader(stream))
        self.assertEqual(payload["matches"][0]["current_game"]["score"][players[0].player_id], 1)
        self.assertEqual(row["current_score_player_one"], "1")
        self.assertEqual(len(event_rows), 1)
        self.assertEqual(json.dumps(tournament.to_dict(), sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
