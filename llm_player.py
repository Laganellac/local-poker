from os.path import join
from typing import List
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

    def take_action(self, state: dict, valid_actions: List[str], history: str) -> str:
        system_prompt = self._system_prompt
        prompt = f"""<RoundHistory>
{history}
</RoundHistory>
<GameState>
{self._state_str(state)}
</GameState>
<Decision>
Valid Actions: {', '.join(valid_actions)}
</Decision>

Reply ONLY with your chosen action from the list of valid actions."""
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
            end_think_idx = response_text.find("</think>")
            if end_think_idx > -1:
                response_text = response_text[end_think_idx+len("</think>"):].strip()
            # NVIDIA model gets really confused about XML in the system prompt, just take the last word
            response_text = response_text.split()[-1].strip().lower()
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