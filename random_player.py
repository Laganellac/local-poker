from os.path import join
from typing import List
import random

from player import Player

class RandomPlayer(Player):
    @staticmethod
    def from_dict(d: dict, log_dir: str):
        return RandomPlayer(
            log_file_path=f"{join(log_dir, d['name'])}.txt",
            name=d["name"],
        )

    def __init__(self, log_file_path: str, name: str):
        super().__init__(log_file_path=log_file_path, name=name)

    def take_action(self, state: dict, valid_actions: List[str], history: str) -> str:
        return random.choice(valid_actions)
