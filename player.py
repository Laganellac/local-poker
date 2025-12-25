from abc import ABC, abstractmethod
from typing import List

from treys import Card

from action import Action

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
        self._is_human = False

    def _state_str(self, state: dict):
        return f"""Round: {state['round']}
Community Cards: {Card.ints_to_pretty_str(state['community_cards'])}
Pot Size: {state['pot']}
Highest Bet to Match: {state['active_bet']}
Your Current Bet in this round: {self.current_bet}
Amount needed to call: {state['active_bet'] - self.current_bet}
Amount needed to raise: {state['min_bet'] - self.current_bet}
Remaining Opponents: {', '.join([p._name for p in state['remaining_players'] if p._name != self._name])}
Your Hand: {Card.ints_to_pretty_str(self.hand)}
Your Stack: {self.stack}"""

    def can_take_action(self) -> bool:
        return not self.is_folded and not self.is_all_in

    def is_human(self) -> bool:
        return self._is_human

    def log(self, message: str):
        with open(self._log_file_path, "a") as f:
            f.write(message)

    def reset_round(self):
        self.hand = []
        self.is_folded = False
        self.current_bet = 0
        self.is_all_in = False

    @abstractmethod
    def take_action(self, state: dict, valid_actions: List[Action], history: str) -> Action:
        pass
