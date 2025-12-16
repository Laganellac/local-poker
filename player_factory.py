from typing import List
import json

from player import Player
from human_player import HumanPlayer
from llm_player import LlmPlayer
from random_player import RandomPlayer

def player_factory(json_players_file_path: str, log_directory: str):
    assert json_players_file_path is not None

    players_list = []
    with open(json_players_file_path, "r") as f:
        players_list = json.load(f)
    if not isinstance(players_list, list):
        raise RuntimeError(f"{json_players_file_path} must contain a list of players!")
    
    players: List[Player] = []
    for p_json in players_list:
        assert isinstance(p_json, dict)
        assert "type" in p_json
        t = p_json["type"]
        if t == "llm":
            players.append(LlmPlayer.from_dict(p_json, log_directory))
        elif t == "human":
            players.append(HumanPlayer.from_dict(p_json, log_directory))
        elif t == "random":
            players.append(RandomPlayer.from_dict(p_json, log_directory))
    return players
