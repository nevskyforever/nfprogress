from unittest.mock import patch

import game
import game_data


def test_lottery_draw_counts_matches_and_calculates_prize():
    values = iter((1, 2, 3, 4, 5, 1, 2, 11, 12, 13))
    with patch.object(game_data, 'randint', side_effect=lambda *_: next(values)), \
            patch.object(game_data, 'calculate_item_price', return_value=10):
        draw = game_data.prepare_lottery_ticket_draw()

    assert draw == {
        'player_numbers': [1, 2, 3, 4, 5],
        'winning_numbers': [1, 2, 11, 12, 13],
        'matches': 2,
        'prize': 20,
    }


def test_lottery_prize_is_saved_only_for_a_winning_draw(monkeypatch):
    gamer = game.Gamer(level=1)
    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(gamer, 'save', lambda: None)

    initial_coins = gamer.get_coins()
    message = game_data.complete_lottery_ticket_draw({'matches': 2, 'prize': 20})

    assert gamer.get_coins() == initial_coins + 20
    assert message == 'Совпало 2 числа! Выигрыш: 20 монет.'
