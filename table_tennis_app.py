'''Table Tennis App'''
import uuid
import json
import random
import os
import tempfile
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

        if not isinstance(player_data["player_id"], str):
            raise ValueError("'player_id' must be a string.")

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
    

    def __init__(self, filename="players.json"):
        self.filename = filename

    def save_players(self, players):
        data = {player_id: player.to_dict() for player_id, player in players.items()}
        

        target = Path(self.filename)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=target.parent,
                delete=False,

            ) as temp_file:
                temp_name = temp_file.name
                json.dump(data, temp_file, indent=4)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_name, target)
        except Exception:
            if temp_name and os.path.exists(temp_name):
                os.remove(temp_name)
            raise



    def load_players(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Player file {self.filename!r} contains invalid JSON "
                f"at line {error.lineno}, column {error.colno}."
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

    def recalculate_current_game_score(self):
        self.current_game_score[self.player_one.player_id] = 0
        self.current_game_score[self.player_two.player_id] = 0

        undone_event_ids = {
            event['undone_event_id']
            for event in self.events
            if event.get('type') == EVENT_UNDO
            and 'undone_event_id' in event
        }

        for event in self.events:
            if event.get('type') != EVENT_POINT:
                continue
            if event.get('event_id') in undone_event_ids:
                continue
            player_id = event.get('player_id')
            if player_id not in self.current_game_score:
                raise ValueError(f'Point event has invalid player id: {player_id}')

            self.current_game_score[player_id] += 1


    def add_point(self, scoring_player, server_id=None):
        if self.current_game_finished:
            print("This game has finished. No more points can be added.")
            return
        if scoring_player not in (self.player_one, self.player_two):
            raise ValueError("Scoring player must be one of the players in this game.")
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
            "player_id": scoring_player.player_id,
            "server_id": server_id,
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
        point_event = {
                    "type": EVENT_POINT,
                    'event_id':str(uuid.uuid4()),
                    "player_id": scoring_player.player_id,
                    "server_id": server_id}
        fault_event = {
            'type' : EVENT_FAULT,
            "event_id": str(uuid.uuid4()),
            'point_event_id':point_event['event_id'],
            'fault_player_id' : fault_player.player_id,
            'scoring_player_id' : scoring_player.player_id

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
            "server_id": server_id,
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
            undone_event_ids = {
                event['undone_event_id']
                for event in self.events
                if event['type'] == EVENT_UNDO
                and 'undone_event_id' in event  #set comprehension
            }

            last_point = None
            for event in reversed(self.events):
                if event['type'] != EVENT_POINT:
                    continue
                if event.get('event_id') in undone_event_ids:
                    continue
                last_point = event
                break
            if last_point is None:
                print("No point to undo.")
                return
            undo_event = {"type": EVENT_UNDO,
            "event_id": str(uuid.uuid4()),
            "undone_event_id": last_point["event_id"],
            "undone_player_id": last_point["player_id"],
            "reason": reason
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

    choice = input("Enter choice (1-5): ")

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

    else:
        print("Invalid input. Try again.")


def print_final_match_results(match):
    print("\nMATCH RESULTS:")
    print(f"{match.player_one.name} won {match.games_won[match.player_one.player_id]}")
    print(f"{match.player_two.name} won {match.games_won[match.player_two.player_id]}")

def run_match(match):
    while not match.match_finished:
        if match.server is None:
            match.set_server_from_toss()
        elif match.games:
            previous_first_server_id = match.games[-1].initial_server_id
            match.server = (
                match.player_two
                if previous_first_server_id == match.player_one.player_id
                else match.player_one
            )

        game = Game(
            player_one=match.player_one,
            player_two=match.player_two,
            game_config=match.game_config,
            save_results=True,
            initial_server=match.server,
        )
        print(f"\n{match.server.name} is serving to start the game.")
        while True:
            while not game.current_game_finished:
                input_point_winner(game, match)

            print(f"Game winner: {game.current_game_winner.name}")
            choice = input("(1) Accept game result | (2) Undo last point: ")
            if choice == "1":
                break
            if choice == "2":
                reason = input("Reason for undo: ")
                game.undo_last_point(reason)
                match.update_server(game)
                continue
            print("Invalid input.")

        print("\nEVENT HISTORY:")
        print(game.events)
        match.games.append(game)
        match.update_games_won(game)
        match.check_match_finished()
        print(f"Games won: "
              
    
        f"{match.player_one.name} - {match.games_won[match.player_one.player_id]}, "
        f"{match.player_two.name} - {match.games_won[match.player_two.player_id]}"
        )

        if match.match_finished:
            break

        # Unlimited match: ask whether to continue
        if match.game_config["games_needed_to_win"] is None:

            choice = input("(1) Play another game | (2) End match: ")

            if choice == "2":
                match.match_finished = True
                break

    if match.match_winner is not None:
        if not match.rating_updated:
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
                undone_event_ids = {
                    event.get("undone_event_id")
                    for event in completed_game.events
                    if event.get("type") == EVENT_UNDO
                }
                for event in completed_game.events:
                    if (
                        event.get("type") == EVENT_POINT
                        and event.get("event_id") not in undone_event_ids
                        and event.get("player_id") in point_counts
                    ):
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

        self.server = None
        self.toss_winner = None
        self.rating_updated = False
        self.records_updated = False

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
        if game.initial_server_id not in (
            self.player_one.player_id,
            self.player_two.player_id,
        ):
            raise ValueError("Game is missing a valid initial server.")

        undone_event_ids = {
            event.get("undone_event_id")
            for event in game.events
            if event.get("type") == EVENT_UNDO
        }
        scores = {self.player_one.player_id: 0, self.player_two.player_id: 0}
        server_id = game.initial_server_id
        points_to_win = self.game_config["points_per_game"]
        normal_interval = 2 if points_to_win == 11 else 5

        for event in game.events:
            if event.get("type") != EVENT_POINT:
                continue
            if event.get("event_id") in undone_event_ids:
                continue
            player_id = event.get("player_id")
            if player_id not in scores:
                raise ValueError(f"Point event has invalid player_id: {player_id}")

            scores[player_id] += 1
            total_points = scores[self.player_one.player_id] + scores[self.player_two.player_id]
            at_deuce = (
                scores[self.player_one.player_id] >= points_to_win - 1
                and scores[self.player_two.player_id] >= points_to_win - 1
            )
            interval = 1 if at_deuce else normal_interval
            if total_points % interval == 0:
                server_id = (
                    self.player_two.player_id
                    if server_id == self.player_one.player_id
                    else self.player_one.player_id
                )

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

class rrt(Tournament):
    def __init__ (self,name,players,game_config):
        super().__init__(name,players) #calls __init__ of tournament class
        self.game_config = game_config
        self.standings = self.create_standings()

    def generate_matches(self):

        self.matches = []
        for i in range(len(self.players)):
            for j in range(i+1, len(self.players)):  #starting from i+1 to prevent duplicates
                player_one = self.players[i]
                player_two = self.players[j]

                match = Match(player_one=player_one,
                            player_two=player_two,
                            game_config=self.game_config,
                            )
                self.matches.append(match)
        
    def create_standings(self):
        standings = {}
        for player in self.players:
            standings[player.player_id] = {
                'player' : player,
                'wins' : 0,
                'losses' : 0,
                'games_won' : 0,
                'games_lost' : 0
            }
        return standings

    def run_tournament(self):
        if self.finished:
            return self.winner
        if len(self.players) < 2:
            raise ValueError("A round-robin tournament needs at least two players.")
        if not self.matches:
            self.generate_matches()

        for match in self.matches:
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
        
        self.finished = True
        self.winner = self.get_winner()


    def get_sorted_standings(self):
        return sorted(
            self.standings.values(),
            key=lambda entry: (
                entry["wins"],
                entry["games_won"] - entry["games_lost"] #if wins r equal, checks GD
            ),
            reverse=True #ensures descending order
        )

        
        
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
    def __init__(self,name,players,game_config):
        super().__init__(name,players)
        self.game_config = game_config
        self.current_players = players[:] #creates copy of the list
        self.round_number = 1

    def run_round(self):
        if len(self.current_players) < 2:
            raise ValueError("A knockout round needs at least two players.")

        print(f"\nRound: {self.round_number}")
        winners = []
        #bye handling

        if len(self.current_players) % 2 == 1:
            bye_player = random.choice(self.current_players)
            self.current_players.remove(bye_player)
            winners.append(bye_player)
            print(f"{bye_player.name.title()} gets a bye.")
        self.matches = []
        for i in range(0,len(self.current_players), 2):
            p1 = self.current_players[i]
            p2 = self.current_players[i+1]

            match = Match(p1, p2, self.game_config,) 
            self.matches.append(match)
            run_match(match)
            if match.match_winner is None:
                raise ValueError(
                    "A knockout match ended without a winner; the bracket cannot advance."
                )
            winners.append(match.match_winner)

        self.current_players = winners
        self.round_number += 1


    def run(self):
        if not self.current_players:
            raise ValueError("A knockout tournament needs at least one player.")
        if len(self.current_players) == 1:
            self.finished = True
            self.winner = self.current_players[0]
            return
        while len(self.current_players) > 1:
            
            self.run_round()
        self.finished = True
        self.winner = self.current_players[0]
        print(f"\nTournament Winner: {self.winner.name}")
       




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


if __name__ == "__main__":
    p1 = Player("Aryan", "shakehand", "right", "attacker")
    p2 = Player("Rahul", "penhold", "left", "defender")

    config = {
        "points_per_game": 11,
        "deuce_enabled": True,
        "golden_point_enabled": False,
        "games_needed_to_win": 1
    }

    match = Match(p1, p2, config)
    run_match(match)

