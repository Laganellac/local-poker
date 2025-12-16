from os.path import join
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


    def take_action(self, state, valid_actions) -> str:
        print(state)
        print(state.community_cards)
        community_cards_str = Card.ints_to_pretty_str(state.community_cards)
        print(community_cards_str)

        prompt = f"""-- Game State --
    Community Cards: {community_cards_str}
    Pot Size: {state.pot}
    Current Highest Bet to Match: {state.highest_bet}
    Your Current Bet in this round: {self.current_bet}
    Amount needed to Call: {state.highest_bet - self.current_bet}
    Your Hand: {Card.ints_to_pretty_str(self.hand)}
    Your Stack: {self.stack}

-- Decision --
    Valid Actions: {', '.join(valid_actions)}

Reply ONLY with your chosen action from the list of valid actions.
    """
        with open(self._log_file_path, "a") as f:
            f.write(f"Game State:\n{prompt}\n")
            print(prompt)
            response_text = None
            try:
                response_text = input(f"{self._name}'s action: ")
            except Exception as _:
                completion = None
                f.write(f"ERROR: Failed to prompt human {traceback.format_exc()}\n")

            # If it failed just randomly select an answer and return
            if response_text is None:
                f.write("WARNING: Failed to prompt human, just generating a random action\n")
                return random.choice(valid_actions)

            # Parse the response
            response_text = response_text.strip()
            f.write(f"{self._name}:\n{response_text}\n\n")
            end_think_idx = response_text.find("</think>")
            if end_think_idx > -1:
                response_text = response_text[end_think_idx+len("</think>"):].strip()
            f.write(f"DEBUG: Used '{response_text}'\n")
            if 'fold' in response_text:
                return 'fold'
            elif 'check' in response_text:
                return 'check'
            elif 'raise' in response_text:
                return 'raise'
            elif 'call' in response_text:
                return 'call'
            else:
                f.write("WARNING: human didn't choose a valid option, just generating a random one")
                return random.choice(valid_actions)
