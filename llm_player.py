from os.path import join
from typing import List
import random
import traceback

from openai import OpenAI
from treys import Card

from action import Action
from player import Player

"""You are {self._name} playing a game of virtual AI Texas Hold'em.
Based on the state of the game decide your action from the list of valid actions.
You may think outloud before making your decision inside an XML with the following tag <think></think>.
The last word of your response MUST be your chosen action.
"""

class LlmPlayer(Player):
    @staticmethod
    def from_dict(d: dict, log_dir: str):
        system_prompt = d.get("system", "")
        if len(system_prompt) == 0:
            # If the system prompt wasn't defined directly, it's probably in a file
            with open(d["systemFile"], "r") as f:
                system_prompt = f.read()

        return LlmPlayer(
            log_file_path=f"{join(log_dir, d['name'])}.txt",
            name=d["name"],
            model=d["model"],
            system_prompt=system_prompt
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

    def take_action(self, state: dict, valid_actions: List[Action], history: str) -> Action:
        system_prompt = self._system_prompt
        prompt = f"""<RoundHistory>
{history}
</RoundHistory>
<GameState>
{self._state_str(state)}
</GameState>

Reply with an explanation of your thought process ending with "/explanation" followed by a new line.
After that, the last word of your response MUST BE one of the valid actions [{', '.join(valid_actions)}]"""
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
            # Skip the thinking block
            end_think_idx = response_text.find("/explanation")
            if end_think_idx > -1:
                response_text = response_text[end_think_idx+len("/explanation"):].strip()
            response_text = response_text.split()[-1].strip().upper()
            f.write(f"DEBUG: Used '{response_text}'\n")

            # If it's not a valid option, just pick a random valid option
            if response_text not in valid_actions:
                f.write(f"WARNING: {self._name} chose '{response_text}' which is not a valid action ({valid_actions}), just generating a random one")
                return random.choice(valid_actions)
            assert response_text in valid_actions
            return Action(response_text)
