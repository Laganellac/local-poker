from os.path import join
from typing import List
import random
import traceback

from treys import Card

from player import Player

class HumanPlayer(Player):
    @staticmethod
    def from_dict(d: dict, log_dir: str):
        return HumanPlayer(
            log_file_path=f"{join(log_dir, d['name'])}.txt",
            name=d["name"],
        )

    def __init__(self, log_file_path: str, name: str):
        super().__init__(log_file_path=log_file_path, name=name)
        self._is_human = True

    def take_action(self, state: dict, valid_actions: List[str], history: str) -> str:
        prompt = f"""<GameState>
{self._state_str(state)}
</GameState>
<Decision>
    Valid Actions: {', '.join(valid_actions)}
</Decision>

Reply ONLY with your chosen action from the list of valid actions."""
        with open(self._log_file_path, "a") as f:
            f.write(f"Game State:\n{prompt}\n")
            print(prompt)
            response_text = None
            while True:
                response_text = ""
                try:
                    response_text = input(f"{self._name}'s action: ").strip().lower()
                    if response_text in valid_actions:
                        break
                except Exception as _:
                    f.write(f"ERROR: Failed to prompt human {traceback.format_exc()}\n")
                    response_text = ""
                print(f"ERROR: '{response_text}' is not a valid choice, try again")
            assert response_text in valid_actions
            f.write(f"DEBUG: Used '{response_text}'\n")
            return response_text
