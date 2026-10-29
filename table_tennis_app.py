'''Table Tennis App'''
import uuid
import json
import random
import os
import tempfile
import csv
import copy
import shutil
import io
import getpass
from datetime import datetime, timezone
from pathlib import Path




ALLOWED_GRIPS = ["shakehand", "penhold"]
ALLOWED_PLAYING_HANDS = ["right", "left"]
ALLOWED_PLAY_STYLES = [
    "attacker",
    "defender",
    "all-rounder",
    "counter-attacker",
    "chopper"
]

EVENT_POINT = "POINT"
EVENT_UNDO = "UNDO_POINT"
EVENT_FAULT = "FAULT"
EVENT_LET = "LET"
EVENT_FAULT_CORRECTION = "FAULT_CORRECTION"
STATE_SCHEMA_VERSION = 1


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_json(filename, data):
    target = Path(filename)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            delete=False, newline=""
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(data, temp_file, indent=2, ensure_ascii=False)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, target)
    except Exception:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)
        raise


def backup_file(filename):
    source = Path(filename)
    if not source.exists():
        return None
    backup = source.with_name(f"{source.name}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}")
    shutil.copy2(source, backup)
    return str(backup)


class Player:
 

    def __init__(self, name, grip, playing_hand, play_style, player_id=None):
        # Assign permanent ID
        if player_id is not None:
            self.player_id = player_id
        else:
            self.player_id = str(uuid.uuid4())

        # Profile info
        self.name = name
        self.grip = grip
        self.playing_hand = playing_hand
        self.play_style = play_style

        # Stats
        self.elo_rating = 1000
        self.matches_won = 0
        self.matches_lost = 0
        self.points_scored = 0
        self.points_conceded = 0

    def to_dict(self):
      
        return {
            "player_id": self.player_id,
            "name": self.name,
            "grip": self.grip,
            "playing_hand": self.playing_hand,
            "play_style": self.play_style,
            "elo_rating": self.elo_rating,
            "matches_won": self.matches_won,
            "matches_lost": self.matches_lost,
            "points_scored": self.points_scored,
            "points_conceded": self.points_conceded
        }

    @staticmethod
    def from_dict(player_data):
        if not isinstance(player_data, dict):
            raise ValueError("Player data must be a dictionary.")

        required_fields = {
            "player_id",
            "name",
            "grip",
            "playing_hand",
            "play_style",
            "elo_rating",
            "matches_won",
            "matches_lost",
            "points_scored",
            "points_conceded",
        }

        missing_fields = required_fields - player_data.keys()
        if missing_fields:
            raise ValueError(
                f"Missing required fields: {', '.join(sorted(missing_fields))}"
            )

        if not isinstance(player_data["player_id"], str) or not player_data["player_id"].strip():
            raise ValueError("'player_id' must be a non-empty string.")

        if not isinstance(player_data["name"], str) or not player_data["name"].strip():
            raise ValueError("'name' must be a non-empty string.")

        if player_data["grip"] not in ALLOWED_GRIPS:
            raise ValueError(f"Invalid grip: {player_data['grip']!r}")

        if player_data["playing_hand"] not in ALLOWED_PLAYING_HANDS:
            raise ValueError(f"Invalid playing hand: {player_data['playing_hand']!r}")

        if player_data["play_style"] not in ALLOWED_PLAY_STYLES:
            raise ValueError(f"Invalid play style: {player_data['play_style']!r}")

        number_fields = (
            "elo_rating",
            "matches_won",
            "matches_lost",
            "points_scored",
            "points_conceded",
        )
        for field in number_fields:
            value = player_data[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"'{field}' must be a number.")

        count_fields = (
            "matches_won",
            "matches_lost",
            "points_scored",
            "points_conceded",
        )
        for field in count_fields:
            value = player_data[field]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"'{field}' must be a non-negative integer.")

        player = Player(
            name=player_data["name"],
            grip=player_data["grip"],
            playing_hand=player_data["playing_hand"],
            play_style=player_data["play_style"],
            player_id=player_data["player_id"]
        )

        player.elo_rating = player_data["elo_rating"]
        player.matches_won = player_data["matches_won"]
        player.matches_lost = player_data["matches_lost"]
        player.points_scored = player_data["points_scored"]
        player.points_conceded = player_data["points_conceded"]

        return player



class StorageManager:
    

    def __init__(self, filename="players.json", state_filename="app_state.json"):
        self.filename = filename
        self.state_filename = str(state_filename)

    def save_players(self, players):
        data = {player_id: player.to_dict() for player_id, player in players.items()}
        atomic_write_json(self.filename, data)



    def load_players(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as error:
            backup = backup_file(self.filename)
            raise ValueError(
                f"Player file {self.filename!r} contains invalid JSON "
                f"at line {error.lineno}, column {error.colno}. "
                f"Original file backed up to {backup!r}."
            ) from error

        if not isinstance(data, dict):
            raise ValueError("Player file must contain a JSON object.")

        players = {}

        for player_id, player_data in data.items():
            try:
                player = Player.from_dict(player_data)
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid player record {player_id!r}: {error}"
                ) from error

            if player.player_id != player_id:
                raise ValueError(
                    f"Player ID mismatch: file key {player_id!r}, "
                    f"record ID {player.player_id!r}."
                )
            players[player_id] = player

        return players

    def save_state(self, players, tournaments, matches=None):
        state = {
            "schema_version": STATE_SCHEMA_VERSION,
            "saved_at": utc_now_iso(),
            "players": {
                player_id: player.to_dict()
                for player_id, player in players.items()
            },
            "tournaments": [tournament.to_dict() for tournament in tournaments],
            "matches": [match.to_dict() for match in (matches or [])],
        }
        atomic_write_json(self.state_filename, state)

    def list_state_backups(self):
        state_path = Path(self.state_filename)
        if not state_path.parent.exists():
            return []
        return sorted(
            state_path.parent.glob(state_path.name + ".backup-*"),
            key=lambda path: path.name,
            reverse=True,
        )

    def restore_state_backup(self, backup_path):
        """Validate and atomically restore one backup created for this state file."""
        state_path = Path(self.state_filename).resolve()
        candidate = Path(backup_path).resolve()
        expected_prefix = state_path.name + ".backup-"
        if candidate.parent != state_path.parent or not candidate.name.startswith(expected_prefix):
            raise ValueError("Choose a timestamped backup belonging to this state file.")
        if not candidate.is_file():
            raise ValueError("The selected state backup does not exist.")
        validator = StorageManager(filename=self.filename, state_filename=str(candidate))
        validator.load_state()
        content = candidate.read_text(encoding="utf-8")
        atomic_write_text(state_path, content)
        return str(state_path)

    def load_state(self):
        try:
            with open(self.state_filename, "r", encoding="utf-8") as state_file:
                state = json.load(state_file)
        except FileNotFoundError:
            return self.load_players(), [], []
        except json.JSONDecodeError as error:
            backup = backup_file(self.state_filename)
            raise ValueError(
                f"State file {self.state_filename!r} contains invalid JSON "
                f"at line {error.lineno}, column {error.colno}. "
                f"Original file backed up to {backup!r}."
            ) from error

        if not isinstance(state, dict):
            backup = backup_file(self.state_filename)
            raise ValueError(
                f"State file must contain a JSON object. Original backed up to {backup!r}."
            )
        version = state.get("schema_version")
        if version != STATE_SCHEMA_VERSION:
            backup = backup_file(self.state_filename)
            raise ValueError(
                f"Unsupported state schema version {version!r}; expected "
                f"{STATE_SCHEMA_VERSION}. Original backed up to {backup!r}."
            )
        if not isinstance(state.get("players"), dict) or not isinstance(
            state.get("tournaments"), list
        ):
            backup = backup_file(self.state_filename)
            raise ValueError(
                f"State file has invalid players/tournaments fields. "
                f"Original backed up to {backup!r}."
            )
        if "matches" in state and not isinstance(state["matches"], list):
            backup = backup_file(self.state_filename)
            raise ValueError(
                f"State file matches field must be a list. Original backed up to {backup!r}."
            )

        players = {}
        for player_id, record in state["players"].items():
            try:
                player = Player.from_dict(record)
            except (KeyError, TypeError, ValueError) as error:
                backup = backup_file(self.state_filename)
                raise ValueError(
                    f"Invalid player {player_id!r} in state file: {error}. "
                    f"Original backed up to {backup!r}."
                ) from error
            if player.player_id != player_id:
                backup = backup_file(self.state_filename)
                raise ValueError(
                    f"Player ID mismatch for state record {player_id!r}. "
                    f"Original backed up to {backup!r}."
                )
            players[player_id] = player

        try:
            tournaments = [
                tournament_from_dict(item, players)
                for item in state["tournaments"]
            ]
            matches = [Match.from_dict(item, players) for item in state.get("matches", [])]
        except (KeyError, TypeError, ValueError) as error:
            backup = backup_file(self.state_filename)
            raise ValueError(
                f"State file contains an invalid match or tournament: {error}. "
                f"Original backed up to {backup!r}."
            ) from error
        return players, tournaments, matches

    def attach_autosave(self, players, tournaments, matches=None):
        matches = matches if matches is not None else []
        def save_bound_state():
            self.save_state(players, tournaments, matches)

        for tournament in tournaments:
            tournament._on_change = save_bound_state
            for match in tournament.matches:
                match._on_change = save_bound_state
        for match in matches:
            match._on_change = save_bound_state
        return save_bound_state


def add_player(players, name, grip, playing_hand, play_style):
    name = name.strip()
    if not name:
        print("Player name cannot be empty.")
        return
    if grip not in ALLOWED_GRIPS:
        print("Invalid grip.")
        return

    if playing_hand not in ALLOWED_PLAYING_HANDS:
        print("Invalid playing hand.")
        return

    if play_style not in ALLOWED_PLAY_STYLES:
        print("Invalid play style.")
        return

    new_player = Player(name, grip, playing_hand, play_style)
    players[new_player.player_id] = new_player

    print("Player added:", new_player.name)
    return new_player



def display_player_profile(player):
    print("\n----- PLAYER PROFILE -----")
    print("Name:", player.name)
    print("Grip:", player.grip)
    print("Playing hand:", player.playing_hand)
    print("Play style:", player.play_style)
    print("ELO rating:", player.elo_rating)
    print("Matches won:", player.matches_won)
    print("Matches lost:", player.matches_lost)
    print("Points scored:", player.points_scored)
    print("Points conceded:", player.points_conceded)
    print("--------------------------\n")

def choose_player_from_list(players):
    if len(players) == 0:
        print("No players available.")
        return
    player_list = list(players.values())
    print("\nSelect a player:   ")
    for index, player in enumerate(player_list, start=1):  #starting at 1 instead of 0 to avoid confusion
        print(f"{index} --- {player.name}")

    choice = input("Enter number:  ")

    if choice.isdigit() == False:
        print("Invalid input.")
        return
    choice = int(choice)
    if choice < 1 or choice > len(player_list):
        print("Choice out of range.")
        return
    
    selected_player = player_list[choice-1]  #index starts from 0
    display_player_profile(selected_player)

    return selected_player


def create_match(players):
    print("\n---CREATE MATCH---")
    print("\nSelect Player 1: ")
    print("1- Create new player")
    print("2- Select existing player")
    choice = input("Enter choice: ")
    if choice == '1':
        name = input("Enter player name: ")
        grip = input("Grip (shakehand/penhold): ").lower()
        playing_hand = input("Playing hand (right/left): ").lower()
        play_style = input(
            "Play style (attacker/defender/all-rounder/"
            "counter-attacker/chopper): "
        ).lower()

        player_one = add_player(
            players, name, grip, playing_hand, play_style
        )
    elif choice == '2':
        player_one = choose_player_from_list(players)
        if player_one is None:
            return
    else:
        print("Invalid input.")
        return
    if player_one is None:
        return

    print("\nPlayer 2:")
    print("1 - Select existing player")
    print("2 - Create new player")

    choice = input("Enter choice: ")

    if choice == "1":
        player_two = choose_player_from_list(players)
        if player_two is None:
            return

    elif choice == "2":
        name = input("Enter player name: ")
        grip = input("Grip (shakehand/penhold): ").lower()
        playing_hand = input("Playing hand (right/left): ").lower()
        play_style = input(
            "Play style (attacker/defender/all-rounder/"
            "counter-attacker/chopper): "
        ).lower()
        
        player_two = add_player(
            players, name, grip, playing_hand, play_style
        )


    else:
        print("Invalid input.")
        return

    if player_two is None:
        return

    if player_one.player_id == player_two.player_id:
        print("A player cannot play against themselves.")
        return

    print("\nSelect game configuration:")
    print("1 - Basic")
    print("   11 points, deuce enabled, no golden point, 1 game")

    print("2 - Advanced")
    print("Choose 11 or 21 points, deuce or golden point, and Best of 3/5/7, One Game, or Unlimited")
    choice = input("Enter choice: ")

    if choice == "1":
        game_config = create_basic_game_config()
    elif choice == "2":
        game_config = create_advanced_game_config()
    else:
        print("Invalid input.")
        return
    print("\n--- MATCH SUMMARY ---")
    print(f"Player 1: {player_one.name}")
    print(f"Player 2: {player_two.name}")
    print(f"Points per game: {game_config['points_per_game']}")
    print(f"Deuce enabled: {game_config['deuce_enabled']}")
    print(f"Golden point enabled: {game_config['golden_point_enabled']}")
    print(f"Games needed to win: {game_config['games_needed_to_win']}")

    return Match(player_one, player_two, game_config)

class Game:
    def __init__(self, player_one, player_two, game_config, save_results,
                 initial_server=None):
        self.player_one = player_one
        self.player_two = player_two
        self.game_config = game_config
        self.save_results = save_results
        self.initial_server_id = (
            initial_server.player_id if initial_server is not None else None
        )

        '''self.games_won = {
            player_one.player_id: 0,
            player_two.player_id: 0
        }'''

        #self.match_finished = False
        #self.match_winner = None

        self.current_game_score = {
            player_one.player_id: 0,
            player_two.player_id: 0
        }
        self.current_game_finished = False
        self.current_game_winner = None

        self.events = []
        self.game_id = str(uuid.uuid4())
        self.match_id = None

    def to_dict(self):
        return {
            "game_id": self.game_id,
            "match_id": self.match_id,
            "initial_server_id": self.initial_server_id,
            "score": dict(self.current_game_score),
            "finished": self.current_game_finished,
            "winner_id": (
                self.current_game_winner.player_id
                if self.current_game_winner is not None else None
            ),
            "events": copy.deepcopy(self.events),
        }

    @classmethod
    def from_dict(cls, data, players, game_config):
        if not isinstance(data, dict) or not isinstance(data.get("events"), list):
            raise ValueError("Game record must be an object with an events list.")
        player_one = players.get(data.get("player_one_id"))
        player_two = players.get(data.get("player_two_id"))
        # Older state stores player IDs only at the match level.
        if player_one is None or player_two is None:
            raise ValueError("Game record references unknown players.")
        initial_server = players.get(data.get("initial_server_id"))
        if data.get("initial_server_id") is not None and initial_server is None:
            raise ValueError("Game record references an unknown initial server.")

        game = cls(player_one, player_two, game_config, save_results=True,
                   initial_server=initial_server)
        game.game_id = data.get("game_id") or str(uuid.uuid4())
        game.match_id = data.get("match_id")
        allowed_types = {
            EVENT_POINT, EVENT_UNDO, EVENT_FAULT, EVENT_LET,
            EVENT_FAULT_CORRECTION,
        }
        seen_ids = set()
        point_ids = set()
        fault_ids = set()
        faults_by_id = {}
        undone_point_ids = set()
        for event in data["events"]:
            if not isinstance(event, dict) or event.get("type") not in allowed_types:
                raise ValueError("Game contains an invalid event record.")
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or not event_id or event_id in seen_ids:
                raise ValueError("Game event IDs must be non-empty and unique.")
            seen_ids.add(event_id)
            if event["type"] == EVENT_POINT:
                if event.get("player_id") not in (player_one.player_id, player_two.player_id):
                    raise ValueError("Point event references an unknown scoring player.")
                server_id = event.get("server_id")
                if server_id is not None and server_id not in (player_one.player_id, player_two.player_id):
                    raise ValueError("Point event references an unknown server.")
                point_ids.add(event_id)
            elif event["type"] == EVENT_UNDO:
                if event.get("undone_event_id") not in point_ids:
                    raise ValueError("Undo event must target an earlier point event.")
                if event.get("undone_event_id") in undone_point_ids:
                    raise ValueError("A point cannot be undone more than once.")
                undone_point_ids.add(event.get("undone_event_id"))
            elif event["type"] == EVENT_FAULT:
                if event.get("point_event_id") not in point_ids:
                    raise ValueError("Fault event must reference its awarded point.")
                if (event.get("fault_player_id") not in (player_one.player_id, player_two.player_id)
                        or event.get("scoring_player_id") not in (player_one.player_id, player_two.player_id)):
                    raise ValueError("Fault event references an unknown player.")
                if event["fault_player_id"] == event["scoring_player_id"]:
                    raise ValueError("A fault point must be awarded to the other player.")
                fault_ids.add(event_id)
                faults_by_id[event_id] = event
            elif event["type"] == EVENT_LET:
                if event.get("server_id") not in (player_one.player_id, player_two.player_id):
                    raise ValueError("Let event references an unknown server.")
            elif event["type"] == EVENT_FAULT_CORRECTION:
                if event.get("fault_event_id") not in fault_ids:
                    raise ValueError("Fault correction must target an earlier fault event.")
                if event.get("point_event_id") != faults_by_id[event["fault_event_id"]].get("point_event_id"):
                    raise ValueError("Fault correction must reference the point awarded for its fault.")
                new_scorer = event.get("new_scoring_player_id")
                if new_scorer is not None and new_scorer not in (player_one.player_id, player_two.player_id):
                    raise ValueError("Fault correction references an unknown scoring player.")
        game.events = copy.deepcopy(data["events"])
        for event in game.events:
            if event.get("match_id") not in (None, game.match_id):
                raise ValueError("Game event references a different match.")
            if event.get("game_id") not in (None, game.game_id):
                raise ValueError("Game event references a different game.")
        game.recalculate_current_game_score()
        game.check_game_finished()
        return game

    def recalculate_current_game_score(self):
        self.current_game_score[self.player_one.player_id] = 0
        self.current_game_score[self.player_two.player_id] = 0

        for event in self.iter_valid_point_events():
            player_id = event["player_id"]
            if player_id not in self.current_game_score:
                raise ValueError(f'Point event has invalid player id: {player_id}')
            self.current_game_score[player_id] += 1

    def iter_valid_point_events(self):
        """Replay awarded points after undo and fault-correction events."""
        undone_ids = {
            event.get("undone_event_id") for event in self.events
            if event.get("type") == EVENT_UNDO
        }
        faults_by_point = {}
        for event in self.events:
            if event.get("type") == EVENT_FAULT:
                faults_by_point[event.get("point_event_id")] = event
        latest_correction = {}
        for event in self.events:
            if event.get("type") == EVENT_FAULT_CORRECTION:
                latest_correction[event.get("fault_event_id")] = event
        score = {self.player_one.player_id: 0, self.player_two.player_id: 0}
        server_id = self.initial_server_id
        normal_interval = 2 if self.game_config["points_per_game"] == 11 else 5
        for event in self.events:
            if event.get("type") != EVENT_POINT or event.get("event_id") in undone_ids:
                continue
            fault = faults_by_point.get(event.get("event_id"))
            correction = latest_correction.get(fault.get("event_id")) if fault else None
            if correction is not None:
                corrected_scorer = correction.get("new_scoring_player_id")
                if corrected_scorer is None:
                    continue
                effective = dict(event)
                effective["player_id"] = corrected_scorer
            else:
                effective = dict(event)
            if effective.get("server_id") is None:
                effective["server_id"] = server_id
            scorer_id = effective["player_id"]
            if scorer_id not in score:
                raise ValueError(f"Point event has invalid player ID: {scorer_id}")
            yield effective
            score[scorer_id] += 1
            total = score[self.player_one.player_id] + score[self.player_two.player_id]
            at_deuce = (
                score[self.player_one.player_id] >= self.game_config["points_per_game"] - 1
                and score[self.player_two.player_id] >= self.game_config["points_per_game"] - 1
            )
            interval = 1 if at_deuce else normal_interval
            if server_id in score and total % interval == 0:
                server_id = (
                    self.player_two.player_id
                    if server_id == self.player_one.player_id
                    else self.player_one.player_id
                )

    def server_id_for_next_point(self):
        """Return the server for the next point, derived from the valid point stream."""
        server_id = self.initial_server_id
        if server_id not in (self.player_one.player_id, self.player_two.player_id):
            return None
        points_to_win = self.game_config["points_per_game"]
        normal_interval = 2 if points_to_win == 11 else 5
        score = {self.player_one.player_id: 0, self.player_two.player_id: 0}
        for event in self.iter_valid_point_events():
            score[event["player_id"]] += 1
            total = score[self.player_one.player_id] + score[self.player_two.player_id]
            at_deuce = (
                score[self.player_one.player_id] >= points_to_win - 1
                and score[self.player_two.player_id] >= points_to_win - 1
            )
            interval = 1 if at_deuce else normal_interval
            if total % interval == 0:
                server_id = (
                    self.player_two.player_id
                    if server_id == self.player_one.player_id
                    else self.player_one.player_id
                )
        return server_id

    def correct_fault(self, fault_event_id, reason, new_scoring_player_id=None):
        """Correct a fault explicitly; None removes its point award."""
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("A reason is required to correct a fault.")
        fault = next((event for event in self.events
                      if event.get("type") == EVENT_FAULT
                      and event.get("event_id") == fault_event_id), None)
        if fault is None:
            raise ValueError(f"Unknown fault event ID: {fault_event_id}")
        if new_scoring_player_id is not None and new_scoring_player_id not in (
            self.player_one.player_id, self.player_two.player_id
        ):
            raise ValueError("Corrected point winner must be one of the game players or None.")
        self.events.append({
            "type": EVENT_FAULT_CORRECTION,
            "event_id": str(uuid.uuid4()),
            "timestamp": utc_now_iso(),
            "match_id": self.match_id,
            "game_id": self.game_id,
            "fault_event_id": fault_event_id,
            "point_event_id": fault.get("point_event_id"),
            "new_scoring_player_id": new_scoring_player_id,
            "reason": reason.strip(),
        })
        self.recalculate_current_game_score()
        self.current_game_finished = False
        self.current_game_winner = None
        self.check_game_finished()


    def add_point(self, scoring_player, server_id=None):
        if self.current_game_finished:
            print("This game has finished. No more points can be added.")
            return
        if scoring_player not in (self.player_one, self.player_two):
            raise ValueError("Scoring player must be one of the players in this game.")
        server_id = server_id or self.server_id_for_next_point()
        if server_id is not None and server_id not in (
            self.player_one.player_id, self.player_two.player_id
        ):
            raise ValueError("Server must be one of the players in this game.")
        #while self.current_game_finished == False:
        
            #point_winner = input("Point Winner (1/2):  ")
            # player_one
        '''self.current_game_score[scoring_player.player_id] += 1
        self.check_game_finished()
        if self.current_game_finished:
            self.update_games_won()
            self.check_match_finished'''
        

        
        event = {
            "type": EVENT_POINT,
            "event_id": str(uuid.uuid4()),
            "timestamp": utc_now_iso(),
            "player_id": scoring_player.player_id,
            "server_id": server_id,
            "match_id": self.match_id,
            "game_id": self.game_id,
        }
        self.events.append(event)

        self.recalculate_current_game_score()
        self.check_game_finished()
    def add_fault(self, fault_player, server_id=None):
        if self.current_game_finished:
            print("This game has finished. No more faults can be recorded.")
            return
        if fault_player == self.player_one:
            scoring_player = self.player_two
        elif fault_player == self.player_two:
            scoring_player = self.player_one
        else:
            print("Invalid input.")
            return
        server_id = server_id or self.server_id_for_next_point()
        if server_id is not None and server_id not in (
            self.player_one.player_id, self.player_two.player_id
        ):
            raise ValueError("Server must be one of the players in this game.")
        point_event = {
                    "type": EVENT_POINT,
                    'event_id':str(uuid.uuid4()),
                    'timestamp': utc_now_iso(),
                    "player_id": scoring_player.player_id,
                    "server_id": server_id,
                    "match_id": self.match_id,
                    "game_id": self.game_id}
        fault_event = {
            'type' : EVENT_FAULT,
            "event_id": str(uuid.uuid4()),
            'timestamp': utc_now_iso(),
            'point_event_id':point_event['event_id'],
            'fault_player_id' : fault_player.player_id,
            'scoring_player_id' : scoring_player.player_id,
            'match_id': self.match_id,
            'game_id': self.game_id

        }

        
        self.events.append(point_event)
        self.events.append(fault_event)
        self.recalculate_current_game_score()
        self.check_game_finished()

    def add_let(self, server_id=None):
        """Record a let without awarding a point."""
        if self.current_game_finished:
            print("This game has finished. No more lets can be recorded.")
            return
        if server_id not in (self.player_one.player_id, self.player_two.player_id):
            raise ValueError("Let event must identify a valid server.")
        self.events.append({
            "type": EVENT_LET,
            "event_id": str(uuid.uuid4()),
            "timestamp": utc_now_iso(),
            "server_id": server_id,
            "match_id": self.match_id,
            "game_id": self.game_id,
        })


    def check_game_finished(self):
        #if (self.current_game_score[self.player_one.player_id] == self.game_config['points_per_game'] - 1) and (self.current_game_score[self.player_two.player_id] == self.game_config['points_per_game'] - 1):        
        points_to_win = self.game_config['points_per_game']
        score_1 = self.current_game_score[self.player_one.player_id]
        score_2 = self.current_game_score[self.player_two.player_id]
        deuce_enabled = self.game_config['deuce_enabled']
        golden_point_enabled = self.game_config['golden_point_enabled']

        if score_1 < points_to_win - 1 or score_2 < points_to_win - 1:
            if score_1 >= points_to_win:
                self.current_game_finished = True
                self.current_game_winner = self.player_one
            elif score_2 >= points_to_win:
                self.current_game_finished = True
                self.current_game_winner = self.player_two
            return
        if score_1 == score_2: #deuce
            return
        
        if golden_point_enabled:
        # next point wins
            if score_1 >= points_to_win:
                self.current_game_finished = True
                self.current_game_winner = self.player_one
            elif score_2 >= points_to_win:
                self.current_game_finished = True
                self.current_game_winner = self.player_two
        else:
            # must lead by 2
            if score_1 >= points_to_win and score_1 - score_2 >= 2:
                self.current_game_finished = True
                self.current_game_winner = self.player_one
            elif score_2 >= points_to_win and score_2 - score_1 >= 2:
                self.current_game_finished = True
                self.current_game_winner = self.player_two


            
        
        '''if self.current_game_score[self.player_one.player_id]  >=  self.game_config['points_per_game']:
            self.current_game_finished = True
            self.current_game_winner = self.player_one
        elif self.current_game_score[self.player_two.player_id]  >=  self.game_config['points_per_game']:
            self.current_game_finished = True
            self.current_game_winner = self.player_two
        else:
            pass'''
    def reset_current_game(self):
        if self.events:
            raise RuntimeError(
                "Cannot reset a game with recorded events without losing its audit history. "
                "Create a new Game instance instead."
            )
        self.current_game_finished  = False
        self.current_game_winner = None
        self.current_game_score[self.player_one.player_id] = 0
        self.current_game_score[self.player_two.player_id] = 0
    


    def undo_last_point(self, reason):
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("A reason is required to undo a point.")
            valid_point_ids = {
                event["event_id"] for event in self.iter_valid_point_events()
            }

            last_point = None
            for event in reversed(self.events):
                if event['type'] != EVENT_POINT:
                    continue
                if event.get('event_id') not in valid_point_ids:
                    continue
                last_point = event
                break
            if last_point is None:
                print("No point to undo.")
                return
            undo_event = {"type": EVENT_UNDO,
            "event_id": str(uuid.uuid4()),
            "timestamp": utc_now_iso(),
            "undone_event_id": last_point["event_id"],
            "undone_player_id": last_point["player_id"],
            "reason": reason,
            "match_id": self.match_id,
            "game_id": self.game_id
            }

            self.events.append(undo_event)

            
            self.recalculate_current_game_score()

        
            self.current_game_finished = False
            self.current_game_winner = None

            self.check_game_finished()
                
            







def create_basic_game_config():
    return {
        'points_per_game' : 11,
            'deuce_enabled' : True,
            'golden_point_enabled' : False,
            #'unlimited_games' : True
            'games_needed_to_win' : 1
        }
    
def create_advanced_game_config():
    config = {}
    while True:
        choice = input("Points per game (11/21):  ")
        if choice in ['11','21']:
            config['points_per_game'] = int(choice)
            break
        print("Invalid input.")
    while True:
        choice = input("Deuce (1) or Golden Point (2)?")
        if choice == '1':
            config['deuce_enabled'] = True 
            config['golden_point_enabled'] = False
            break
        elif choice == '2':
            config['golden_point_enabled'] = True 
            config['deuce_enabled'] = False
            break
        else:
            print("Invalid input.")
    while True:
        choice = input('''
                           Number of Games? \n
                           1. Best of 3\n
                           2. Best of 5\n
                           3. Best of 7\n
                           4. One Game\n
                           5. Unlimited
''')
        if choice == '1':
            config['games_needed_to_win'] = 2
        
            break
        elif choice == '2':
            config['games_needed_to_win'] = 3
            break
        elif choice == '3':
            config['games_needed_to_win'] = 4
            break
        elif choice == '4':
            config['games_needed_to_win'] = 1
            break
        elif choice == '5':
            config['games_needed_to_win'] = None
            break
        else:
            print("Invalid input.")
    return config



def score_check(game):
    print("\nCurrent score:  ")
    print(f"{game.player_one.name} : {game.current_game_score[game.player_one.player_id]}")
    print(f"{game.player_two.name} : {game.current_game_score[game.player_two.player_id]}")
    '''
    print("\nWho won the point?")
    print("1 -", game.player_one.name)
    print("2 -", game.player_two.name)

    choice = input("Enter choice (1-6): ")

        if choice == "1":
            engine.add_point(player_one)
        elif choice == "2":
            engine.add_point(player_two)
        else:
            print("Invalid input. Try again.")'''


def input_point_winner(game,match):
    score_check(game)
    print(f"\n{match.server.name} is serving.")
    print("\nWho won the point?")
    print("1 -", game.player_one.name)
    print("2 -", game.player_two.name)
    print("3 - Fault")
    print("4 - Let")
    print("5 - Undo")
    print("6 - Correct a previously recorded fault")

    choice = input("Enter choice (1-5): ")
    if choice == "1":
        game.add_point(game.player_one, match.server.player_id)
        match.update_server(game)

    elif choice == "2":
        game.add_point(game.player_two, match.server.player_id)
        match.update_server(game)

    elif choice == "3":
        print("Who committed the fault?")
        print("1 -", game.player_one.name)
        print("2 -", game.player_two.name)

        fault_player = input("Enter 1 or 2: ")

        if fault_player == "1":
            game.add_fault(game.player_one, match.server.player_id)
            match.update_server(game)

        elif fault_player == "2":
            game.add_fault(game.player_two, match.server.player_id)
            match.update_server(game)

        else:
            print("Invalid input.")

    elif choice == "4":
        game.add_let(match.server.player_id)
        print("Let — no point awarded.")

    elif choice == "5":
        reason = input("Reason for undo: ")
        game.undo_last_point(reason)
        match.update_server(game)

    elif choice == "6":
        faults = [event for event in game.events if event.get("type") == EVENT_FAULT]
        if not faults:
            print("This game has no recorded faults to correct.")
            return
        for index, event in enumerate(faults, start=1):
            print(f"{index}. Fault event {event['event_id']} — {event['fault_player_id']}")
        selected = input("Fault number: ").strip()
        if not selected.isdigit() or not 1 <= int(selected) <= len(faults):
            print("Choose a listed fault number.")
            return
        print("Corrected outcome: 1/2 awards the point to that player; 3 removes the point.")
        outcome = input("Enter 1, 2, or 3: ").strip()
        if outcome == "1":
            corrected_scorer = game.player_one.player_id
        elif outcome == "2":
            corrected_scorer = game.player_two.player_id
        elif outcome == "3":
            corrected_scorer = None
        else:
            print("Choose 1, 2, or 3.")
            return
        reason = input("Reason for correction: ")
        game.correct_fault(faults[int(selected) - 1]["event_id"], reason, corrected_scorer)
        match.update_server(game)

    else:
        print("Invalid input. Try again.")


def print_final_match_results(match):
    print("\nMATCH RESULTS:")
    print(f"{match.player_one.name} won {match.games_won[match.player_one.player_id]}")
    print(f"{match.player_two.name} won {match.games_won[match.player_two.player_id]}")

def run_match(match):
    if (not match.match_finished and match.current_game is None
            and match.game_config["games_needed_to_win"] is not None
            and any(wins >= match.game_config["games_needed_to_win"]
                    for wins in match.games_won.values())):
        raise ValueError(
            "This match already has a clinching score. Correct the recorded result "
            "or explicitly revise its game history before continuing play."
        )
    while not match.match_finished:
        if match.current_game is not None:
            game = match.current_game
            if match.server is None:
                match.server = (
                    match.player_one
                    if game.initial_server_id == match.player_one.player_id
                    else match.player_two
                )
                match.update_server(game)
        else:
            if match.server is None:
                match.set_server_from_toss()
            elif match.games:
                match.server = match.next_game_server()
            game = match.create_game(match.server)
        print(f"\n{match.server.name} is serving to start the game.")
        while True:
            while not game.current_game_finished:
                input_point_winner(game, match)
                match.notify_state_change()

            print(f"Game winner: {game.current_game_winner.name}")
            choice = input("(1) Accept game result | (2) Undo last point: ")
            if choice == "1":
                break
            if choice == "2":
                reason = input("Reason for undo: ")
                game.undo_last_point(reason)
                match.update_server(game)
                match.notify_state_change()
                continue
            print("Invalid input.")

        print("\nEVENT HISTORY:")
        print(game.events)
        match.games.append(game)
        match.current_game = None
        match.update_games_won(game)
        match.check_match_finished()
        match.status = "completed" if match.match_finished else "in_progress"
        if match.match_finished:
            match.completed_at = utc_now_iso()
        match.notify_state_change()
        print(f"Games won: "
              
    
        f"{match.player_one.name} - {match.games_won[match.player_one.player_id]}, "
        f"{match.player_two.name} - {match.games_won[match.player_two.player_id]}"
        )

        if match.match_finished:
            break

        # Unlimited match: ask whether to continue
        if match.game_config["games_needed_to_win"] is None:
            while True:
                choice = input("(1) Play another game | (2) End match: ").strip()
                if choice == "1":
                    break
                if choice == "2":
                    match.match_finished = True
                    match.status = "completed"
                    match.completed_at = utc_now_iso()
                    match.notify_state_change()
                    break
                print("Enter 1 or 2.")
            if choice == "2":
                break

    if match.match_winner is not None:
        if match.status != "walkover" and not match.rating_updated:
            match.rating_before = {
                match.player_one.player_id: match.player_one.elo_rating,
                match.player_two.player_id: match.player_two.elo_rating,
            }
            EloSystem.update_score(
                match.player_one,
                match.player_two,
                match.match_winner
            )
            match.rating_updated = True

        if not match.records_updated:
            point_counts = {
                match.player_one.player_id: 0,
                match.player_two.player_id: 0,
            }
            for completed_game in match.games:
                for event in completed_game.iter_valid_point_events():
                    if event.get("player_id") in point_counts:
                        point_counts[event["player_id"]] += 1

            p1 = match.player_one
            p2 = match.player_two
            p1.points_scored += point_counts[p1.player_id]
            p2.points_scored += point_counts[p2.player_id]
            p1.points_conceded += point_counts[p2.player_id]
            p2.points_conceded += point_counts[p1.player_id]
            match.match_winner.matches_won += 1
            loser = p2 if match.match_winner == p1 else p1
            loser.matches_lost += 1
            match.records_updated = True
        match.notify_state_change()

    print_final_match_results(match)
    
'''def deuce_logic(game):
    is_deuce = False
    while not game.match_finished:
        while not game.current_game_finished:
            if game.current_game_score[game.player_one.player_id] == 10 and game.current_game_score[game.player_two.player_id] == 10:
                is_deuce = True
            while is_deuce:
'''
        








class Match:
    def __init__(self,player_one,player_two,game_config):
        if player_one is None or player_two is None:
            raise ValueError("Both match players must be provided.")
        if not getattr(player_one, "player_id", None) or not getattr(player_two, "player_id", None):
            raise ValueError("Both match players must have valid player IDs.")
        if player_one.player_id == player_two.player_id:
            raise ValueError("A player cannot play against themselves.")
        if not isinstance(game_config, dict):
            raise ValueError("Game configuration must be a dictionary.")
        required_config = {
            "points_per_game",
            "deuce_enabled",
            "golden_point_enabled",
            "games_needed_to_win",
        }
        missing_config = required_config - game_config.keys()
        if missing_config:
            raise ValueError(
                f"Game configuration is missing: {', '.join(sorted(missing_config))}"
            )
        if game_config["points_per_game"] not in (11, 21):
            raise ValueError("Points per game must be 11 or 21.")
        if not isinstance(game_config["deuce_enabled"], bool) or not isinstance(
            game_config["golden_point_enabled"], bool
        ):
            raise ValueError("Deuce and golden-point settings must be true or false.")
        if game_config["deuce_enabled"] == game_config["golden_point_enabled"]:
            raise ValueError("Enable exactly one of deuce or golden point.")
        games_needed = game_config["games_needed_to_win"]
        if games_needed is not None and (
            not isinstance(games_needed, int)
            or isinstance(games_needed, bool)
            or games_needed not in (1, 2, 3, 4)
        ):
            raise ValueError("Games needed to win must be 1, 2, 3, 4, or None.")

        self.player_one = player_one
        self.player_two = player_two
        self.game_config = game_config
        self.games_won = {
            player_one.player_id : 0,
            player_two.player_id : 0
        }
        self.match_finished = False
        self.match_winner = None
        self.games = []
        self.current_game = None
        self.match_id = str(uuid.uuid4())
        self.created_at = utc_now_iso()
        self.completed_at = None
        self.status = "scheduled"
        self.round_number = None
        self.slot_number = None
        self.table_assignment = None
        self.manually_overridden = False

        self.server = None
        self.toss_winner = None
        self.rating_updated = False
        self.rating_before = None
        self.records_updated = False
        self._on_change = None

    def notify_state_change(self):
        if self._on_change is not None:
            self._on_change()

    def create_game(self, initial_server):
        if initial_server not in (self.player_one, self.player_two):
            raise ValueError("Initial server must be one of the match players.")
        game = Game(
            self.player_one, self.player_two, self.game_config,
            save_results=True, initial_server=initial_server
        )
        game.match_id = self.match_id
        self.current_game = game
        self.server = initial_server
        self.status = "in_progress"
        self.notify_state_change()
        return game

    def next_game_server(self):
        """Return the opening server for a new game, alternating from the last game."""
        if not self.games:
            return self.server
        previous_server_id = self.games[-1].initial_server_id
        if previous_server_id == self.player_one.player_id:
            return self.player_two
        if previous_server_id == self.player_two.player_id:
            return self.player_one
        raise ValueError("The previous game has no valid initial server.")

    def to_dict(self):
        games = []
        for game in self.games:
            game_data = game.to_dict()
            game_data["match_id"] = self.match_id
            game_data["player_one_id"] = self.player_one.player_id
            game_data["player_two_id"] = self.player_two.player_id
            games.append(game_data)
        current_game = None
        if self.current_game is not None:
            current_game = self.current_game.to_dict()
            current_game["match_id"] = self.match_id
            current_game["player_one_id"] = self.player_one.player_id
            current_game["player_two_id"] = self.player_two.player_id
        return {
            "match_id": self.match_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "player_one_id": self.player_one.player_id,
            "player_two_id": self.player_two.player_id,
            "game_config": copy.deepcopy(self.game_config),
            "status": self.status,
            "match_finished": self.match_finished,
            "winner_id": self.match_winner.player_id if self.match_winner else None,
            "games_won": dict(self.games_won),
            "games": games,
            "current_game": current_game,
            "server_id": self.server.player_id if self.server else None,
            "toss_winner_id": self.toss_winner.player_id if self.toss_winner else None,
            "round_number": self.round_number,
            "slot_number": self.slot_number,
            "table_assignment": self.table_assignment,
            "manually_overridden": self.manually_overridden,
            "rating_updated": self.rating_updated,
            "rating_before": copy.deepcopy(self.rating_before),
            "records_updated": self.records_updated,
        }

    @classmethod
    def from_dict(cls, data, players):
        if not isinstance(data, dict):
            raise ValueError("Match record must be an object.")
        player_one = players.get(data.get("player_one_id"))
        player_two = players.get(data.get("player_two_id"))
        if player_one is None or player_two is None:
            raise ValueError("Match record references unknown players.")
        match = cls(player_one, player_two, data.get("game_config"))
        match_id = data.get("match_id")
        if match_id is not None and (not isinstance(match_id, str) or not match_id):
            raise ValueError("Match ID must be a non-empty string.")
        match.match_id = match_id or str(uuid.uuid4())
        match.created_at = data.get("created_at", utc_now_iso())
        match.completed_at = data.get("completed_at")
        allowed_statuses = {
            "scheduled", "in_progress", "completed", "postponed",
            "cancelled", "walkover", "retired", "reopened",
        }
        status = data.get("status", "scheduled")
        if status not in allowed_statuses:
            raise ValueError(f"Invalid match status: {status!r}")
        match.status = status
        game_rows = data.get("games", [])
        if not isinstance(game_rows, list):
            raise ValueError("Match games field must be a list.")
        expected_player_ids = {player_one.player_id, player_two.player_id}
        for game_row in game_rows:
            if (not isinstance(game_row, dict)
                    or {game_row.get("player_one_id"), game_row.get("player_two_id")}
                    != expected_player_ids):
                raise ValueError("Game record players do not match the parent match.")
        match.games = [Game.from_dict(item, players, match.game_config)
                       for item in game_rows]
        if any(game.current_game_winner is None for game in match.games):
            raise ValueError("Completed-game history contains a game without a winner.")
        current_game_data = data.get("current_game")
        if current_game_data is not None:
            if (not isinstance(current_game_data, dict)
                    or {current_game_data.get("player_one_id"), current_game_data.get("player_two_id")}
                    != expected_player_ids):
                raise ValueError("Current-game players do not match the parent match.")
            match.current_game = Game.from_dict(
                current_game_data, players, match.game_config
            )
        for game in [*match.games, *([match.current_game] if match.current_game else [])]:
            if game.match_id not in (None, match.match_id):
                raise ValueError("Game record belongs to a different match.")
            game.match_id = match.match_id
            for event in game.events:
                if event.get("match_id") not in (None, match.match_id):
                    raise ValueError("Event record belongs to a different match.")
                if event.get("game_id") not in (None, game.game_id):
                    raise ValueError("Event record belongs to a different game.")
                event["match_id"] = match.match_id
                event["game_id"] = game.game_id
        match.games_won = {player_one.player_id: 0, player_two.player_id: 0}
        for game in match.games:
            if game.current_game_winner is not None:
                match.games_won[game.current_game_winner.player_id] += 1
        winner_id = data.get("winner_id")
        if winner_id is not None:
            match.match_winner = players.get(winner_id)
            if match.match_winner not in (player_one, player_two):
                raise ValueError("Match winner ID is not one of the match players.")
        match.match_finished = bool(data.get("match_finished", False))
        match.server = players.get(data.get("server_id"))
        match.toss_winner = players.get(data.get("toss_winner_id"))
        if data.get("server_id") is not None and match.server not in (player_one, player_two):
            raise ValueError("Match server ID is not one of the match players.")
        if data.get("toss_winner_id") is not None and match.toss_winner not in (player_one, player_two):
            raise ValueError("Toss winner ID is not one of the match players.")
        match.round_number = data.get("round_number")
        match.slot_number = data.get("slot_number")
        match.table_assignment = data.get("table_assignment")
        match.manually_overridden = bool(data.get("manually_overridden", False))
        match.rating_updated = bool(data.get("rating_updated", False))
        match.rating_before = copy.deepcopy(data.get("rating_before"))
        match.records_updated = bool(data.get("records_updated", False))
        if match.rating_before is not None:
            if (not isinstance(match.rating_before, dict)
                    or set(match.rating_before) != expected_player_ids
                    or any(not isinstance(value, int) or isinstance(value, bool)
                           for value in match.rating_before.values())):
                raise ValueError("Match rating_before must contain integer ratings for both players.")
        terminal_status = status in {"completed", "walkover", "retired"}
        if match.match_finished != terminal_status:
            raise ValueError("Match status and match_finished flag are inconsistent.")
        if match.match_winner is not None and not match.match_finished:
            raise ValueError("An unfinished match cannot contain a winner.")
        if status in {"walkover", "retired"} and match.match_winner is None:
            raise ValueError("Walkover and retired matches must record a winner.")
        if (status == "completed" and match.match_winner is None
                and match.game_config["games_needed_to_win"] is not None):
            raise ValueError("A completed finite-length match must record a winner.")
        return match

    def set_server_from_toss(self):
        print(f'\nWho won the toss?')
        print(f'1. {self.player_one.name}')
        print(f'2. {self.player_two.name}')
        while True:
            choice = input("Enter 1 or 2:  ")
            if choice == '1':
                self.toss_winner = self.player_one
                break

            elif choice == '2':
                self.toss_winner = self.player_two
                break
            else:
                print("Invalid input.")

        while True:
            print(f"{self.toss_winner.name}, choose:")
            print("1. Serve first")
            print("2. Receive first")
            choice = input("Enter 1 or 2: ")
            if choice == "1":
                self.server = self.toss_winner
                return
            if choice == "2":
                self.server = (
                    self.player_two
                    if self.toss_winner == self.player_one
                    else self.player_one
                )
                return
            print("Invalid input.")

    def update_server(self, game):
        """Rebuild the next server from the game's initial server and valid points."""
        server_id = game.server_id_for_next_point()
        if server_id is None:
            raise ValueError("Game is missing a valid initial server.")
        self.server = (
            self.player_one
            if server_id == self.player_one.player_id
            else self.player_two
        )

    def update_games_won(self,game):
            if game.current_game_winner is None:
                raise ValueError("Cannot record a game without a winner.")
            winner_id = game.current_game_winner.player_id
            self.games_won[winner_id] += 1
    def check_match_finished(self):
        games_needed = self.game_config['games_needed_to_win']
        if games_needed is None:
            return
        for player_id, wins in self.games_won.items():
            if wins >= games_needed:
                self.match_finished= True
                if player_id == self.player_one.player_id:
                    self.match_winner = self.player_one
                else:
                    self.match_winner = self.player_two

class EloSystem:
    k_factor = 24  #scaling factor. 24 is the norm
    @staticmethod
    
    def expected_score(rating_a,rating_b):
        #elo formula as used in Chess
        rating_difference = rating_b - rating_a
        exponent = rating_difference / 400
        expected = 1 / (1+10**exponent)
        return expected
    @staticmethod
    def update_score(player_a,player_b,winner):
        rating_a = player_a.elo_rating
        rating_b = player_b.elo_rating

        expected_a = EloSystem.expected_score(rating_a, rating_b)
        expected_b = EloSystem.expected_score(rating_b,rating_a)

        if winner == player_a:
            actual_a = 1
            actual_b = 0
        elif winner == player_b:
            actual_a = 0
            actual_b = 1
        else:
            raise ValueError("Winner must be one of the two match players.")
        new_rating_a = rating_a + EloSystem.k_factor * (actual_a - expected_a)
        new_rating_b = rating_b + EloSystem.k_factor * (actual_b - expected_b)

        player_a.elo_rating = round(new_rating_a)
        player_b.elo_rating = round(new_rating_b)

class Tournament:
    def __init__(self,name,players):
        self.name = name
        self.players = players
        self.matches = []
        self.finished = False
        self.winner = None
        self.tournament_id = str(uuid.uuid4())
        self.created_at = utc_now_iso()
        self.seeds = {}
        self.original_draw = None
        self.draw_metadata = {}
        self.audit_log = []
        self.manually_overridden = False
        self.automatic_progression_paused = False
        self._on_change = None

    def record_change(self, action, entity_type, entity_id, previous, new_value, reason):
        self._require_reason(reason)
        entry = {
            "event_id": str(uuid.uuid4()),
            "timestamp": utc_now_iso(),
            "actor": getpass.getuser(),
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "previous_value": copy.deepcopy(previous),
            "new_value": copy.deepcopy(new_value),
            "reason": reason.strip(),
        }
        self.audit_log.append(entry)
        self.manually_overridden = True
        if self._on_change is not None:
            self._on_change()
        return entry

    @staticmethod
    def _require_reason(reason):
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("An audit reason is required for tournament edits.")

    def add_entrant(self, player, reason):
        self._require_reason(reason)
        if player is None or not getattr(player, "player_id", None):
            raise ValueError("A valid player is required as an entrant.")
        if any(existing.player_id == player.player_id for existing in self.players):
            raise ValueError("That player is already entered in this tournament.")
        self.players.append(player)
        self.seeds.setdefault(player.player_id, None)
        if isinstance(self, rrt):
            self.generate_matches()
            self.recalculate_standings()
        self.record_change("add_entrant", "player", player.player_id, None,
                           player.to_dict(), reason)
        return player

    def remove_entrant(self, player_id, reason):
        self._require_reason(reason)
        player = next((item for item in self.players if item.player_id == player_id), None)
        if player is None:
            raise ValueError(f"Unknown entrant ID: {player_id}")
        affected = [match for match in self.matches
                    if player_id in (match.player_one.player_id, match.player_two.player_id)]
        if any(match.status == "in_progress" or match.current_game is not None for match in affected):
            raise ValueError("Finish or explicitly correct in-progress matches before withdrawing an entrant.")
        previous_matches = []
        for match in affected:
            previous_matches.append({"match_id": match.match_id, "status": match.status})
            if match.status == "scheduled":
                match.status = "cancelled"
                match.match_finished = False
        previous_current_ids = (
            [item.player_id for item in self.current_players]
            if isinstance(self, kot) else None
        )
        self.players.remove(player)
        if isinstance(self, kot):
            self.current_players = [item for item in self.current_players
                                    if item.player_id != player_id]
        previous_seed = self.seeds.pop(player_id, None)
        self.record_change("remove_entrant", "player", player_id,
                           {"player": player.to_dict(), "seed": previous_seed,
                            "affected_matches": previous_matches,
                            "current_player_ids": previous_current_ids}, None, reason)
        if isinstance(self, rrt):
            self.recalculate_standings()
        return player

    def replace_entrant(self, old_player_id, new_player, reason):
        self._require_reason(reason)
        old_player = next((item for item in self.players if item.player_id == old_player_id), None)
        if old_player is None:
            raise ValueError(f"Unknown entrant ID: {old_player_id}")
        if new_player is None or any(p.player_id == new_player.player_id for p in self.players):
            raise ValueError("Replacement must be a valid player not already entered.")
        affected = [match for match in self.matches
                    if old_player_id in (match.player_one.player_id, match.player_two.player_id)]
        if any(match.status == "in_progress" or match.current_game is not None for match in affected):
            raise ValueError("Pause or finish in-progress matches before replacing an entrant.")
        if isinstance(self, kot) and (
            any(match.games or match.match_finished for match in affected)
            or any(row.get("completed") for row in self.draw_metadata.get("rounds", []))
        ):
            raise ValueError(
                "A knockout entrant cannot be replaced after bracket results have been recorded; "
                "correct or rebuild the bracket first."
            )
        index = self.players.index(old_player)
        old_seed = self.seeds.pop(old_player_id, None)
        self.players[index] = new_player
        if isinstance(self, kot):
            self.current_players = [
                new_player if item.player_id == old_player_id else item
                for item in self.current_players
            ]
        self.seeds[new_player.player_id] = old_seed
        replacements = []
        for match in affected:
            if match.games or match.match_finished:
                match.status = "cancelled"
                match.match_finished = False
                opponent = match.player_two if match.player_one.player_id == old_player_id else match.player_one
                replacement = Match(new_player, opponent, match.game_config)
                replacement.round_number = match.round_number
                replacement.slot_number = match.slot_number
                replacement.table_assignment = match.table_assignment
                replacement._on_change = self._on_change
                self.matches.append(replacement)
                replacements.append({"superseded_match_id": match.match_id,
                                     "replacement_match_id": replacement.match_id})
            elif match.player_one.player_id == old_player_id:
                match.player_one = new_player
                match.games_won = {match.player_one.player_id: 0, match.player_two.player_id: 0}
            else:
                match.player_two = new_player
                match.games_won = {match.player_one.player_id: 0, match.player_two.player_id: 0}
        if isinstance(self, rrt):
            self.generate_matches()
            self.recalculate_standings()
        elif isinstance(self, kot):
            for row in self.draw_metadata.get("rounds", []):
                row["entrant_ids"] = [
                    new_player.player_id if player_id == old_player_id else player_id
                    for player_id in row.get("entrant_ids", [])
                ]
                row["bye_player_ids"] = [
                    new_player.player_id if player_id == old_player_id else player_id
                    for player_id in row.get("bye_player_ids", [])
                ]
                if row.get("bye_player_id") == old_player_id:
                    row["bye_player_id"] = new_player.player_id
            for bye in self.draw_metadata.get("byes", []):
                if bye.get("player_id") == old_player_id:
                    bye["player_id"] = new_player.player_id
            for plan in self.draw_metadata.get("match_plans", []):
                for key in ("player_one_id", "player_two_id"):
                    if plan.get(key) == old_player_id:
                        plan[key] = new_player.player_id
        self.record_change("replace_entrant", "player", old_player_id,
                           {"old": old_player.to_dict(), "replacement": new_player.to_dict(),
                            "superseded_matches": replacements},
                           new_player.to_dict(), reason)
        return old_player

    def set_seed(self, player_id, seed, reason):
        self._require_reason(reason)
        if not any(player.player_id == player_id for player in self.players):
            raise ValueError(f"Unknown entrant ID: {player_id}")
        if seed is not None and (
            not isinstance(seed, int) or isinstance(seed, bool) or seed < 1
        ):
            raise ValueError("Seed must be a positive integer or None.")
        if seed is not None and any(
            other_id != player_id and other_seed == seed
            for other_id, other_seed in self.seeds.items()
        ):
            raise ValueError(f"Seed {seed} is already assigned.")
        previous = self.seeds.get(player_id)
        self.seeds[player_id] = seed
        self.record_change("set_seed", "player", player_id, previous, seed, reason)

    def set_match_order(self, match_id, round_number, slot_number, reason):
        self._require_reason(reason)
        match = self._match_by_id(match_id)
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 1
               for value in (round_number, slot_number)):
            raise ValueError("Round and slot numbers must be positive integers.")
        if any(other.match_id != match_id
               and other.round_number == round_number
               and other.slot_number == slot_number for other in self.matches):
            raise ValueError("Another match already occupies that round and slot.")
        previous = {"round": match.round_number, "slot": match.slot_number}
        match.round_number = round_number
        match.slot_number = slot_number
        match.manually_overridden = True
        self.record_change("set_match_order", "match", match_id, previous,
                           {"round": round_number, "slot": slot_number}, reason)

    def reschedule_match(self, match_id, round_number, slot_number, table_assignment, reason):
        self._require_reason(reason)
        match = self._match_by_id(match_id)
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 1
               for value in (round_number, slot_number)):
            raise ValueError("Round and slot numbers must be positive integers.")
        if any(other.match_id != match_id
               and other.round_number == round_number
               and other.slot_number == slot_number for other in self.matches):
            raise ValueError("Another match already occupies that round and slot.")
        previous = {
            "round": match.round_number,
            "slot": match.slot_number,
            "table_assignment": match.table_assignment,
        }
        match.round_number = round_number
        match.slot_number = slot_number
        match.table_assignment = table_assignment
        match.manually_overridden = True
        self.record_change("reschedule_match", "match", match_id, previous,
                           {"round": round_number, "slot": slot_number,
                            "table_assignment": table_assignment}, reason)

    def pause_progression(self, reason):
        self._require_reason(reason)
        previous = self.automatic_progression_paused
        self.automatic_progression_paused = True
        self.record_change("pause_progression", "tournament", self.tournament_id,
                           previous, True, reason)

    def resume_progression(self, reason):
        self._require_reason(reason)
        previous = self.automatic_progression_paused
        self.automatic_progression_paused = False
        self.record_change("resume_progression", "tournament", self.tournament_id,
                           previous, False, reason)

    def correct_match_result(self, match_id, winner_id, reason, games_won=None):
        self._require_reason(reason)
        match = self._match_by_id(match_id)
        winner = next((player for player in (match.player_one, match.player_two)
                       if player.player_id == winner_id), None)
        if winner is None:
            raise ValueError("Corrected winner must be one of the match players.")
        previous = {
            "winner_id": match.match_winner.player_id if match.match_winner else None,
            "games_won": dict(match.games_won),
            "status": match.status,
        }
        if games_won is not None:
            if (not isinstance(games_won, dict)
                    or set(games_won) != {match.player_one.player_id, match.player_two.player_id}
                    or any(not isinstance(value, int) or isinstance(value, bool) or value < 0
                           for value in games_won.values())):
                raise ValueError("games_won must contain non-negative integer counts for both players.")
            match.games_won = dict(games_won)
        previous_winner = match.match_winner
        if match.records_updated:
            if previous_winner is not None and previous_winner != winner:
                previous_winner.matches_won = max(0, previous_winner.matches_won - 1)
                previous_loser = (
                    match.player_two if previous_winner == match.player_one
                    else match.player_one
                )
                previous_loser.matches_lost = max(0, previous_loser.matches_lost - 1)
                winner.matches_won += 1
                new_loser = match.player_two if winner == match.player_one else match.player_one
                new_loser.matches_lost += 1
        else:
            winner.matches_won += 1
            loser = match.player_two if winner == match.player_one else match.player_one
            loser.matches_lost += 1
            match.records_updated = True
        if match.rating_updated and match.rating_before:
            match.player_one.elo_rating = match.rating_before[match.player_one.player_id]
            match.player_two.elo_rating = match.rating_before[match.player_two.player_id]
        match.rating_before = {
            match.player_one.player_id: match.player_one.elo_rating,
            match.player_two.player_id: match.player_two.elo_rating,
        }
        EloSystem.update_score(match.player_one, match.player_two, winner)
        match.rating_updated = True
        match.match_winner = winner
        match.match_finished = True
        match.status = "completed"
        match.completed_at = utc_now_iso()
        match.manually_overridden = True
        self.record_change("correct_match_result", "match", match_id, previous,
                           {"winner_id": winner_id, "games_won": dict(match.games_won)}, reason)
        if isinstance(self, rrt):
            self.recalculate_standings()

    def mark_walkover(self, match_id, winner_id, reason):
        self.set_match_status(match_id, "walkover", reason, winner_id=winner_id)

    def reopen_match(self, match_id, reason):
        self.set_match_status(match_id, "reopened", reason)

    def swap_match_players(self, match_id_a, player_id_a, match_id_b, player_id_b, reason):
        self._require_reason(reason)
        match_a = self._match_by_id(match_id_a)
        match_b = self._match_by_id(match_id_b)
        if (match_a.status == "in_progress" or match_b.status == "in_progress"
                or match_a.games or match_b.games
                or match_a.current_game is not None or match_b.current_game is not None):
            raise ValueError(
                "Only matches with no recorded games can have their players swapped. "
                "Keep completed scores intact and create a corrected replacement match."
            )
        player_a = next((p for p in (match_a.player_one, match_a.player_two)
                         if p.player_id == player_id_a), None)
        player_b = next((p for p in (match_b.player_one, match_b.player_two)
                         if p.player_id == player_id_b), None)
        if player_a is None or player_b is None:
            raise ValueError("The selected players must occupy the selected match slots.")
        if match_a.status in {"completed", "walkover", "retired"} or match_b.status in {"completed", "walkover", "retired"}:
            raise ValueError("Reopen completed matches before changing their players.")
        previous = {match_id_a: [match_a.player_one.player_id, match_a.player_two.player_id],
                    match_id_b: [match_b.player_one.player_id, match_b.player_two.player_id]}
        self._replace_match_player(match_a, player_a.player_id, player_b)
        self._replace_match_player(match_b, player_b.player_id, player_a)
        self.record_change("swap_match_players", "matches", f"{match_id_a},{match_id_b}",
                           previous,
                           {match_id_a: [match_a.player_one.player_id, match_a.player_two.player_id],
                            match_id_b: [match_b.player_one.player_id, match_b.player_two.player_id]},
                           reason)

    def _replace_match_player(self, match, player_id, new_player):
        if match.player_one.player_id == player_id:
            match.player_one = new_player
        else:
            match.player_two = new_player
        match.games_won = {match.player_one.player_id: 0, match.player_two.player_id: 0}
        match.match_winner = None
        match.match_finished = False
        match.status = "reopened"
        match.manually_overridden = True

    def set_match_status(self, match_id, status, reason, winner_id=None):
        self._require_reason(reason)
        allowed = {"scheduled", "in_progress", "completed", "postponed",
                   "cancelled", "walkover", "retired", "reopened"}
        if status not in allowed:
            raise ValueError(f"Unsupported match status: {status!r}")
        match = self._match_by_id(match_id)
        winner = None
        if winner_id is not None:
            winner = next((p for p in (match.player_one, match.player_two)
                           if p.player_id == winner_id), None)
            if winner is None:
                raise ValueError("Match winner must be one of the match players.")
        if status in {"completed", "walkover", "retired"} and winner is None:
            raise ValueError("Completed, walkover, and retired matches require a winner.")
        previous = {"status": match.status,
                    "winner_id": match.match_winner.player_id if match.match_winner else None}
        old_winner = match.match_winner
        was_finished = match.match_finished and old_winner is not None
        will_finish = status in {"completed", "walkover", "retired"}
        if match.records_updated and old_winner is not None and (
            not will_finish or old_winner != winner
        ):
            old_loser = match.player_two if old_winner == match.player_one else match.player_one
            old_winner.matches_won = max(0, old_winner.matches_won - 1)
            old_loser.matches_lost = max(0, old_loser.matches_lost - 1)
            match.records_updated = False
        if match.rating_updated and match.rating_before and (
            not will_finish or status == "walkover" or old_winner != winner
        ):
            match.player_one.elo_rating = match.rating_before[match.player_one.player_id]
            match.player_two.elo_rating = match.rating_before[match.player_two.player_id]
            match.rating_updated = False
        match.status = status
        match.match_winner = winner
        match.match_finished = will_finish
        if match.match_finished:
            match.completed_at = utc_now_iso()
            if not match.records_updated:
                winner.matches_won += 1
                loser = match.player_two if winner == match.player_one else match.player_one
                loser.matches_lost += 1
                match.records_updated = True
            if status != "walkover" and not match.rating_updated:
                match.rating_before = {
                    match.player_one.player_id: match.player_one.elo_rating,
                    match.player_two.player_id: match.player_two.elo_rating,
                }
                EloSystem.update_score(match.player_one, match.player_two, winner)
                match.rating_updated = True
        else:
            match.completed_at = None
        match.manually_overridden = True
        if isinstance(self, rrt):
            self.recalculate_standings()
        self.record_change("set_match_status", "match", match_id, previous,
                           {"status": status, "winner_id": winner_id}, reason)

    def _match_by_id(self, match_id):
        match = next((item for item in self.matches if item.match_id == match_id), None)
        if match is None:
            raise ValueError(f"Unknown match ID: {match_id}")
        return match

    def to_dict(self):
        return {
            "tournament_id": self.tournament_id,
            "format": getattr(self, "tournament_format", "tournament"),
            "name": self.name,
            "created_at": self.created_at,
            "entrant_ids": [player.player_id for player in self.players],
            "matches": [match.to_dict() for match in self.matches],
            "finished": self.finished,
            "winner_id": self.winner.player_id if self.winner else None,
            "seeds": dict(self.seeds),
            "original_draw": copy.deepcopy(self.original_draw),
            "draw_metadata": copy.deepcopy(self.draw_metadata),
            "audit_log": copy.deepcopy(self.audit_log),
            "manually_overridden": self.manually_overridden,
            "automatic_progression_paused": self.automatic_progression_paused,
        }

class rrt(Tournament):
    tournament_format = "round_robin"

    def __init__ (self,name,players,game_config,tie_break_settings=None):
        super().__init__(name,players) #calls __init__ of tournament class
        self.game_config = game_config
        self.tie_break_settings = tie_break_settings or [
            "match_wins", "game_difference", "games_won"
        ]
        allowed_tie_breaks = {"match_wins", "game_difference", "games_won"}
        if (not isinstance(self.tie_break_settings, list)
                or not self.tie_break_settings
                or any(not isinstance(item, str) for item in self.tie_break_settings)
                or len(set(self.tie_break_settings)) != len(self.tie_break_settings)
                or any(item not in allowed_tie_breaks for item in self.tie_break_settings)):
            raise ValueError("Tie-break settings must be a unique ordered list of supported rules.")
        self.standings = self.create_standings()

    def generate_matches(self):
        existing_pairs = {
            frozenset((match.player_one.player_id, match.player_two.player_id))
            for match in self.matches
        }
        next_slot = max((match.slot_number or 0 for match in self.matches), default=0) + 1
        for i in range(len(self.players)):
            for j in range(i+1, len(self.players)):  #starting from i+1 to prevent duplicates
                player_one = self.players[i]
                player_two = self.players[j]
                pair = frozenset((player_one.player_id, player_two.player_id))
                if pair in existing_pairs:
                    continue

                match = Match(player_one=player_one,
                            player_two=player_two,
                            game_config=self.game_config,
                            )
                match._on_change = self._on_change
                match.round_number = 1
                match.slot_number = next_slot
                next_slot += 1
                self.matches.append(match)
                existing_pairs.add(pair)
        if self.original_draw is None:
            self.original_draw = {
                "entrants": [player.player_id for player in self.players],
                "matches": [match.to_dict() for match in self.matches],
            }
        
    def create_standings(self):
        standings = {}
        for player in self.players:
            standings[player.player_id] = {
                'player' : player,
                'wins' : 0,
                'losses' : 0,
                'games_won' : 0,
                'games_lost' : 0,
                'points_for': 0,
                'points_against': 0,
            }
        return standings

    def recalculate_standings(self):
        self.standings = self.create_standings()
        for match in self.matches:
            winner = match.match_winner
            if winner is None or not match.match_finished:
                continue
            loser = match.player_two if winner == match.player_one else match.player_one
            win_entry = self.standings.get(winner.player_id)
            lose_entry = self.standings.get(loser.player_id)
            if win_entry is None or lose_entry is None:
                continue
            win_entry["wins"] += 1
            lose_entry["losses"] += 1
            win_entry["games_won"] += match.games_won.get(winner.player_id, 0)
            win_entry["games_lost"] += match.games_won.get(loser.player_id, 0)
            lose_entry["games_won"] += match.games_won.get(loser.player_id, 0)
            lose_entry["games_lost"] += match.games_won.get(winner.player_id, 0)
            for game in match.games:
                for event in game.iter_valid_point_events():
                    scorer_id = event.get("player_id")
                    if scorer_id == winner.player_id:
                        win_entry["points_for"] += 1
                        lose_entry["points_against"] += 1
                    elif scorer_id == loser.player_id:
                        lose_entry["points_for"] += 1
                        win_entry["points_against"] += 1

    def run_tournament(self):
        if self.finished:
            return self.winner
        if self.automatic_progression_paused:
            raise RuntimeError("Automatic progression is paused; resume it before running the tournament.")
        if len(self.players) < 2:
            raise ValueError("A round-robin tournament needs at least two players.")
        if not self.matches:
            self.generate_matches()

        for match in self.matches:
            if match.status == "cancelled":
                active_ids = {player.player_id for player in self.players}
                if {match.player_one.player_id, match.player_two.player_id}.issubset(active_ids):
                    raise RuntimeError(
                        f"Cancelled match {match.match_id} still has two active entrants; "
                        "reschedule it or withdraw an entrant before completing the tournament."
                    )
                continue
            if match.status == "postponed":
                raise RuntimeError(
                    f"Match {match.match_id} is postponed; reschedule or cancel it before completing the tournament."
                )
            run_match(match)
            winner = match.match_winner
            if winner is None:
                raise ValueError(
                    "A tournament match ended without a winner; standings were not updated."
                )
            loser = match.player_two if winner == match.player_one else match.player_one

            self.standings[winner.player_id]['wins'] += 1
            self.standings[loser.player_id]['losses'] += 1

            self.standings[winner.player_id]["games_won"] += match.games_won[winner.player_id]
            self.standings[winner.player_id]["games_lost"] += match.games_won[loser.player_id]

            self.standings[loser.player_id]["games_won"] += match.games_won[loser.player_id]
            self.standings[loser.player_id]["games_lost"] += match.games_won[winner.player_id]
        
        self.recalculate_standings()
        self.finished = True
        self.winner = self.get_winner()
        if self._on_change is not None:
            self._on_change()


    def get_sorted_standings(self):
        def ranking_key(entry):
            values = {
                "match_wins": entry["wins"],
                "game_difference": entry["games_won"] - entry["games_lost"],
                "games_won": entry["games_won"],
            }
            return tuple(values[rule] for rule in self.tie_break_settings)
        return sorted(
            self.standings.values(),
            key=ranking_key,
            reverse=True #ensures descending order
        )

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "game_config": copy.deepcopy(self.game_config),
            "tie_break_settings": list(self.tie_break_settings),
            "standings": {
                player_id: {key: value for key, value in entry.items() if key != "player"}
                for player_id, entry in self.standings.items()
            },
        })
        return data

        
        
    def get_winner(self):
        sorted_standings = self.get_sorted_standings()
        if not sorted_standings:
            raise ValueError("A tournament with no players has no winner.")
        return sorted_standings[0]['player']
    def print_standings(self):
        print("\nSTANDINGS:   ")
        for index, entry in enumerate(self.get_sorted_standings(), start=1):
            player = entry['player']
            wins = entry['wins']
            losses = entry['losses']
            print(f"{index}. {player.name}- {wins}W / {losses}L")



class kot(Tournament):
    tournament_format = "knockout"

    def __init__(self,name,players,game_config):
        super().__init__(name,players)
        self.game_config = game_config
        self.current_players = players[:] #creates copy of the list
        self.round_number = 1

    def _materialize_planned_round(self, round_number):
        plans = [row for row in self.draw_metadata.get("match_plans", [])
                 if row.get("round") == round_number]
        if not plans:
            return None

        matches_by_id = {match.match_id: match for match in self.matches}
        byes_by_id = {
            row["match_id"]: row["player_id"]
            for row in self.draw_metadata.get("byes", [])
            if row.get("round") == round_number - 1
        }
        materialized = []
        entrant_ids = []
        for plan in sorted(plans, key=lambda row: row["slot"]):
            selected_players = []
            for source_id in plan["winner_of"]:
                source_match = matches_by_id.get(source_id)
                if source_match is not None:
                    if not source_match.match_finished or source_match.match_winner is None:
                        raise RuntimeError(
                            f"Knockout match {plan['match_id']} awaits the result of {source_id}."
                        )
                    player = source_match.match_winner
                else:
                    player_id = byes_by_id.get(source_id)
                    player = next((p for p in self.players if p.player_id == player_id), None)
                    if player is None:
                        raise ValueError(
                            f"Knockout plan {plan['match_id']} references an unknown or withdrawn bye."
                        )
                selected_players.append(player)
            if selected_players[0] == selected_players[1]:
                raise ValueError(
                    f"Knockout plan {plan['match_id']} resolves to the same player twice."
                )
            match = Match(selected_players[0], selected_players[1], self.game_config)
            match.match_id = plan["match_id"]
            match.round_number = round_number
            match.slot_number = plan["slot"]
            match.table_assignment = plan.get("table")
            match._on_change = self._on_change
            self.matches.append(match)
            materialized.append(match)
            entrant_ids.extend(player.player_id for player in selected_players)

        record = {
            "round": round_number,
            "entrant_ids": list(dict.fromkeys(entrant_ids)),
            "bye_player_id": None,
            "bye_player_ids": [],
            "bye_match_ids": [],
            "match_ids": [match.match_id for match in materialized],
            "completed": False,
        }
        return record, materialized

    def run_round(self):
        if self.automatic_progression_paused:
            raise RuntimeError("Automatic progression is paused; resume it or advance matches manually.")
        if len(self.current_players) < 2:
            raise ValueError("A knockout round needs at least two players.")

        print(f"\nRound: {self.round_number}")
        rounds = self.draw_metadata.setdefault("rounds", [])
        round_record = next(
            (row for row in rounds if row.get("round") == self.round_number), None
        )
        if round_record is not None and round_record.get("completed"):
            raise ValueError(f"Knockout round {self.round_number} is already complete.")
        if round_record is None:
            planned_round = self._materialize_planned_round(self.round_number)
            if planned_round is not None:
                round_record, round_matches = planned_round
            else:
                round_record = {
                    "round": self.round_number,
                    "entrant_ids": [player.player_id for player in self.current_players],
                    "bye_player_id": None,
                    "bye_player_ids": [],
                    "bye_match_ids": [],
                    "match_ids": [],
                    "completed": False,
                }
                remaining = list(self.current_players)
                if len(remaining) % 2 == 1:
                    bye_player = random.choice(remaining)
                    remaining.remove(bye_player)
                    round_record["bye_player_id"] = bye_player.player_id
                    round_record["bye_player_ids"].append(bye_player.player_id)
                    print(f"{bye_player.name.title()} gets a bye.")
                round_matches = []
                for index in range(0, len(remaining), 2):
                    match = Match(remaining[index], remaining[index + 1], self.game_config)
                    match._on_change = self._on_change
                    match.round_number = self.round_number
                    match.slot_number = index // 2 + 1
                    self.matches.append(match)
                    round_matches.append(match)
                    round_record["match_ids"].append(match.match_id)
            rounds.append(round_record)
            if self._on_change is not None:
                self._on_change()
        else:
            match_map = {match.match_id: match for match in self.matches}
            if any(match_id not in match_map for match_id in round_record.get("match_ids", [])):
                raise ValueError("Saved knockout round references a missing match.")
            round_matches = [match_map[match_id] for match_id in round_record["match_ids"]]

        winners = []
        bye_ids = round_record.get("bye_player_ids") or (
            [round_record["bye_player_id"]] if round_record.get("bye_player_id") else []
        )
        for bye_id in bye_ids:
            bye_player = next((player for player in self.players if player.player_id == bye_id), None)
            if bye_player is not None:
                winners.append(bye_player)

        for match in round_matches:
            if match.match_finished and match.match_winner is not None:
                winners.append(match.match_winner)
                continue
            if match.status in {"cancelled", "postponed"}:
                raise RuntimeError(
                    f"Match {match.match_id} is {match.status}; manually advance the round or reschedule it."
                )
            run_match(match)
            if match.match_winner is None:
                raise ValueError(
                    "A knockout match ended without a winner; the bracket cannot advance."
                )
            winners.append(match.match_winner)

        self.current_players = winners
        round_record["completed"] = True
        self.round_number += 1
        if self._on_change is not None:
            self._on_change()

    def advance_round_manually(self, winner_ids_by_match, reason):
        """Advance an interrupted knockout round from explicit organizer decisions."""
        self._require_reason(reason)
        rounds = self.draw_metadata.get("rounds", [])
        round_record = next(
            (row for row in rounds if row.get("round") == self.round_number), None
        )
        if round_record is None or round_record.get("completed"):
            raise ValueError("There is no incomplete knockout round to advance.")
        match_map = {match.match_id: match for match in self.matches}
        round_matches = []
        for match_id in round_record.get("match_ids", []):
            match = match_map.get(match_id)
            if match is None:
                raise ValueError(f"Saved knockout round references missing match {match_id!r}.")
            round_matches.append(match)
        if not isinstance(winner_ids_by_match, dict):
            raise ValueError("Provide a match-ID to winner-ID mapping for the round.")
        expected_ids = {match.match_id for match in round_matches}
        if set(winner_ids_by_match) != expected_ids:
            raise ValueError("Choose exactly one winner for every match in the incomplete round.")

        winners = []
        bye_ids = round_record.get("bye_player_ids") or (
            [round_record["bye_player_id"]] if round_record.get("bye_player_id") else []
        )
        for bye_id in bye_ids:
            bye_player = next((p for p in self.players if p.player_id == bye_id), None)
            if bye_player is not None:
                winners.append(bye_player)
        decisions = []
        for match in round_matches:
            winner_id = winner_ids_by_match[match.match_id]
            winner = next((p for p in (match.player_one, match.player_two)
                           if p.player_id == winner_id), None)
            if winner is None:
                raise ValueError(f"Winner for match {match.match_id} must be one of its players.")
            if not any(p.player_id == winner.player_id for p in self.players):
                raise ValueError("A withdrawn player cannot advance from the knockout round.")
            if match.match_finished and match.match_winner not in (None, winner):
                raise ValueError(
                    f"Match {match.match_id} already has another recorded winner; correct its result first."
                )
            if not match.match_finished or not match.records_updated:
                self.set_match_status(
                    match.match_id,
                    "walkover" if not match.match_finished else match.status,
                    reason,
                    winner_id=winner.player_id,
                )
            winners.append(winner)
            decisions.append({"match_id": match.match_id, "winner_id": winner.player_id})

        self.current_players = winners
        round_record["completed"] = True
        self.round_number += 1
        self.record_change(
            "advance_knockout_round", "round", round_record["round"], None,
            {"winners": [player.player_id for player in winners], "decisions": decisions}, reason,
        )
        if self._on_change is not None:
            self._on_change()
        return winners

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "game_config": copy.deepcopy(self.game_config),
            "current_player_ids": [player.player_id for player in self.current_players],
            "round_number": self.round_number,
        })
        return data


    def run(self):
        if self.automatic_progression_paused:
            raise RuntimeError("Automatic progression is paused; resume it or advance matches manually.")
        if not self.current_players:
            raise ValueError("A knockout tournament needs at least one player.")
        if len(self.current_players) == 1:
            incomplete = any(
                not row.get("completed") and row.get("round") == self.round_number
                for row in self.draw_metadata.get("rounds", [])
            )
            if incomplete:
                raise RuntimeError(
                    "An incomplete knockout round needs manual advancement before declaring a winner."
                )
            self.finished = True
            self.winner = self.current_players[0]
            if self._on_change is not None:
                self._on_change()
            return
        while len(self.current_players) > 1:
            
            self.run_round()
        self.finished = True
        self.winner = self.current_players[0]
        print(f"\nTournament Winner: {self.winner.name}")
        if self._on_change is not None:
            self._on_change()
       




class StatisticsService:
    @staticmethod
    def player_statistics(player_id, matches):
        stats = {
            "player_id": player_id,
            "matches_played": 0,
            "matches_won": 0,
            "matches_lost": 0,
            "games_won": 0,
            "games_lost": 0,
            "points_won": 0,
            "points_lost": 0,
            "points_on_serve_won": 0,
            "points_on_serve_played": 0,
            "points_return_won": 0,
            "points_return_played": 0,
            "deuce_games_played": 0,
            "deuce_games_won": 0,
            "opponents": {},
            "formats": {},
        }
        for match in matches:
            player_ids = (match.player_one.player_id, match.player_two.player_id)
            if player_id not in player_ids:
                continue
            opponent = match.player_two if match.player_one.player_id == player_id else match.player_one
            opponent_row = stats["opponents"].setdefault(opponent.player_id, {
                "name": opponent.name, "matches": 0, "wins": 0, "points_won": 0,
            })
            if match.match_finished and match.match_winner is not None:
                stats["matches_played"] += 1
                opponent_row["matches"] += 1
                if match.match_winner.player_id == player_id:
                    stats["matches_won"] += 1
                    opponent_row["wins"] += 1
                else:
                    stats["matches_lost"] += 1
            format_key = str(match.game_config.get("games_needed_to_win"))
            stats["formats"][format_key] = stats["formats"].get(format_key, 0) + 1

            match_games = list(match.games)
            if match.current_game is not None and match.current_game not in match_games:
                match_games.append(match.current_game)
            for game in match_games:
                if game.current_game_winner is not None:
                    if game.current_game_winner.player_id == player_id:
                        stats["games_won"] += 1
                    else:
                        stats["games_lost"] += 1
                score = {match.player_one.player_id: 0, match.player_two.player_id: 0}
                deuce_reached = False
                for event in game.iter_valid_point_events():
                    scorer_id = event.get("player_id")
                    if scorer_id not in score:
                        continue
                    score[scorer_id] += 1
                    if score[match.player_one.player_id] >= match.game_config["points_per_game"] - 1 and score[match.player_two.player_id] >= match.game_config["points_per_game"] - 1:
                        deuce_reached = True
                    if scorer_id == player_id:
                        stats["points_won"] += 1
                    else:
                        stats["points_lost"] += 1
                    server_id = event.get("server_id")
                    if server_id == player_id:
                        stats["points_on_serve_played"] += 1
                        if scorer_id == player_id:
                            stats["points_on_serve_won"] += 1
                    elif server_id in player_ids:
                        stats["points_return_played"] += 1
                        if scorer_id == player_id:
                            stats["points_return_won"] += 1
                if deuce_reached:
                    stats["deuce_games_played"] += 1
                    if game.current_game_winner is not None and game.current_game_winner.player_id == player_id:
                        stats["deuce_games_won"] += 1
                opponent_row["points_won"] += sum(
                    1 for event in game.iter_valid_point_events()
                    if event.get("player_id") == player_id
                )

        total_points = stats["points_won"] + stats["points_lost"]
        stats["point_sample_size"] = total_points
        stats["point_win_rate"] = (
            stats["points_won"] / total_points if total_points else None
        )
        stats["serve_point_win_rate"] = (
            stats["points_on_serve_won"] / stats["points_on_serve_played"]
            if stats["points_on_serve_played"] else None
        )
        stats["return_point_win_rate"] = (
            stats["points_return_won"] / stats["points_return_played"]
            if stats["points_return_played"] else None
        )
        stats["match_win_rate"] = (
            stats["matches_won"] / stats["matches_played"]
            if stats["matches_played"] else None
        )
        return stats


class TournamentDrawService:
    """Validate and preview documented JSON or CSV draw files without mutation."""

    @staticmethod
    def sample_json_template():
        return {
            "schema_version": 1,
            "tournament": {
                "name": "Example Open",
                "format": "knockout",
                "game_config": {
                    "points_per_game": 11,
                    "deuce_enabled": True,
                    "golden_point_enabled": False,
                    "games_needed_to_win": 1,
                },
            },
            "entrants": [
                {"participant_id": "seed-1", "player_id": "EXISTING_PLAYER_ID", "seed": 1},
                {"participant_id": "seed-2", "player_id": "ANOTHER_PLAYER_ID", "seed": 2},
                {"participant_id": "seed-3", "player_id": "THIRD_PLAYER_ID", "seed": 3},
                {"participant_id": "seed-4", "player_id": "FOURTH_PLAYER_ID", "seed": 4},
            ],
            "matches": [
                {"match_id": "semi-1", "round": 1, "slot": 1,
                 "player_one": "seed-1", "player_two": "seed-4", "table": "Table 1"},
                {"match_id": "semi-2", "round": 1, "slot": 2,
                 "player_one": "seed-2", "player_two": "seed-3", "table": "Table 2"},
                {"match_id": "final", "round": 2, "slot": 1,
                 "winner_of": ["semi-1", "semi-2"], "table": "Table 1"},
            ],
        }

    @classmethod
    def preview_json(cls, source, players, player_mapping=None):
        try:
            players_by_id = (
                dict(players) if isinstance(players, dict)
                else {player.player_id: player for player in players}
            )
        except (TypeError, AttributeError):
            return {"valid": False, "errors": ["players must be a collection of player records."], "warnings": []}
        if any(
            not isinstance(player_id, str) or not player_id
            or not isinstance(getattr(player, "name", None), str)
            for player_id, player in players_by_id.items()
        ):
            return {"valid": False, "errors": ["players contains an invalid ID or player record."], "warnings": []}
        if isinstance(source, str):
            try:
                source = json.loads(source)
            except json.JSONDecodeError as error:
                return {"valid": False, "errors": [f"Invalid JSON: {error}"], "warnings": []}
        errors = []
        warnings = []
        mapping = player_mapping or {}
        if not isinstance(mapping, dict):
            return {"valid": False, "errors": ["player_mapping must be an object."], "warnings": []}
        if not isinstance(source, dict):
            return {"valid": False, "errors": ["Draw must be a JSON object."], "warnings": []}
        if (source.get("schema_version") != 1
                or isinstance(source.get("schema_version"), bool)):
            errors.append("schema_version must be 1.")
        details = source.get("tournament")
        if not isinstance(details, dict):
            details = {}
            errors.append("tournament must be an object.")
        format_name = details.get("format")
        if format_name not in ("round_robin", "knockout"):
            errors.append("tournament.format must be 'round_robin' or 'knockout'.")
        tournament_name = details.get("name", "Unnamed tournament")
        if not isinstance(tournament_name, str) or not tournament_name.strip():
            errors.append("tournament.name must be a non-empty string.")
        entrant_rows = source.get("entrants")
        if not isinstance(entrant_rows, list) or not entrant_rows:
            entrant_rows = []
            errors.append("entrants must be a non-empty list.")
        by_name = {}
        for player in players_by_id.values():
            by_name.setdefault(player.name.casefold(), []).append(player)
        resolved = {}
        normalized_entrants = []
        player_ids = set()
        seeds = set()
        for index, row in enumerate(entrant_rows, start=1):
            if not isinstance(row, dict):
                errors.append(f"Entrant {index} must be an object.")
                continue
            participant_id = row.get("participant_id")
            if not isinstance(participant_id, str) or not participant_id:
                errors.append(f"Entrant {index} needs a non-empty participant_id.")
                continue
            if participant_id in resolved:
                errors.append(f"Duplicate participant_id {participant_id!r}.")
                continue
            player_id = row.get("player_id")
            mapped_player_id = mapping.get(participant_id)
            if mapped_player_id is None and isinstance(row.get("name"), str):
                mapped_player_id = mapping.get(row["name"])
            if mapped_player_id is not None:
                if not isinstance(mapped_player_id, str):
                    errors.append(f"Player mapping for {participant_id!r} must be a player ID string.")
                    continue
                player_id = mapped_player_id
            player = players_by_id.get(player_id) if isinstance(player_id, str) else None
            if player is None and isinstance(row.get("name"), str):
                candidates = by_name.get(row["name"].casefold(), [])
                if len(candidates) == 1:
                    player = candidates[0]
                elif len(candidates) > 1:
                    errors.append(f"Ambiguous player name {row['name']!r}; provide player_id.")
                else:
                    errors.append(f"Unknown player name {row['name']!r}.")
            if player is None:
                errors.append(f"Entrant {participant_id!r} does not map to an existing player.")
                continue
            if player.player_id in player_ids:
                errors.append(f"Player {player.name!r} appears more than once in entrants.")
            player_ids.add(player.player_id)
            seed = row.get("seed")
            if seed is not None:
                if not isinstance(seed, int) or isinstance(seed, bool) or seed < 1:
                    errors.append(f"Seed for {participant_id!r} must be a positive integer.")
                elif seed in seeds:
                    errors.append(f"Duplicate seed value {seed}.")
                else:
                    seeds.add(seed)
            resolved[participant_id] = player
            normalized_entrants.append({
                "participant_id": participant_id,
                "player_id": player.player_id,
                "seed": seed,
            })
        if len(normalized_entrants) < 2:
            errors.append("A tournament draw needs at least two resolved entrants.")
        if len(normalized_entrants) >= 2 and isinstance(details.get("game_config"), dict):
            try:
                Match(players_by_id[normalized_entrants[0]["player_id"]],
                      players_by_id[normalized_entrants[1]["player_id"]],
                      details["game_config"])
            except (KeyError, TypeError, ValueError) as error:
                errors.append(f"Invalid game_config: {error}")
        elif not isinstance(details.get("game_config"), dict):
            errors.append("tournament.game_config must be an object.")
        if format_name == "round_robin":
            tie_rules = details.get("tie_break_settings", [
                "match_wins", "game_difference", "games_won"
            ])
            supported = {"match_wins", "game_difference", "games_won"}
            if (not isinstance(tie_rules, list) or not tie_rules
                    or any(not isinstance(rule, str) for rule in tie_rules)
                    or len(set(tie_rules)) != len(tie_rules)
                    or any(rule not in supported for rule in tie_rules)):
                errors.append("Invalid round-robin tie_break_settings.")

        matches = source.get("matches", [])
        if not isinstance(matches, list):
            errors.append("matches must be a list.")
            matches = []
        match_ids = set()
        match_positions = set()
        pairs_seen = set()
        knockout_round_players = {}
        normalized_matches = []
        normalized_byes = []
        source_round_by_id = {}
        for source_index, source_row in enumerate(matches, start=1):
            if not isinstance(source_row, dict):
                continue
            source_id = source_row.get("match_id") or f"imported-match-{source_index}"
            if isinstance(source_id, str):
                source_round_by_id[source_id] = source_row.get("round", 1)
        used_knockout_sources = {}
        for index, row in enumerate(matches, start=1):
            if not isinstance(row, dict):
                errors.append(f"Match {index} must be an object.")
                continue
            match_id = row.get("match_id") or f"imported-match-{index}"
            if not isinstance(match_id, str) or match_id in match_ids:
                errors.append(f"Match {index} has a missing or duplicate match_id.")
                continue
            match_ids.add(match_id)
            p1_ref, p2_ref = row.get("player_one"), row.get("player_two")
            bye_ref = row.get("bye_player")
            round_no, slot_no = row.get("round", 1), row.get("slot", index)
            if any(not isinstance(value, int) or isinstance(value, bool) or value < 1
                   for value in (round_no, slot_no)):
                errors.append(f"Match {match_id!r} has an invalid round or slot.")
                continue
            position = (round_no, slot_no)
            if position in match_positions:
                errors.append(f"Multiple matches/byes use round {round_no}, slot {slot_no}.")
            match_positions.add(position)
            if (format_name == "knockout" and isinstance(bye_ref, str)
                    and bye_ref in resolved):
                if round_no != 1:
                    errors.append(
                        "Imported byes must be in round 1; later-round entrants must use winner_of references."
                    )
                round_players = knockout_round_players.setdefault(round_no, set())
                if bye_ref in round_players:
                    errors.append(
                        f"Knockout participant {bye_ref!r} appears more than once in round {round_no}."
                    )
                round_players.add(bye_ref)
                normalized_byes.append({
                    "match_id": match_id,
                    "player_id": resolved[bye_ref].player_id,
                    "round": round_no,
                    "slot": slot_no,
                })
                continue
            winner_of = row.get("winner_of")
            if format_name == "knockout" and winner_of is not None:
                if (not isinstance(winner_of, list) or len(winner_of) != 2
                        or any(not isinstance(source_id, str) or not source_id
                               for source_id in winner_of)
                        or len(set(winner_of)) != 2):
                    errors.append(f"Knockout match {match_id!r} needs two distinct winner_of match IDs.")
                    continue
                if round_no < 2:
                    errors.append(f"Knockout match {match_id!r} cannot use winner_of in round 1.")
                    continue
                for source_id in winner_of:
                    source_round = source_round_by_id.get(source_id)
                    if source_round != round_no - 1:
                        errors.append(
                            f"Knockout match {match_id!r} must reference matches/byes from round {round_no - 1}."
                        )
                    used = used_knockout_sources.setdefault(round_no, set())
                    if source_id in used:
                        errors.append(f"Knockout source {source_id!r} advances more than once in round {round_no}.")
                    used.add(source_id)
                normalized_matches.append({
                    "match_id": match_id,
                    "winner_of": list(winner_of),
                    "round": round_no,
                    "slot": slot_no,
                    "table": row.get("table"),
                })
                continue
            if not isinstance(p1_ref, str) or not isinstance(p2_ref, str):
                errors.append(f"Match {match_id!r} participant references must be strings.")
                continue
            if p1_ref not in resolved or p2_ref not in resolved:
                errors.append(f"Match {match_id!r} references an unknown participant.")
                continue
            if p1_ref == p2_ref:
                errors.append(f"Match {match_id!r} assigns a player against themselves.")
                continue
            if format_name == "knockout":
                if round_no > 1:
                    errors.append(
                        f"Knockout match {match_id!r} in a later round must use winner_of references, not entrant IDs."
                    )
                round_players = knockout_round_players.setdefault(round_no, set())
                repeated = {p1_ref, p2_ref}.intersection(round_players)
                if repeated:
                    errors.append(
                        f"Knockout participant(s) {', '.join(sorted(repeated))} appear more than once in round {round_no}."
                    )
                round_players.update((p1_ref, p2_ref))
            pair = frozenset((p1_ref, p2_ref))
            if pair in pairs_seen:
                errors.append(f"Duplicate fixture for participants {p1_ref!r} and {p2_ref!r}.")
            pairs_seen.add(pair)
            normalized_matches.append({
                "match_id": match_id,
                "player_one_id": resolved[p1_ref].player_id,
                "player_two_id": resolved[p2_ref].player_id,
                "round": round_no,
                "slot": slot_no,
                "table": row.get("table"),
            })
        if not normalized_matches:
            warnings.append("The draw contains no playable matches.")
        if format_name == "knockout" and (normalized_matches or normalized_byes):
            first_round = min(
                [row["round"] for row in normalized_matches + normalized_byes]
            )
            first_round_players = knockout_round_players.get(first_round, set())
            if first_round_players != set(resolved):
                errors.append(
                    "The first imported knockout round must assign every entrant exactly once, either to a match or a bye."
                )
            for round_no, used_sources in used_knockout_sources.items():
                expected_sources = {
                    source_id for source_id, source_round in source_round_by_id.items()
                    if source_round == round_no - 1
                }
                if expected_sources != used_sources:
                    errors.append(
                        f"Knockout round {round_no} must advance every prior-round match and bye exactly once."
                    )
        if format_name == "round_robin" and len(normalized_entrants) >= 2:
            expected = len(normalized_entrants) * (len(normalized_entrants) - 1) // 2
            if len(pairs_seen) < expected:
                warnings.append(
                    f"Round-robin draw has {len(pairs_seen)} fixtures; a complete all-play-all draw has {expected}."
                )
        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "tournament": copy.deepcopy(details),
            "entrants": normalized_entrants,
            "matches": normalized_matches,
            "byes": normalized_byes,
            "raw": copy.deepcopy(source),
        }

    @classmethod
    def preview_csv(cls, csv_text, players, name, format_name, game_config,
                    tie_break_settings=None, player_mapping=None):
        players_by_id = (
            players if isinstance(players, dict)
            else {player.player_id: player for player in players}
        )
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            fieldnames = reader.fieldnames or []
            rows = list(reader)
        except (csv.Error, TypeError) as error:
            return {"valid": False, "errors": [f"Invalid CSV: {error}"], "warnings": []}
        required = {"player_one_id", "player_two_id", "round", "slot"}
        mapping = player_mapping or {}
        if not isinstance(mapping, dict):
            return {"valid": False, "errors": ["player_mapping must be an object."], "warnings": []}
        if not rows:
            return {"valid": False, "errors": ["CSV contains no match rows."], "warnings": []}
        if (any(not isinstance(header, str) or not header.strip() for header in fieldnames)
                or len(fieldnames) != len(set(fieldnames))):
            return {"valid": False, "errors": ["CSV headers must be non-empty and unique."], "warnings": []}
        headers = set(fieldnames)
        if not required.issubset(headers):
            return {"valid": False, "errors": [
                f"CSV needs columns: {', '.join(sorted(required))}."
            ], "warnings": []}
        entrants = []
        seen = set()
        matches = []
        for index, row in enumerate(rows, start=1):
            if None in row:
                return {"valid": False, "errors": [f"CSV row {index} has more values than headers."], "warnings": []}
            mapped_ids = {}
            for column in ("player_one_id", "player_two_id"):
                imported_id = row[column]
                if not isinstance(imported_id, str) or not imported_id.strip():
                    return {"valid": False, "errors": [f"CSV row {index} has a blank {column}."], "warnings": []}
                player_id = mapping.get(imported_id, imported_id)
                if not isinstance(player_id, str):
                    return {"valid": False, "errors": [f"Mapping for CSV ID {imported_id!r} must be a player ID string."], "warnings": []}
                if player_id not in players_by_id:
                    return {"valid": False, "errors": [f"CSV row {index} has unknown player ID {imported_id!r}; map it to an existing player ID."], "warnings": []}
                mapped_ids[column] = player_id
                if player_id not in seen:
                    seen.add(player_id)
                    entrants.append({"participant_id": player_id, "player_id": player_id})
            matches.append({
                "match_id": row.get("match_id") or f"csv-match-{index}",
                "round": row["round"],
                "slot": row["slot"],
                "player_one": mapped_ids["player_one_id"],
                "player_two": mapped_ids["player_two_id"],
                "table": row.get("table_assignment"),
            })
        try:
            for row in matches:
                row["round"] = int(row["round"])
                row["slot"] = int(row["slot"])
        except (TypeError, ValueError):
            return {"valid": False, "errors": ["CSV round and slot values must be positive integers."], "warnings": []}
        payload = {
            "schema_version": 1,
            "tournament": {
                "name": name,
                "format": format_name,
                "game_config": game_config,
                "tie_break_settings": tie_break_settings or [
                    "match_wins", "game_difference", "games_won"
                ],
            },
            "entrants": entrants,
            "matches": matches,
        }
        return cls.preview_json(payload, players, player_mapping=player_mapping)

    @staticmethod
    def apply_preview(preview, players, confirmed=False, reason="Confirmed draw import"):
        players_by_id = (
            players if isinstance(players, dict)
            else {player.player_id: player for player in players}
        )
        if not confirmed:
            raise ValueError("Draw import requires explicit confirmation.")
        if not preview.get("valid"):
            raise ValueError("Cannot import an invalid draw: " + "; ".join(preview.get("errors", [])))
        details = preview["tournament"]
        entrants = [players_by_id[row["player_id"]] for row in preview["entrants"]]
        if details["format"] == "round_robin":
            tournament = rrt(
                details.get("name", "Imported tournament"), entrants,
                details["game_config"],
                tie_break_settings=details.get("tie_break_settings"),
            )
        else:
            tournament = kot(details.get("name", "Imported tournament"),
                             entrants, details["game_config"])
        for row in preview["entrants"]:
            tournament.seeds[row["player_id"]] = row.get("seed")
        tournament.matches = []
        concrete_matches = [
            row for row in preview["matches"] if "winner_of" not in row
        ] if isinstance(tournament, kot) else preview["matches"]
        for row in concrete_matches:
            match = Match(players_by_id[row["player_one_id"]], players_by_id[row["player_two_id"]],
                          details["game_config"])
            match.match_id = row["match_id"]
            match.round_number = row["round"]
            match.slot_number = row["slot"]
            match.table_assignment = row.get("table")
            tournament.matches.append(match)
        tournament.original_draw = copy.deepcopy(preview["raw"])
        tournament.draw_metadata = {
            "imported": True,
            "imported_at": utc_now_iso(),
            "warnings": list(preview.get("warnings", [])),
        }
        if isinstance(tournament, kot):
            round_rows = {}
            for row in concrete_matches:
                entry = round_rows.setdefault(row["round"], {
                    "round": row["round"], "entrant_ids": [],
                    "bye_player_id": None, "bye_player_ids": [],
                    "bye_match_ids": [], "match_ids": [], "completed": False,
                })
                entry["match_ids"].append(row["match_id"])
                for player_id in (row["player_one_id"], row["player_two_id"]):
                    if player_id not in entry["entrant_ids"]:
                        entry["entrant_ids"].append(player_id)
            for bye in preview.get("byes", []):
                entry = round_rows.setdefault(bye["round"], {
                    "round": bye["round"], "entrant_ids": [],
                    "bye_player_id": None, "bye_player_ids": [],
                    "bye_match_ids": [], "match_ids": [], "completed": False,
                })
                if entry["bye_player_id"] is None:
                    entry["bye_player_id"] = bye["player_id"]
                entry["bye_player_ids"].append(bye["player_id"])
                entry["bye_match_ids"].append(bye["match_id"])
                if bye["player_id"] not in entry["entrant_ids"]:
                    entry["entrant_ids"].append(bye["player_id"])
            tournament.draw_metadata["rounds"] = [round_rows[key] for key in sorted(round_rows)]
            tournament.draw_metadata["byes"] = copy.deepcopy(preview.get("byes", []))
            tournament.draw_metadata["match_plans"] = [
                copy.deepcopy(row) for row in preview["matches"]
                if "winner_of" in row
            ]
        tournament.record_change("import_draw", "tournament", tournament.tournament_id,
                                 None, tournament.original_draw, reason)
        return tournament


def export_tournament_package(tournament, output_directory):
    output_root = Path(output_directory)
    output_root.mkdir(parents=True, exist_ok=True)
    export_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    final_package_dir = output_root / f"tournament_{tournament.tournament_id}_{export_stamp}"
    package_dir = Path(tempfile.mkdtemp(prefix=".tournament_export_", dir=output_root))

    payload = {
        "schema_version": STATE_SCHEMA_VERSION,
        "exported_at": utc_now_iso(),
        "time_zone": "UTC; timestamps are ISO-8601",
        "derived_fields": ["standings", "player statistics"],
        "unavailable_fields": [
            "fields that were never recorded remain null or absent; no values are inferred"
        ],
        **tournament.to_dict(),
    }
    payload["player_statistics"] = {
        player.player_id: StatisticsService.player_statistics(
            player.player_id, tournament.matches
        )
        for player in tournament.players
    }
    json_path = package_dir / "tournament.json"
    atomic_write_json(json_path, payload)

    match_buffer = io.StringIO(newline="")
    match_fields = [
        "match_id", "round", "slot", "table", "status", "player_one_id",
        "player_one_name", "player_two_id", "player_two_name", "winner_id",
        "games_won_player_one", "games_won_player_two", "current_score_player_one",
        "current_score_player_two", "game_scores",
    ]
    writer = csv.DictWriter(match_buffer, fieldnames=match_fields)
    writer.writeheader()
    for match in tournament.matches:
        current_score = match.current_game.current_game_score if match.current_game else {}
        writer.writerow({
            "match_id": match.match_id,
            "round": match.round_number,
            "slot": match.slot_number,
            "table": match.table_assignment,
            "status": match.status,
            "player_one_id": match.player_one.player_id,
            "player_one_name": match.player_one.name,
            "player_two_id": match.player_two.player_id,
            "player_two_name": match.player_two.name,
            "winner_id": match.match_winner.player_id if match.match_winner else None,
            "games_won_player_one": match.games_won.get(match.player_one.player_id, 0),
            "games_won_player_two": match.games_won.get(match.player_two.player_id, 0),
            "current_score_player_one": current_score.get(match.player_one.player_id),
            "current_score_player_two": current_score.get(match.player_two.player_id),
            "game_scores": " | ".join(
                f"{game.current_game_score.get(match.player_one.player_id, 0)}-"
                f"{game.current_game_score.get(match.player_two.player_id, 0)}"
                for game in match.games
            ),
        })
    matches_csv_path = package_dir / "matches.csv"
    atomic_write_text(matches_csv_path, match_buffer.getvalue())

    event_buffer = io.StringIO(newline="")
    event_writer = csv.DictWriter(
        event_buffer,
        fieldnames=["match_id", "game_id", "event_id", "timestamp", "type", "player_id", "server_id", "event_json"],
    )
    event_writer.writeheader()
    for match in tournament.matches:
        games = match.games + ([match.current_game] if match.current_game else [])
        for game in games:
            for event in game.events:
                event_writer.writerow({
                    "match_id": match.match_id,
                    "game_id": game.game_id,
                    "event_id": event.get("event_id"),
                    "timestamp": event.get("timestamp"),
                    "type": event.get("type"),
                    "player_id": event.get("player_id", event.get("undone_player_id")),
                    "server_id": event.get("server_id"),
                    "event_json": json.dumps(event, ensure_ascii=False, sort_keys=True),
                })
    events_csv_path = package_dir / "events.csv"
    atomic_write_text(events_csv_path, event_buffer.getvalue())

    statistics_fields = [
        "player_id", "matches_played", "matches_won", "matches_lost",
        "games_won", "games_lost", "points_won", "points_lost",
        "points_on_serve_won", "points_on_serve_played", "points_return_won",
        "points_return_played", "deuce_games_played", "deuce_games_won",
        "point_sample_size", "point_win_rate", "serve_point_win_rate",
        "return_point_win_rate", "match_win_rate",
    ]
    statistics_buffer = io.StringIO(newline="")
    statistics_writer = csv.DictWriter(statistics_buffer, fieldnames=statistics_fields)
    statistics_writer.writeheader()
    for player in tournament.players:
        stats = StatisticsService.player_statistics(player.player_id, tournament.matches)
        statistics_writer.writerow({key: stats.get(key) for key in statistics_fields})
    statistics_csv_path = package_dir / "player_statistics.csv"
    atomic_write_text(statistics_csv_path, statistics_buffer.getvalue())

    standings_path = package_dir / "standings.csv"
    standings_buffer = io.StringIO(newline="")
    if isinstance(tournament, rrt):
        rows = tournament.get_sorted_standings()
        fields = ["place", "player_id", "player_name", "wins", "losses", "games_won", "games_lost", "game_difference", "points_for", "points_against"]
        standings_writer = csv.DictWriter(standings_buffer, fieldnames=fields)
        standings_writer.writeheader()
        for place, row in enumerate(rows, start=1):
            standings_writer.writerow({
                "place": place,
                "player_id": row["player"].player_id,
                "player_name": row["player"].name,
                "wins": row["wins"],
                "losses": row["losses"],
                "games_won": row["games_won"],
                "games_lost": row["games_lost"],
                "game_difference": row["games_won"] - row["games_lost"],
                "points_for": row.get("points_for", 0),
                "points_against": row.get("points_against", 0),
            })
    else:
        standings_buffer.write("Standings are not applicable to knockout tournaments.\n")
    atomic_write_text(standings_path, standings_buffer.getvalue())

    manifest_path = package_dir / "README.txt"
    manifest = (
        "Table Tennis Tournament Package\n"
        f"Tournament ID: {tournament.tournament_id}\n"
        f"schema_version: {STATE_SCHEMA_VERSION}\n"
        "Timestamps use ISO-8601 UTC. IDs are stable identifiers; names are display labels.\n"
        "tournament.json is the complete machine-readable source, including partial matches, events, audit log, draw metadata, and available settings.\n"
        "matches.csv, events.csv, and player_statistics.csv are spreadsheet-friendly summaries; tournament.json retains full fidelity.\n"
        "standings.csv is derived from currently recorded completed match results. Missing values are left blank.\n"
    )
    atomic_write_text(manifest_path, manifest)
    os.replace(package_dir, final_package_dir)
    package_dir = final_package_dir
    return {
        "directory": str(package_dir),
        "json": str(package_dir / "tournament.json"),
        "matches_csv": str(package_dir / "matches.csv"),
        "events_csv": str(package_dir / "events.csv"),
        "statistics_csv": str(package_dir / "player_statistics.csv"),
        "standings_csv": str(package_dir / "standings.csv"),
        "manifest": str(package_dir / "README.txt"),
    }


def atomic_write_text(filename, content):
    target = Path(filename)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=target.parent,
            delete=False
        ) as temp_file:
            temp_name = temp_file.name
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, target)
    except Exception:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)
        raise


def tournament_from_dict(data, players):
    if not isinstance(data, dict):
        raise ValueError("Tournament record must be an object.")
    format_name = data.get("format")
    entrants = []
    for player_id in data.get("entrant_ids", []):
        player = players.get(player_id)
        if player is None:
            raise ValueError(f"Tournament references unknown entrant {player_id!r}.")
        entrants.append(player)

    game_config = data.get("game_config")
    if format_name == "round_robin":
        tournament = rrt(
            data.get("name", "Unnamed tournament"), entrants, game_config,
            tie_break_settings=data.get("tie_break_settings"),
        )
    elif format_name == "knockout":
        tournament = kot(data.get("name", "Unnamed tournament"), entrants, game_config)
    else:
        raise ValueError(f"Unsupported tournament format: {format_name!r}")

    tournament.tournament_id = data.get("tournament_id") or str(uuid.uuid4())
    tournament.created_at = data.get("created_at", utc_now_iso())
    tournament.matches = [Match.from_dict(item, players) for item in data.get("matches", [])]
    tournament.finished = bool(data.get("finished", False))
    winner_id = data.get("winner_id")
    tournament.winner = players.get(winner_id) if winner_id else None
    if winner_id and tournament.winner is None:
        raise ValueError(f"Tournament references unknown winner {winner_id!r}.")
    seeds = data.get("seeds", {})
    entrant_ids = {player.player_id for player in entrants}
    if not isinstance(seeds, dict) or any(player_id not in entrant_ids for player_id in seeds):
        raise ValueError("Tournament seeds contain an unknown entrant.")
    tournament.seeds = dict(seeds)
    tournament.original_draw = copy.deepcopy(data.get("original_draw"))
    tournament.draw_metadata = copy.deepcopy(data.get("draw_metadata", {}))
    tournament.audit_log = copy.deepcopy(data.get("audit_log", []))
    tournament.manually_overridden = bool(data.get("manually_overridden", False))
    tournament.automatic_progression_paused = bool(
        data.get("automatic_progression_paused", False)
    )
    

    if isinstance(tournament, rrt):
        tournament.recalculate_standings()
    else:
        current_ids = data.get("current_player_ids", data.get("entrant_ids", []))
        tournament.current_players = []
        for player_id in current_ids:
            player = players.get(player_id)
            if player is None:
                raise ValueError(f"Knockout state references unknown player {player_id!r}.")
            tournament.current_players.append(player)
        tournament.round_number = data.get("round_number", 1)
    return tournament


'''if __name__ == "__main__":
    p1 = Player("A", "shakehand", "right", "attacker")
    p2 = Player("B", "penhold", "left", "defender")

    config = create_basic_game_config()
    match = Match(p1,p2,config)
    game = Game(p1, p2, config, save_results=True)
    game.add_point(p1)
    game.add_point(p2)
    game.add_point(p1)

    game.undo_last_point("Net serve")

    game.undo_last_point( "Illegal serve")
    game.undo_last_point( "Illegal serve")
    game.undo_last_point( "Illegal serve")  # should give p1 a point

    print(game.current_game_score)
    print(game.events)'''


def _choose_player(players, prompt="Select player number: "):
    player_list = list(players.values())
    if not player_list:
        raise ValueError("No players are available. Add players first.")
    for index, player in enumerate(player_list, start=1):
        print(f"{index}. {player.name} ({player.player_id})")
    choice = input(prompt).strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(player_list):
        raise ValueError("Choose a listed player number.")
    return player_list[int(choice) - 1]


def _choose_players(players):
    player_list = list(players.values())
    if len(player_list) < 2:
        raise ValueError("At least two players are required.")
    for index, player in enumerate(player_list, start=1):
        print(f"{index}. {player.name} ({player.player_id})")
    choices = input("Enter player numbers separated by commas: ").split(",")
    try:
        indexes = [int(value.strip()) - 1 for value in choices]
    except ValueError as error:
        raise ValueError("Enter numeric player positions separated by commas.") from error
    if len(indexes) < 2 or any(index < 0 or index >= len(player_list) for index in indexes):
        raise ValueError("Select at least two listed players.")
    selected = [player_list[index] for index in indexes]
    if len({player.player_id for player in selected}) != len(selected):
        raise ValueError("Do not select the same player more than once.")
    return selected


def _choose_game_config():
    choice = input("Game rules: (1) Basic 11-point single game, (2) Advanced: ").strip()
    if choice == "1":
        return create_basic_game_config()
    if choice == "2":
        return create_advanced_game_config()
    raise ValueError("Choose 1 or 2.")


def _choose_tournament(tournaments):
    if not tournaments:
        raise ValueError("No tournaments are saved.")
    for index, tournament in enumerate(tournaments, start=1):
        print(f"{index}. {tournament.name} [{tournament.tournament_id}] — {tournament.__class__.__name__}")
    value = input("Select tournament number: ").strip()
    if not value.isdigit() or not 1 <= int(value) <= len(tournaments):
        raise ValueError("Choose a listed tournament number.")
    return tournaments[int(value) - 1]


def main():
    storage = StorageManager()
    try:
        players, tournaments, matches = storage.load_state()
    except ValueError as error:
        print(f"Could not load saved state: {error}")
        return
    save_state = storage.attach_autosave(players, tournaments, matches)

    while True:
        print("\nTABLE TENNIS MANAGER")
        print("1. List players")
        print("2. Add player")
        print("3. Create and play a match")
        print("4. Resume a saved match")
        print("5. Create tournament")
        print("6. Run or resume tournament")
        print("7. Edit tournament match/result")
        print("8. Import a JSON or CSV draw")
        print("9. Export tournament package")
        print("10. View player statistics")
        print("11. View tournament standings or bracket")
        print("12. Restore a timestamped state backup")
        print("13. Save and quit")
        choice = input("Choose an action: ").strip()
        try:
            if choice == "1":
                if not players:
                    print("No players saved.")
                for player in players.values():
                    display_player_profile(player)
            elif choice == "2":
                name = input("Player name: ").strip()
                grip = input("Grip (shakehand/penhold): ").strip().lower()
                hand = input("Playing hand (right/left): ").strip().lower()
                style = input("Play style: ").strip().lower()
                player = add_player(players, name, grip, hand, style)
                if player is not None:
                    save_state()
            elif choice == "3":
                player_one = _choose_player(players, "Player 1 number: ")
                player_two = _choose_player(players, "Player 2 number: ")
                if player_one.player_id == player_two.player_id:
                    raise ValueError("A player cannot play against themselves.")
                match = Match(player_one, player_two, _choose_game_config())
                matches.append(match)
                match._on_change = save_state
                save_state()
                run_match(match)
            elif choice == "4":
                pending = [match for match in matches if not match.match_finished]
                if not pending:
                    raise ValueError("There are no unfinished saved matches.")
                for index, pending_match in enumerate(pending, start=1):
                    print(f"{index}. {pending_match.match_id}: {pending_match.player_one.name} vs {pending_match.player_two.name} [{pending_match.status}]")
                match_index = 0 if len(pending) == 1 else int(input("Select match number: ").strip()) - 1
                if not 0 <= match_index < len(pending):
                    raise ValueError("Choose a listed match number.")
                match = pending[match_index]
                match._on_change = save_state
                run_match(match)
            elif choice == "5":
                name = input("Tournament name: ").strip()
                format_choice = input("Format: (1) Round robin (2) Knockout: ").strip()
                entrants = _choose_players(players)
                config = _choose_game_config()
                if format_choice == "1":
                    tie_breaks = input(
                        "Tie-break order (match_wins,game_difference,games_won) [Enter for default]: "
                    ).strip()
                    rules = [item.strip() for item in tie_breaks.split(",") if item.strip()] if tie_breaks else None
                    tournament = rrt(name, entrants, config, tie_break_settings=rules)
                    tournaments.append(tournament)
                    tournament.generate_matches()
                elif format_choice == "2":
                    tournament = kot(name, entrants, config)
                    tournaments.append(tournament)
                else:
                    raise ValueError("Choose round robin (1) or knockout (2).")
                save_state = storage.attach_autosave(players, tournaments, matches)
                save_state()
            elif choice == "6":
                tournament = _choose_tournament(tournaments)
                save_state = storage.attach_autosave(players, tournaments, matches)
                if isinstance(tournament, rrt):
                    tournament.run_tournament()
                elif isinstance(tournament, kot):
                    tournament.run()
            elif choice == "7":
                tournament = _choose_tournament(tournaments)
                action = input(
                    "Action: (1) Reschedule (2) Postpone (3) Cancel (4) Reopen "
                    "(5) Correct winner (6) Pause progression (7) Resume progression "
                    "(8) Manually advance knockout round (9) View audit history "
                    "(10) Walkover (11) Retirement (12) Add entrant (13) Withdraw entrant "
                    "(14) Replace entrant (15) Edit seed (16) Swap match positions "
                    "(17) Edit match order: "
                ).strip()
                if action in {"6", "7"}:
                    reason = input("Reason for the change: ").strip()
                    if action == "6":
                        tournament.pause_progression(reason)
                    else:
                        tournament.resume_progression(reason)
                    continue
                if action == "8":
                    if not isinstance(tournament, kot):
                        raise ValueError("Manual round advancement applies only to knockout tournaments.")
                    round_record = next(
                        (row for row in tournament.draw_metadata.get("rounds", [])
                         if row.get("round") == tournament.round_number),
                        None,
                    )
                    if round_record is None or round_record.get("completed"):
                        raise ValueError("There is no incomplete knockout round to advance.")
                    match_map = {match.match_id: match for match in tournament.matches}
                    winners_by_match = {}
                    for match_id in round_record.get("match_ids", []):
                        match = match_map.get(match_id)
                        if match is None:
                            raise ValueError(f"Saved round references missing match {match_id!r}.")
                        print(f"{match.match_id}: {match.player_one.name} vs {match.player_two.name} [{match.status}]")
                        if match.match_finished and match.match_winner is not None:
                            print(f"Recorded winner: {match.match_winner.name}")
                            winners_by_match[match.match_id] = match.match_winner.player_id
                        else:
                            winner = _choose_player({
                                match.player_one.player_id: match.player_one,
                                match.player_two.player_id: match.player_two,
                            }, "Advancing player number: ")
                            winners_by_match[match.match_id] = winner.player_id
                    reason = input("Reason for manual advancement: ").strip()
                    tournament.advance_round_manually(winners_by_match, reason)
                    continue
                if action == "9":
                    print(json.dumps(tournament.audit_log, indent=2, ensure_ascii=False))
                    continue
                if action in {"12", "13", "14", "15"}:
                    reason = input("Reason for the change: ").strip()
                    tournament_players = {p.player_id: p for p in tournament.players}
                    if action == "12":
                        available = {key: value for key, value in players.items()
                                     if key not in tournament_players}
                        entrant = _choose_player(available, "New entrant number: ")
                        tournament.add_entrant(entrant, reason)
                    elif action == "13":
                        entrant = _choose_player(tournament_players, "Entrant to withdraw: ")
                        tournament.remove_entrant(entrant.player_id, reason)
                    elif action == "14":
                        old_player = _choose_player(tournament_players, "Entrant to replace: ")
                        available = {key: value for key, value in players.items()
                                     if key not in tournament_players}
                        new_player = _choose_player(available, "Replacement player: ")
                        tournament.replace_entrant(old_player.player_id, new_player, reason)
                    else:
                        entrant = _choose_player(tournament_players, "Entrant to reseed: ")
                        raw_seed = input("New seed (blank to clear): ").strip()
                        seed = int(raw_seed) if raw_seed else None
                        tournament.set_seed(entrant.player_id, seed, reason)
                    continue
                if action == "16":
                    if len(tournament.matches) < 2:
                        raise ValueError("At least two matches are needed to swap bracket positions.")
                    for index, item in enumerate(tournament.matches, start=1):
                        print(f"{index}. {item.match_id}: {item.player_one.name} vs {item.player_two.name}")
                    first_index = int(input("First match number: ").strip()) - 1
                    second_index = int(input("Second match number: ").strip()) - 1
                    if (not 0 <= first_index < len(tournament.matches)
                            or not 0 <= second_index < len(tournament.matches)
                            or first_index == second_index):
                        raise ValueError("Choose two different listed matches.")
                    first_match = tournament.matches[first_index]
                    second_match = tournament.matches[second_index]
                    first_player = _choose_player({
                        first_match.player_one.player_id: first_match.player_one,
                        first_match.player_two.player_id: first_match.player_two,
                    }, "Player to move from first match: ")
                    second_player = _choose_player({
                        second_match.player_one.player_id: second_match.player_one,
                        second_match.player_two.player_id: second_match.player_two,
                    }, "Player to move from second match: ")
                    reason = input("Reason for the change: ").strip()
                    tournament.swap_match_players(
                        first_match.match_id, first_player.player_id,
                        second_match.match_id, second_player.player_id, reason,
                    )
                    continue
                if action not in {"1", "2", "3", "4", "5", "10", "11", "17"}:
                    raise ValueError("Choose one of the listed tournament actions.")
                if not tournament.matches:
                    raise ValueError("This tournament has no scheduled matches.")
                for index, match in enumerate(tournament.matches, start=1):
                    print(f"{index}. {match.match_id}: {match.player_one.name} vs {match.player_two.name} [{match.status}]")
                match_index = int(input("Select match number: ").strip()) - 1
                if not 0 <= match_index < len(tournament.matches):
                    raise ValueError("Choose a listed match number.")
                match = tournament.matches[match_index]
                reason = input("Reason for the change: ").strip()
                if action == "1":
                    round_no = int(input("New round: ").strip())
                    slot_no = int(input("New slot: ").strip())
                    table = input("Table/court assignment (blank if none): ").strip() or None
                    tournament.reschedule_match(match.match_id, round_no, slot_no, table, reason)
                elif action == "17":
                    round_no = int(input("New round: ").strip())
                    slot_no = int(input("New slot: ").strip())
                    tournament.set_match_order(match.match_id, round_no, slot_no, reason)
                elif action == "2":
                    tournament.set_match_status(match.match_id, "postponed", reason)
                elif action == "3":
                    tournament.set_match_status(match.match_id, "cancelled", reason)
                elif action == "4":
                    tournament.reopen_match(match.match_id, reason)
                elif action == "5":
                    winner = _choose_player({
                        match.player_one.player_id: match.player_one,
                        match.player_two.player_id: match.player_two,
                    }, "Winner number: ")
                    tournament.correct_match_result(match.match_id, winner.player_id, reason)
                elif action in {"10", "11"}:
                    winner = _choose_player({
                        match.player_one.player_id: match.player_one,
                        match.player_two.player_id: match.player_two,
                    }, "Winner number: ")
                    tournament.set_match_status(
                        match.match_id,
                        "walkover" if action == "10" else "retired",
                        reason,
                        winner_id=winner.player_id,
                    )
                else:
                    raise ValueError("Choose one of the listed actions.")
            elif choice == "8":
                draw_path = Path(input("JSON draw file path: ").strip())
                source = draw_path.read_text(encoding="utf-8")
                mapping_text = input(
                    "Optional participant-ID to existing player-ID mapping as JSON (Enter for none): "
                ).strip()
                mapping = json.loads(mapping_text) if mapping_text else {}
                if draw_path.suffix.lower() == ".csv":
                    name = input("Tournament name: ").strip()
                    format_choice = input("Format: (1) Round robin (2) Knockout: ").strip()
                    if format_choice not in {"1", "2"}:
                        raise ValueError("Choose round robin (1) or knockout (2).")
                    format_name = "round_robin" if format_choice == "1" else "knockout"
                    tie_breaks = None
                    if format_name == "round_robin":
                        value = input("Tie-break order (comma separated, Enter for default): ").strip()
                        tie_breaks = [item.strip() for item in value.split(",") if item.strip()] if value else None
                    preview = TournamentDrawService.preview_csv(
                        source, players, name, format_name, _choose_game_config(),
                        tie_break_settings=tie_breaks, player_mapping=mapping,
                    )
                else:
                    preview = TournamentDrawService.preview_json(
                        source, players, player_mapping=mapping,
                    )
                for warning in preview.get("warnings", []):
                    print("Warning:", warning)
                if not preview["valid"]:
                    print("Import problems:")
                    for error in preview["errors"]:
                        print("-", error)
                else:
                    print(f"Preview: {preview['tournament'].get('name')} — {len(preview['entrants'])} entrants, {len(preview['matches'])} matches")
                    if input("Import this draw? (yes/no): ").strip().lower() == "yes":
                        tournament = TournamentDrawService.apply_preview(preview, players, confirmed=True)
                        backup_file(storage.state_filename)
                        tournaments.append(tournament)
                        save_state = storage.attach_autosave(players, tournaments, matches)
                        try:
                            save_state()
                        except OSError:
                            tournaments.remove(tournament)
                            save_state = storage.attach_autosave(players, tournaments, matches)
                            raise
            elif choice == "9":
                tournament = _choose_tournament(tournaments)
                paths = export_tournament_package(tournament, "exports")
                print(f"Exported package: {paths['directory']}")
            elif choice == "10":
                player = _choose_player(players)
                all_matches = list(matches)
                for tournament in tournaments:
                    all_matches.extend(tournament.matches)
                stats = StatisticsService.player_statistics(player.player_id, all_matches)
                print(json.dumps(stats, indent=2, ensure_ascii=False))
            elif choice == "11":
                tournament = _choose_tournament(tournaments)
                if isinstance(tournament, rrt):
                    tournament.recalculate_standings()
                    print("Tie-break order:", ", ".join(tournament.tie_break_settings))
                    tournament.print_standings()
                else:
                    print(f"Round {tournament.round_number}; current entrants:")
                    for player in tournament.current_players:
                        print(f"- {player.name} ({player.player_id})")
                    for match in sorted(
                        tournament.matches,
                        key=lambda item: (item.round_number or 0, item.slot_number or 0),
                    ):
                        winner = match.match_winner.name if match.match_winner else "pending"
                        print(
                            f"Round {match.round_number}, slot {match.slot_number}: "
                            f"{match.player_one.name} vs {match.player_two.name} "
                            f"[{match.status}; winner: {winner}]"
                        )
            elif choice == "12":
                backups = storage.list_state_backups()
                if not backups:
                    raise ValueError("No timestamped state backups are available.")
                for index, backup in enumerate(backups, start=1):
                    print(f"{index}. {backup.name}")
                selected = input("Backup number to restore: ").strip()
                if not selected.isdigit() or not 1 <= int(selected) <= len(backups):
                    raise ValueError("Choose a listed backup number.")
                backup_file(storage.state_filename)
                restored = storage.restore_state_backup(backups[int(selected) - 1])
                print(f"Restored {restored}. Restart the app to load the restored state.")
                return
            elif choice == "13":
                save_state()
                print("Saved.")
                return
            else:
                print("Choose a number from 1 to 13.")
        except (ValueError, OSError, IndexError, RuntimeError) as error:
            print(f"Could not complete that action: {error}")


if __name__ == "__main__":
    main()
