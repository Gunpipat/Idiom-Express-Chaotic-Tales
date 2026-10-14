"""Unit tests for the game rules; run with python -m unittest discover -s tests."""

import random
import unittest
from pathlib import Path

from game_logic import GameState, load_json_data, validate_sentence


PROJECT = Path(__file__).resolve().parents[1]


def sentence_for(idiom: dict, connector: str = "") -> str:
    """Build a simple five-word sentence for testing phrase validation."""
    middle = f"{connector} " if connector else ""
    return f"We {middle}used {idiom['idiom'].lower()} during class today."


class GameLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.idioms, cls.scenarios = load_json_data(PROJECT / "data")

    def make_game(self, idioms=None, mode="solo", players=None):
        return GameState(
            idioms or self.idioms,
            self.scenarios,
            players or (["Ari"] if mode == "solo" else ["Ari", "Bo"]),
            mode=mode,
            rng=random.Random(7),
        )

    def test_existing_catalogs_load_with_enough_content(self):
        self.assertEqual(len(self.idioms), 33)
        self.assertEqual(len(self.scenarios), 10)
        self.assertIn("thai", self.idioms[0])
        self.assertIn("objective", self.scenarios[0])

    def test_phrase_and_minimum_length_are_both_required(self):
        idiom = next(item for item in self.idioms if item["id"] == "break-the-ice")
        valid = validate_sentence(idiom, "We broke the ice before lunch today.")
        self.assertTrue(valid["valid"])
        self.assertFalse(valid["context_confirmed"])
        self.assertFalse(validate_sentence(idiom, "We broke the ice.")["valid"])
        self.assertFalse(validate_sentence(idiom, "We had a nice lunch before class.")["valid"])

    def test_pull_someones_leg_accepts_common_pronoun_variants(self):
        idiom = next(item for item in self.idioms if item["id"] == "pull-someones-leg")
        for sentence in (
            "I was pulling your leg during our science class today.",
            "They pulled somebody's leg before the show started today.",
        ):
            with self.subTest(sentence=sentence):
                self.assertTrue(validate_sentence(idiom, sentence)["valid"])

    def test_solo_accepts_immediately_and_rewards_three_star_idiom(self):
        hardest = next(item for item in self.idioms if item["difficulty"] == 3)
        game = self.make_game([hardest])
        outcome = game.submit(hardest["id"], sentence_for(hardest))
        self.assertFalse(outcome["pending"])
        self.assertEqual(outcome["outcome"]["points"], 15)
        self.assertEqual(game.score, 15)
        self.assertEqual(game.rounds, 1)

    def test_three_different_idioms_award_objective_once(self):
        cards = self.idioms[:3]
        game = self.make_game(cards)
        outcomes = []
        for _ in range(3):
            card_id = game.current_hand[0]
            card = game.idioms[card_id]
            outcomes.append(game.submit(card_id, sentence_for(card))["outcome"])
        self.assertEqual(game.rounds, 3)
        self.assertEqual(len(game.used_idioms), 3)
        self.assertTrue(game.objective_awarded)
        self.assertGreaterEqual(max(outcome["points"] for outcome in outcomes), 20)
        expected = 30 + 10 + 5 * sum(item["difficulty"] == 3 for item in cards)
        self.assertEqual(game.score, expected)

    def test_coop_combo_requires_same_category_and_connector(self):
        by_category = {}
        for idiom in self.idioms:
            by_category.setdefault(idiom["category"], []).append(idiom)
        pair = next(items[:2] for items in by_category.values() if len(items) >= 2)
        game = self.make_game(pair, mode="coop")

        first_id = game.current_hand[0]
        first = game.idioms[first_id]
        game.submit(first_id, sentence_for(first))
        game.resolve("accept")

        second_id = game.current_hand[0]
        second = game.idioms[second_id]
        game.submit(second_id, sentence_for(second, connector="Then"))
        combo = game.resolve("accept")
        expected_combo = 13 + (5 if second["difficulty"] == 3 else 0)
        self.assertEqual(combo["points"], expected_combo)
        self.assertTrue(any("+3" in note for note in combo["notes"]))

        no_connector = self.make_game(pair, mode="coop")
        first_id = no_connector.current_hand[0]
        first_card = no_connector.idioms[first_id]
        no_connector.submit(first_id, sentence_for(first_card))
        no_connector.resolve("accept")
        second_id = no_connector.current_hand[0]
        second_card = no_connector.idioms[second_id]
        no_connector.submit(second_id, sentence_for(second_card))
        plain = no_connector.resolve("accept")
        expected_plain = 10 + (5 if second_card["difficulty"] == 3 else 0)
        self.assertEqual(plain["points"], expected_plain)
        self.assertFalse(any("+3" in note for note in plain["notes"]))

    def test_coop_reject_needs_objection_and_awards_no_points(self):
        idiom = self.idioms[0]
        game = self.make_game([idiom], mode="coop")
        idiom_id = game.current_hand[0]
        selected = game.idioms[idiom_id]
        game.submit(idiom_id, sentence_for(selected))
        with self.assertRaises(ValueError):
            game.resolve("reject")
        review = game.open_objection()
        self.assertEqual(review["idiom"], selected["idiom"])
        result = game.resolve("reject")
        self.assertEqual(result["points"], 0)
        self.assertEqual(game.score, 0)
        self.assertEqual(game.current_player, "Bo")
        self.assertEqual(game.story, [])

    def test_coop_revision_is_revalidated_before_acceptance(self):
        idiom = self.idioms[0]
        game = self.make_game([idiom], mode="coop")
        idiom_id = game.current_hand[0]
        selected = game.idioms[idiom_id]
        game.submit(idiom_id, sentence_for(selected))
        with self.assertRaises(ValueError):
            game.finish()
        game.open_objection()
        invalid = game.resolve("revise", "Too short.")
        self.assertFalse(invalid["valid"])
        self.assertIsNotNone(game.pending_turn)
        revised = sentence_for(selected, connector="Then")
        result = game.resolve("revise", revised)
        self.assertEqual(result["decision"], "revised")
        self.assertEqual(game.story[0]["sentence"], revised)
        self.assertEqual(game.score, 10)

    def test_invalid_attempt_keeps_card_and_does_not_score(self):
        game = self.make_game(self.idioms[:2])
        card_id = game.current_hand[0]
        result = game.submit(card_id, "No idiom in this short line.")
        self.assertFalse(result["valid"])
        self.assertIn(card_id, game.current_hand)
        self.assertEqual(game.score, 0)
        self.assertIsNone(game.pending_turn)

    def test_mode_player_count_and_pending_finish_are_guarded(self):
        with self.assertRaises(ValueError):
            self.make_game(mode="coop", players=["Only one"])
        with self.assertRaises(ValueError):
            self.make_game(mode="coop", players=["Same", "same"])
        game = self.make_game(self.idioms[:1], mode="coop")
        card_id = game.current_hand[0]
        card = game.idioms[card_id]
        game.submit(card_id, sentence_for(card))
        with self.assertRaises(ValueError):
            game.finish()
        game.resolve("accept")
        self.assertEqual(game.finish()["score"], 10)


if __name__ == "__main__":
    unittest.main()
