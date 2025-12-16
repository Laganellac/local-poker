from datetime import datetime
from typing import List
import random
import os
import sys
import time
import traceback

from treys import Card, Deck, Evaluator

from player_factory import player_factory
from player import Player


# --- Helper Functions ---
def format_hand(cards_ints):
    """
    Converts a list of treys integers into readable strings.
    Example: [268446761, 134236965] -> ['Ah', 'Ks']
    """
    if not cards_ints:
        return []
    return [Card.print_pretty_card(c) for c in cards_ints]


def format_hand_pretty(cards_ints):
    """
    Optional: Converts to string for console printing with brackets.
    """
    return str(Card.ints_to_pretty_str(cards_ints))


class HandState(object):
    def __init__(self):
        self.deck = Deck()
        self.deck.shuffle()
        self.pot = 0
        self.highest_bet = 0
        self.active_players: List[Player] = []
        self.dealer_position = 0
        self.community_cards: List[int] = []

class Poker(object):
    def __init__(self, players: List[Player]):
        assert players is not None
        assert len(players) > 0
        assert all(isinstance(p, Player) for p in players)
        self._players = players
        self._starting_stack = 2500
        self._small_blind = 25
        self._big_blind = 50
        self._dealer_position = 0
        self._max_hands = 5
        self.evaluator = Evaluator()

    def play_game(self):
        # Initialize starting stack
        for p in self._players:
            p.stack = self._starting_stack

        dealer_position = 0
        hands = 0
        active_players = [p for p in self._players]
        while len(active_players) >= 2 or hands < self._max_hands:
            state = HandState()
            state.active_players = active_players
            state.dealer_position = dealer_position
            self.play_hand(state)

            # TODO: Handle dealer position correctly when a player busts out
            active_players = [p for p in self._players if p.stack >= self._big_blind]
            dealer_position = (dealer_position + 1) % len(active_players)


    def betting_round(self, state: HandState, start_idx: int):
        current_idx = start_idx
        # We need to loop until everyone has acted and matched the bet
        players_acted = 0
        # If someone raises, we reset the acted counter so others must call
        # A simplified betting loop:

        # Everyone starts as "has not acted" this round except if they are all in or folded
        aggressor_idx = None # Track who made the last raise

        while True:
            # Check if round is complete
            # Round is complete if everyone active has acted AND matched the highest bet
            # OR if everyone but one is folded/all-in

            p = state.active_players[current_idx]

            # Skip if folded or all-in
            if p.is_folded or p.is_all_in:
                current_idx = (current_idx + 1) % len(state.active_players)
                # Optimization: prevent infinite loop if everyone is all in
                if self.is_round_complete(state, start_idx, players_acted):
                    break
                continue

            # Determine valid actions
            to_call = state.highest_bet - p.current_bet
            valid_actions = ['fold']
            if to_call == 0:
                valid_actions.append('check')
            if p.stack > to_call:
                valid_actions.append('raise')
            if p.stack >= to_call:
                valid_actions.append('call')

            # GET DECISION
            action = p.take_action(state, valid_actions).lower()
            print(f">>> {p._name} ({Card.ints_to_pretty_str(p.hand)}) chooses to: {action.upper()}")

            # EXECUTE ACTION
            if action == 'fold':
                p.is_folded = True

            elif action == 'check':
                pass # Do nothing

            elif action == 'call':
                amount = min(p.stack, to_call)
                p.stack -= amount
                p.current_bet += amount
                state.pot += amount
                if p.stack == 0:
                    p.is_all_in = True

            elif action == 'raise':
                # Simple fixed raise (Min raise + Blind) or just double for sim
                raise_amt = to_call + self._big_blind
                if raise_amt > p.stack:
                    raise_amt = p.stack # All in raise
                    p.is_all_in = True

                p.stack -= raise_amt
                p.current_bet += raise_amt
                state.pot += raise_amt

                if p.current_bet > state.highest_bet:
                    state.highest_bet = p.current_bet
                    # Reset the round loop requirement because the bet increased
                    # Everyone else must now act again
                    players_acted = 0

            players_acted += 1
            current_idx = (current_idx + 1) % len(state.active_players)

            # Check break condition: All active players have acted and bets are equal
            if self.is_round_complete(state, start_idx, players_acted):
                break

        # End of betting round: Reset 'current_bet' for next street
        # but keep the pot.
        state.highest_bet = 0
        for p in state.active_players:
            p.current_bet = 0


    def check_winner_by_fold(self, state):
        active = [p for p in state.active_players if not p.is_folded]
        if len(active) == 1:
            winner = active[0]
            winner.stack += state.pot
            print(f"\nResult: Everyone else folded. {winner._name} wins {state.pot} chips!")
            return True
        return False


    def is_round_complete(self, state, start_idx, players_acted):
        active_unfolded = [p for p in state.active_players if not p.is_folded and not p.is_all_in]

        # If 0 or 1 player left acting, round is done
        if len(active_unfolded) < 2:
            # Check if the one player matches the bet (unless they are the aggressor)
            return True

        # Have we gone through everyone at least once?
        if players_acted < len(active_unfolded):
            return False

        # Are all bets equal?
        # Get target bet of any active player
        target = -1
        for p in state.active_players:
            if not p.is_folded and not p.is_all_in:
                if target == -1:
                    target = p.current_bet
                elif p.current_bet != target:
                    return False
        return True


    def play_hand(self, state: HandState):
        print(f"\n{'='*40}\nSTARTING NEW HAND\n{'='*40}")

        # Initialize the new hand
        for p in state.active_players:
            p.reset_round()
            if p.stack < self._big_blind:
                # Shouldn't happen
                print(f"ERROR: Player {p._name} should not be considered an active player!")
                p.is_folded = True

        # Post Blinds
        PLAYERS_COUNT = len(state.active_players)
        sb_idx = (state.dealer_position + 1) % PLAYERS_COUNT
        bb_idx = (state.dealer_position + 2) % PLAYERS_COUNT
        self.post_blind(state, state.active_players[sb_idx], self._small_blind)
        self.post_blind(state, state.active_players[bb_idx], self._big_blind)

        # Deal Hole Cards
        for _ in range(2):
            for p in state.active_players:
                p.hand = p.hand + state.deck.draw(1)

        # Pre-flop
        self.betting_round(state, start_idx=(bb_idx + 1) % PLAYERS_COUNT)
        state.active_players = [p for p in state.active_players if not p.is_folded]
        if self.check_winner_by_fold(state):
            return

        # Flop
        print("\n--- Dealing Flop ---")
        state.community_cards = state.deck.draw(3)
        print(f"Community: {Card.ints_to_pretty_str(state.community_cards)}")
        self.betting_round(state, start_idx=(state.dealer_position+1) % len(state.active_players))
        state.active_players = [p for p in state.active_players if not p.is_folded]
        if self.check_winner_by_fold(state):
            return

        # 3. Turn
        print("\n--- Dealing Turn ---")
        state.community_cards = state.community_cards + state.deck.draw(1)
        print(f"Community: {Card.ints_to_pretty_str(state.community_cards)}")
        self.betting_round(state, start_idx=(state.dealer_position+1) % PLAYERS_COUNT)
        state.active_players = [p for p in state.active_players if not p.is_folded]
        if self.check_winner_by_fold(state):
            return

        # 4. River
        print("\n--- Dealing River ---")
        state.community_cards = state.community_cards + state.deck.draw(1)
        print(f"Community: {Card.ints_to_pretty_str(state.community_cards)}")
        self.betting_round(state, start_idx=(self._dealer_position + 1) % PLAYERS_COUNT)
        if self.check_winner_by_fold(state):
            return

        # 5. Showdown
        self.showdown(state)


    def post_blind(self, state, player: Player, blind: int):
        actual_bet = min(player.stack, blind)
        player.stack -= actual_bet
        player.current_bet = actual_bet
        state.pot += actual_bet
        state.highest_bet = max(state.highest_bet, actual_bet)
        print(f"{player._name} posts blind of {actual_bet}")


    def showdown(self, state: HandState):
        print(f"\n{'='*10} SHOWDOWN {'='*10}")

        print(f"Board: {format_hand_pretty(state.community_cards)}")

        best_score = sys.maxsize
        winners = []

        print("\n--- Hand Analysis ---")
        for p in state.active_players:
            # Treys Evaluator uses integers directly
            score = self.evaluator.evaluate(state.community_cards, p.hand)

            # Convert score to readable class (e.g. "Full House")
            rank_class = self.evaluator.get_rank_class(score)
            desc = self.evaluator.class_to_string(rank_class)

            print(f"{p._name} ({Card.ints_to_pretty_str(p.hand)}): {desc} (Score: {score})")

            if score < best_score:
                best_score = score
                winners = [p]
            elif score == best_score:
                winners.append(p)

        # Award Pot
        if len(winners) == 1:
            w = winners[0]
            w.stack += state.pot
            print(f"\n>>> {w._name} wins the pot of {state.pot}!")
        else:
            print(f"\n>>> Split Pot! ({len(winners)} ways)")
            split = state.pot // len(winners)
            for w in winners:
                w.stack += split
                print(f"    {w._name} takes {split}")


# --- Main Execution ---
if __name__ == "__main__":
    deck = Deck()
    community_cards = deck.draw(5)
    Card.ints_to_pretty_str(community_cards)

    log_directory = f"Game{str(datetime.now())}"
    os.mkdir(log_directory)
    players: List[Player] = player_factory("players.json", log_directory)
    assert len(players) > 0
    assert len(players) == 6
    print(players)

    game = Poker(players)
    game.play_game()

