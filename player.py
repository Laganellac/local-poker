from abc import ABC, abstractmethod
from typing import List

class Player(ABC):
    def __init__(self, log_file_path: str, name: str):
        assert log_file_path is not None
        assert name is not None

        self._log_file_path = log_file_path
        self._name = name

        self.stack = 0

        self.hand = []
        self.is_folded = False
        self.current_bet = 0  # Amount bet in the current round
        self.is_all_in = False


    def log(self, message: str):
        with open(self._log_file_path, "a") as f:
            f.write(message)


    def reset_round(self):
        self.hand = []
        self.is_folded = False
        self.current_bet = 0
        self.is_all_in = False

    @abstractmethod
    def take_action(self, state, valid_actions: List[str]) -> str:
        pass