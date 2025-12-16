from os.path import join
import random
import traceback

from openai import OpenAI
from treys import Card

from player import Player

"""You are {self._name} playing a game of virtual AI Texas Hold'em.
Based on the state of the game decide your action from the list of valid actions.
You may think outloud before making your decision inside an XML with the following tag <think></think>.
The last word of your response MUST be your chosen action.
"""

class LlmPlayer(Player):
    @staticmethod
    def from_dict(d: dict, log_dir: str):
        return LlmPlayer(
            log_file_path=f"{join(log_dir, d['name'])}.txt",
            name=d["name"],
            model=d["model"],
            system_prompt=d["system"]
        )

    def __init__(self, log_file_path: str, name: str, model: str, system_prompt: str):
        super().__init__(log_file_path=log_file_path, name=name)
        assert model is not None
        assert isinstance(model, str)

        self._model = model
        self._system_prompt = system_prompt

        self._client = OpenAI(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio"
        )

    def take_action(self, state, valid_actions) -> str:
        community_cards_str = Card.ints_to_pretty_str(state.community_cards)
        assert all(isinstance(c, int) for c in self.hand)
        hand_str = Card.ints_to_pretty_str(self.hand)

        system_prompt = self._system_prompt
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        with open(self._log_file_path, "a") as f:
            f.write(f"Game State:\n{prompt}\n")
            # Execute the prompt
            completion = None
            try:
                completion = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=0.7,
                    stream=False
                )
            except Exception as _:
                completion = None
                f.write(f"ERROR: Failed to prompt llm {traceback.format_exc()}\n")

            # If it failed just randomly select an answer and return
            if completion is None:
                f.write("WARNING: Failed to prompt llm, just generating a random action\n")
                return random.choice(valid_actions)

            # Parse the response
            response_text = completion.choices[0].message.content
            if response_text is None:
                response_text = ""
            response_text = response_text.strip()
            f.write(f"{self._name}:\n{response_text}\n\n")
            end_think_idx = response_text.find("</think>")
            if end_think_idx > -1:
                response_text = response_text[end_think_idx+len("</think>"):].strip()
            response_text = response_text.lower()
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
                f.write("WARNING: model didn't choose a valid option, just generating a random one")
                return random.choice(valid_actions)