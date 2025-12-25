from typing import List
import sys
import time

from treys import Card, Deck, Evaluator

from action import Action
from player import Player


class Round(object):
    def __init__(
            self,
            active_players: List[Player],
            dealer_position: int,
            deck: Deck,
            evalutor: Evaluator,
            big_blind: int,
            small_blind: int
    ):
        self._active_players = active_players
        self._big_blind_idx = (dealer_position + 2) % len(active_players)
        self._big_blind = big_blind
        self._community_cards = []
        self._dealer_position = dealer_position
        self._deck = deck
        self._evaluator = evalutor
        self._history = ""
        self._min_bet = big_blind
        self._pot = 0
        self._round = "Pre-Flop"
        self._small_blind = small_blind
        self._small_blind_idx = (dealer_position + 1) % len(active_players)

        self._any_human_players = any(p.is_human() for p in self._active_players)

    def _betting_round(self, starting_idx: int, starting_bet: int):
        assert starting_idx < len(self._active_players)
        actions_taken = 0
        active_bet = starting_bet
        min_bet = active_bet * 2 if active_bet > 0 else self._big_blind
        idx = starting_idx
        while actions_taken < len(self._active_players):
            p = self._active_players[idx]
            if not p.can_take_action():
                actions_taken += 1
                idx = (idx + 1) % len(self._active_players)
                continue

            # Determine the valid actions
            to_call = active_bet - p.current_bet
            valid_actions = [Action.FOLD]
            if to_call == 0:
                valid_actions.append(Action.CHECK)
            elif to_call > 0:
                valid_actions.append(Action.CALL)

            if p.current_bet + p.stack >= min_bet:
                valid_actions.append(Action.RAISE)

            # Have the user take an action
            before_action = time.perf_counter()
            action = p.take_action(self._table_state_dict(active_bet, min_bet), valid_actions, self._history)
            after_action = time.perf_counter()
            if action not in valid_actions:
                raise RuntimeError(f"Unexpected action '{action}' not in valid actions {valid_actions}")
            action_time_sec = float((after_action - before_action) * 1000) / 1000.0
            self._history += f">>> {p._name} chooses to: {action.upper()} in {action_time_sec:.3f}s\n"
            # If there are any human players, censor the cards from the output
            if self._any_human_players:
                print(f">>> {p._name} chooses to: {action.upper()} in {action_time_sec:.3f}s")
            else:
                print(f">>> {p._name} ({Card.ints_to_pretty_str(p.hand)}) chooses to: {action.upper()} in {action_time_sec:.3f}s")

            # Handle action
            if action == Action.FOLD:
                p.is_folded = True
                actions_taken += 1
                # If there is only 1 non-folded player left, break out of the loop
                if sum(1 for p in self._active_players if not p.is_folded) == 1:
                    break
            elif action == Action.CHECK:
                actions_taken += 1 
            elif action == Action.RAISE:
                # Move the chips from the player's hand into the pot
                to_raise = min_bet - p.current_bet
                p.stack -= to_raise
                self._pot += to_raise
                p.current_bet = min_bet
                # Update the state, reset actions taken
                active_bet = min_bet
                min_bet = active_bet * 2
                actions_taken = 1
            elif action == Action.CALL:
                p.stack -= to_call
                self._pot += to_call
                p.current_bet += to_call
                actions_taken += 1
            else:
                raise RuntimeError("Non-existant action taken")

            # Move the action around the table
            idx = (idx + 1) % len(self._active_players)

        # Reset players' current bet
        for p in self._active_players:
            p.current_bet = 0

    def _check_win_by_fold(self):
        active = [p for p in self._active_players if not p.is_folded]
        if len(active) == 1:
            winner = active[0]
            winner.stack += self._pot
            print(f"\nResult: Everyone else folded. {winner._name} wins {self._pot} chips!")
            return True
        return False

    def _showdown(self):
        # Lowest score wins
        best_score = sys.maxsize
        winners = []
        for p in self._active_players:
            if p.is_folded:
                continue
            score = self._evaluator.evaluate(self._community_cards, p.hand)

            # Convert score to readable class (e.g. "Full House")
            rank_class = self._evaluator.get_rank_class(score)
            desc = self._evaluator.class_to_string(rank_class)

            print(f"{p._name} ({Card.ints_to_pretty_str(p.hand)}): {desc} (Score: {score})")
            self._history += f"{p._name} ({Card.ints_to_pretty_str(p.hand)}): {desc} (Score: {score})\n"

            if score < best_score:
                best_score = score
                winners = [p]
            elif score == best_score:
                winners.append(p)

        # Award Pot
        if len(winners) == 1:
            w = winners[0]
            w.stack += self._pot
            print(f"\n>>> {w._name} wins the pot of {self._pot}!")
            self._history += f"\n>>> {w._name} wins the pot of {self._pot}!\n"
        else:
            print(f"\n>>> Split Pot! ({len(winners)} ways)")
            self._history += f"\n>>> Split Pot! ({len(winners)} ways)\n"
            split = self._pot // len(winners)
            for w in winners:
                w.stack += split
                print(f"    {w._name} takes {split}")

    def _table_state_dict(self, active_bet: int, min_bet: int) -> dict:
        return {
            "active_bet": active_bet,
            "community_cards": self._community_cards,
            "min_bet": min_bet,
            "pot": self._pot,
            "remaining_players": [p for p in self._active_players if not p.is_folded],
            "round": self._round
        }

    def play_round(self):
        print("---------- STARTING NEW ROUND ----------")
        # Reset each player's round state and shuffle the deck
        for p in self._active_players:
            p.reset_round()
        self._deck.shuffle()
        print("Stacks:")
        for p in self._active_players:
            print(f"  {p._name} {p.stack}")

        # Post blinds
        self._pot += self._small_blind + self._big_blind
        bb_player = self._active_players[self._big_blind_idx]
        sb_player = self._active_players[self._small_blind_idx]
        bb_player.current_bet += self._big_blind
        bb_player.stack -= self._big_blind
        sb_player.current_bet += self._small_blind
        sb_player.stack += self._small_blind
        self._history += f">>> {sb_player._name} posts small blind of {self._small_blind}\n"
        self._history += f">>> {bb_player._name} posts big blind of {self._big_blind}\n"
        print(f">>> {sb_player._name} posts small blind of {self._small_blind}")
        print(f">>> {bb_player._name} posts small blind of {self._big_blind}")

        # Deal hole cards
        for _ in range(0, 2):
            for p in self._active_players:
                p.hand = p.hand + self._deck.draw(1)

        # Pre-flop
        print("---- Pre-Flop ----")
        self._history += "---- Pre-Flop ----\n"
        self._round = "Pre-Flop"
        self._betting_round((self._big_blind_idx + 1) % len(self._active_players), self._big_blind)
        if self._check_win_by_fold(): return

        # Flop
        self._deck.draw(1)
        self._community_cards = self._deck.draw(3)
        print("---- Flop ----")
        print(Card.ints_to_pretty_str(self._community_cards))
        self._history += "---- Flop ----\n"
        self._history += f"{Card.ints_to_pretty_str(self._community_cards)}\n"
        self._round = "Flop"
        self._betting_round((self._dealer_position + 1) % len(self._active_players), 0)
        if self._check_win_by_fold(): return

        # Turn
        self._deck.draw(1)
        self._community_cards += self._deck.draw(1)
        print("---- Turn ----")
        print(Card.ints_to_pretty_str(self._community_cards))
        self._history += "---- Turn ----\n"
        self._history += f"{Card.ints_to_pretty_str(self._community_cards)}\n"
        self._round = "Turn"
        self._betting_round((self._dealer_position + 1) % len(self._active_players), 0)
        if self._check_win_by_fold(): return

        # River
        self._deck.draw(1)
        self._community_cards += self._deck.draw(1)
        print("---- River ----")
        print(Card.ints_to_pretty_str(self._community_cards))
        self._history += "---- River ----\n"
        self._history += f"{Card.ints_to_pretty_str(self._community_cards)}\n"
        self._round = "River"
        self._betting_round((self._dealer_position + 1) % len(self._active_players), 0)
        if self._check_win_by_fold(): return

        print("---- SHOWDOWN ----")
        print(Card.ints_to_pretty_str(self._community_cards))
        self._history += "---- SHOWDOWN ----\n"
        self._history += f"{Card.ints_to_pretty_str(self._community_cards)}\n"
        self._showdown()
