"""Core rules for Idiom Express: Chaotic Tales.

This module deliberately has no Pygame dependency, so its rules can be tested
with Python's standard library and reused by another interface later.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
CONNECTOR_WORDS = {
    "because", "then", "so", "but", "afterward", "afterwards", "meanwhile",
    "therefore", "however", "finally", "as", "result", "next", "later",
}
HAND_SIZE = 5
MIN_SENTENCE_WORDS = 5
VERB_FORMS = {
    "break": ("break", "breaks", "broke", "breaking"),
    "spill": ("spill", "spills", "spilled", "spilt", "spilling"),
    "hit": ("hit", "hits", "hitting"),
    "cost": ("cost", "costs", "costing"),
    "let": ("let", "lets", "letting"),
    "bite": ("bite", "bites", "bit", "biting"),
    "call": ("call", "calls", "called", "calling"),
    "beat": ("beat", "beats", "beating"),
    "get": ("get", "gets", "got", "getting"),
    "keep": ("keep", "keeps", "kept", "keeping"),
    "miss": ("miss", "misses", "missed", "missing"),
    "speak": ("speak", "speaks", "spoke", "speaking"),
    "burn": ("burn", "burns", "burned", "burnt", "burning"),
    "cut": ("cut", "cuts", "cutting"),
    "hang": ("hang", "hangs", "hung", "hanging"),
    "kill": ("kill", "kills", "killed", "killing"),
    "make": ("make", "makes", "made", "making"),
    "see": ("see", "sees", "saw", "seeing"),
    "take": ("take", "takes", "took", "taking"),
    "give": ("give", "gives", "gave", "giving"),
}


def load_json_data(data_dir: Path | str = DATA_DIR) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load the editable idiom and scenario catalogs from JSON files."""
    folder = Path(data_dir)
    with (folder / "idioms.json").open(encoding="utf-8") as file:
        idioms = json.load(file)
    with (folder / "scenarios.json").open(encoding="utf-8") as file:
        scenarios = json.load(file)
    if not idioms or not scenarios:
        raise ValueError("The game needs at least one idiom and one scenario.")
    return idioms, scenarios


def _idiom_expression(idiom: dict[str, Any]) -> re.Pattern[str]:
    """Build a forgiving phrase matcher for common pronoun variations."""
    idiom_id = idiom["id"]
    phrase = idiom["idiom"]

    def flexible_phrase(text: str) -> str:
        """Escape a phrase while allowing common forms of its first verb."""
        leading_space = text[:1].isspace()
        trailing_space = text[-1:].isspace()
        words = text.split()
        if not words:
            return r"\s+" if leading_space or trailing_space else ""
        forms = VERB_FORMS.get(words[0].casefold())
        first = "(?:" + "|".join(forms) + ")" if forms else re.escape(words[0])
        rest = r"\s+".join(re.escape(word) for word in words[1:])
        result = (r"\s+" if leading_space else "") + first
        if rest:
            result += r"\s+" + rest
        if trailing_space:
            result += r"\s+"
        return result

    if idiom_id == "pull-someones-leg":
        expression = (
            r"\bpull(?:s|ed|ing)?\s+"
            r"(?:someone['’]s|somebody['’]s|your|his|her|their)\s+leg\b"
        )
    elif "someone's" in phrase.casefold():
        before, after = phrase.casefold().split("someone's", 1)
        expression = (
            flexible_phrase(before)
            + r"(?:someone['’]s|somebody['’]s|your|his|her|their)"
            + flexible_phrase(after)
        )
    elif "someone" in phrase.casefold():
        before, after = phrase.casefold().split("someone", 1)
        expression = (
            flexible_phrase(before)
            + r"(?:someone|somebody|you|him|her|them)"
            + flexible_phrase(after)
        )
    else:
        expression = flexible_phrase(phrase)
    return re.compile(r"(?<!\w)" + expression + r"(?!\w)", re.IGNORECASE)


def validate_sentence(idiom: dict[str, Any], sentence: str) -> dict[str, Any]:
    """Check phrase presence and length; meaning fit remains a human decision."""
    clean = sentence.strip()
    words = re.findall(r"[\w’'-]+", clean, flags=re.UNICODE)
    phrase_found = bool(_idiom_expression(idiom).search(clean))
    length_ok = len(words) >= MIN_SENTENCE_WORDS

    if not clean:
        message = "Write a sentence before submitting."
    elif not phrase_found:
        message = f"Include the selected idiom, “{idiom['idiom']},” in your sentence."
    elif not length_ok:
        message = f"Add context: use at least {MIN_SENTENCE_WORDS} words."
    else:
        message = "The phrase and length check passed. Discuss whether the meaning fits."

    return {
        "valid": phrase_found and length_ok,
        "idiom_found": phrase_found,
        "length_ok": length_ok,
        "word_count": len(words),
        "context_confirmed": False,
        "message": message,
        "meaning": idiom["definition"],
        "thai": idiom["thai"],
        "example": idiom["example"],
    }


class GameState:
    """State and rules for a single Solo or local Co-op game."""

    def __init__(
        self,
        idioms: list[dict[str, Any]],
        scenarios: list[dict[str, Any]],
        players: list[str],
        mode: str = "solo",
        scenario: dict[str, Any] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.rng = rng or random.Random()
        self.idioms = {item["id"]: item for item in idioms}
        self.scenarios = scenarios
        self.mode = mode
        self.players = [name.strip() for name in players if name.strip()]
        if mode not in {"solo", "coop"}:
            raise ValueError("Mode must be 'solo' or 'coop'.")
        if mode == "solo" and len(self.players) != 1:
            raise ValueError("Solo mode requires exactly one player.")
        if mode == "coop" and not 2 <= len(self.players) <= 4:
            raise ValueError("Co-op mode requires two to four players.")
        if len({name.casefold() for name in self.players}) != len(self.players):
            raise ValueError("Each player needs a different name.")
        if not self.idioms or not scenarios:
            raise ValueError("The game needs idioms and scenarios.")
        if len(self.idioms) != len(idioms):
            raise ValueError("Each idiom must have a unique id.")

        self.scenario = scenario or self.rng.choice(scenarios)
        card_ids = list(self.idioms)
        self.rng.shuffle(card_ids)
        self.hands: list[list[str]] = [[] for _player in self.players]
        # Deal round-robin so custom catalogs still give every co-op player cards.
        for _card_number in range(HAND_SIZE):
            for hand in self.hands:
                if card_ids:
                    hand.append(card_ids.pop(0))
        self.draw_pile = card_ids

        self.current_player_index = 0
        self.score = 0
        self.rounds = 0
        self.attempts = 0
        self.used_idioms: set[str] = set()
        self.discarded_idioms: set[str] = set()
        self.objective_awarded = False
        self.story: list[dict[str, Any]] = []
        self.turn_history: list[dict[str, Any]] = []
        self.player_scores = {name: 0 for name in self.players}
        self.pending_turn: dict[str, Any] | None = None
        self.objection_open = False
        self.finished = False

    @property
    def current_player(self) -> str:
        return self.players[self.current_player_index]

    @property
    def current_hand(self) -> list[str]:
        return self.hands[self.current_player_index]

    def submit(self, idiom_id: str, sentence: str) -> dict[str, Any]:
        """Validate a sentence; Solo accepts it while Co-op waits for a vote."""
        if self.finished:
            raise ValueError("This game has ended.")
        if self.pending_turn:
            raise ValueError("Resolve the current Co-op turn first.")
        if idiom_id not in self.current_hand:
            raise ValueError("Choose an idiom card from the current player's hand.")

        idiom = self.idioms[idiom_id]
        validation = validate_sentence(idiom, sentence)
        self.attempts += 1
        if not validation["valid"]:
            return {"valid": False, "pending": False, "validation": validation}

        self.pending_turn = {
            "player_index": self.current_player_index,
            "player": self.current_player,
            "idiom_id": idiom_id,
            "sentence": sentence.strip(),
            "validation": validation,
        }
        if self.mode == "solo":
            outcome = self.resolve("accept")
            return {"valid": True, "pending": False, "validation": validation, "outcome": outcome}
        return {"valid": True, "pending": True, "validation": validation}

    def open_objection(self) -> dict[str, Any]:
        """Open a Co-op discussion; the card's meaning and example guide review."""
        if self.mode != "coop" or not self.pending_turn:
            raise ValueError("There is no Co-op turn to challenge.")
        self.objection_open = True
        idiom = self.idioms[self.pending_turn["idiom_id"]]
        return {
            "sentence": self.pending_turn["sentence"],
            "idiom": idiom["idiom"],
            "definition": idiom["definition"],
            "thai": idiom["thai"],
            "example": idiom["example"],
        }

    def resolve(self, decision: str, revised_sentence: str | None = None) -> dict[str, Any]:
        """Accept, revise, or reject a pending Co-op sentence."""
        if not self.pending_turn:
            raise ValueError("There is no submitted sentence waiting for a decision.")
        if decision not in {"accept", "revise", "reject"}:
            raise ValueError("Decision must be accept, revise, or reject.")
        if decision in {"revise", "reject"} and not self.objection_open:
            raise ValueError("Open an objection before revising or rejecting.")

        turn = self.pending_turn
        idiom = self.idioms[turn["idiom_id"]]
        if decision == "revise":
            revised = (revised_sentence or "").strip()
            validation = validate_sentence(idiom, revised)
            if not validation["valid"]:
                return {"valid": False, "validation": validation}
            turn["sentence"] = revised
            turn["validation"] = validation
            accepted_decision = "revised"
        elif decision == "reject":
            self.discarded_idioms.add(turn["idiom_id"])
            history_entry = {
                "player": turn["player"],
                "idiom": idiom,
                "sentence": turn["sentence"],
                "decision": "rejected",
                "points": 0,
                "notes": ["Rejected after an objection; no points were awarded."],
            }
            self.turn_history.append(history_entry)
            self._consume_card(turn)
            self._finish_turn()
            return {"valid": True, "decision": "rejected", "points": 0, "score": self.score, "notes": history_entry["notes"]}
        else:
            accepted_decision = "accepted_after_objection" if self.objection_open else "accepted"

        return self._accept_turn(turn, idiom, accepted_decision)

    def _accept_turn(self, turn: dict[str, Any], idiom: dict[str, Any], decision: str) -> dict[str, Any]:
        """Apply all scoring rules and add an accepted sentence to the story."""
        sentence = turn["sentence"]
        points = 0
        notes: list[str] = []
        idiom_id = turn["idiom_id"]
        if idiom_id not in self.used_idioms:
            points += 10
            notes.append("+10: first accepted use of this idiom.")
            if idiom["difficulty"] == 3:
                points += 5
                notes.append("+5: three-star idiom bonus.")
        else:
            notes.append("No repeat bonus: this idiom has already appeared in the story.")

        previous_story_turn = self.story[-1] if self.story else None
        if (
            self.mode == "coop"
            and previous_story_turn
            and previous_story_turn["idiom"]["category"] == idiom["category"]
            and self._has_connector(sentence)
        ):
            points += 3
            notes.append("+3: same-category idioms are linked by a story connector.")

        self.used_idioms.add(idiom_id)
        if not self.objective_awarded and len(self.used_idioms) >= 3:
            points += 10
            self.objective_awarded = True
            notes.append("+10: the story used three different idioms.")

        self.score += points
        self.rounds += 1
        self.player_scores[turn["player"]] += points
        entry = {
            "player": turn["player"],
            "idiom": idiom,
            "sentence": sentence,
            "decision": decision,
            "points": points,
            "notes": notes,
        }
        self.story.append(entry)
        self.turn_history.append(entry)
        self._consume_card(turn)
        self._finish_turn()
        return {"valid": True, "decision": decision, "points": points, "score": self.score, "notes": notes}

    @staticmethod
    def _has_connector(sentence: str) -> bool:
        words = {word.casefold() for word in re.findall(r"[A-Za-z]+", sentence)}
        return bool(words & CONNECTOR_WORDS)

    def _consume_card(self, turn: dict[str, Any]) -> None:
        """Discard the played card and draw one replacement when available."""
        hand = self.hands[turn["player_index"]]
        idiom_id = turn["idiom_id"]
        if idiom_id in hand:
            hand.remove(idiom_id)
        if self.draw_pile:
            hand.append(self.draw_pile.pop())

    def _finish_turn(self) -> None:
        """Clear the review state and rotate to the next Co-op player."""
        turn = self.pending_turn
        self.pending_turn = None
        self.objection_open = False
        if self.mode == "coop" and turn:
            self.current_player_index = (turn["player_index"] + 1) % len(self.players)

    def finish(self) -> dict[str, Any]:
        """Finish the session and return a compact results summary."""
        if self.pending_turn:
            raise ValueError("Resolve the pending Co-op sentence before ending the game.")
        self.finished = True
        return self.results()

    def results(self) -> dict[str, Any]:
        """Return a display-ready summary without changing game state."""
        return {
            "mode": self.mode,
            "players": self.players[:],
            "scenario": self.scenario,
            "score": self.score,
            "rounds": self.rounds,
            "attempts": self.attempts,
            "unique_idioms": len(self.used_idioms),
            "objective_complete": self.objective_awarded,
            "player_scores": self.player_scores.copy(),
            "story": self.story[:],
        }
