from datetime import datetime
from typing import List
import os
import sys

from treys import Card, Deck, Evaluator

from player_factory import player_factory
from player import Player
from round import Round


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


class Poker(object):
    def __init__(self, players: List[Player], evaluator: Evaluator, deck: Deck):
        assert players is not None
        assert len(players) > 0
        assert all(isinstance(p, Player) for p in players)
        self._players = players
        self._starting_stack = 2500
        self._small_blind = 25
        self._big_blind = 50
        self._dealer_position = 0
        self._max_hands = 1000
        self._evaluator = evaluator
        self._deck = deck

    def play_game(self):
        # Initialize starting stack
        for p in self._players:
            p.stack = self._starting_stack

        dealer_position = 0
        hands = 0
        active_players = [p for p in self._players]
        while len(active_players) >= 2 or hands < self._max_hands:
            round = Round(active_players, dealer_position, self._deck, self._evaluator, self._big_blind, self._small_blind)
            round.play_round()
            # Remove the players that have busted out and move the dealer chip
            active_players = [p for p in self._players if p.stack >= self._big_blind]
            dealer_position = (dealer_position + 1) % len(active_players)
            hands += 1

# --- Main Execution ---
if __name__ == "__main__":
    log_directory = f"Game{str(datetime.now())}"
    os.mkdir(log_directory)

    players_file = "players.json"
    if len(sys.argv) > 1:
        players_file = sys.argv[1]

    players: List[Player] = player_factory(players_file, log_directory)
    assert len(players) > 0
    assert len(players) == 6
    print(players)

    deck = Deck()
    evaluator = Evaluator()
    game = Poker(
        players,
        evaluator,
        deck
    )
    game.play_game()

