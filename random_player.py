from os.path import join
import random
import traceback

from openai import OpenAI

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


    def take_action(self, _: dict, valid_actions) -> str:
        return random.choice(valid_actions)

