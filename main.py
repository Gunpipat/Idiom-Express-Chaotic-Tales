"""Pygame desktop interface for Idiom Express: Chaotic Tales."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

try:
    import pygame
except ImportError as exc:  # Give new Python learners a useful setup hint.
    raise SystemExit("Pygame is missing. Install it with: python -m pip install -r requirements.txt") from exc

from game_logic import GameState, load_json_data


BASE_SIZE = (1280, 800)
PURPLE = (33, 27, 53)  # #211B35
PURPLE_LIGHT = (54, 45, 79)
PURPLE_MID = (72, 60, 100)
ORANGE = (255, 159, 67)  # #FF9F43
CREAM = (255, 245, 232)  # #FFF5E8
CREAM_DARK = (232, 220, 204)
MUTED = (192, 183, 208)
GREEN = (124, 211, 154)
RED = (255, 132, 125)
PANEL = (43, 36, 66)


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Wrap English and Thai text, splitting long unspaced Thai runs as needed."""
    lines: list[str] = []
    for paragraph in str(text).splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if font.size(candidate)[0] <= max_width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = ""
            # Thai explanations can contain long runs without spaces.
            chunk = ""
            for character in word:
                if chunk and font.size(chunk + character)[0] > max_width:
                    lines.append(chunk)
                    chunk = character
                else:
                    chunk += character
            line = chunk
        if line:
            lines.append(line)
    return lines


class DesktopGame:
    """Own the Pygame window, screen navigation, drawing, and input handling."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Idiom Express: Chaotic Tales")
        self.window = pygame.display.set_mode(BASE_SIZE, pygame.RESIZABLE)
        pygame.display.set_icon(self._make_icon())
        self.canvas = pygame.Surface(BASE_SIZE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.screen = "menu"
        self.mode = "solo"
        self.setup_names = "Storyteller"
        self.setup_error = ""
        self.include_condition = True
        self.input_text = ""
        self.input_focus = False
        self.revision_mode = False
        self.notice = ""
        self.notice_color = MUTED
        self.selected_idiom: str | None = None
        self.story_scroll = 0
        self.hit_targets: list[tuple[pygame.Rect, Callable[[], None], bool]] = []
        self.pointer = (0, 0)
        self.scale = 1.0
        self.offset = (0, 0)
        self.fonts: dict[int, pygame.font.Font] = {}
        self.idioms, self.scenarios = load_json_data()
        self.game: GameState | None = None
        self.last_players: list[str] = ["Storyteller"]

    @staticmethod
    def _make_icon() -> pygame.Surface:
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(icon, ORANGE, (16, 16), 15)
        pygame.draw.line(icon, PURPLE, (9, 17), (14, 22), 3)
        pygame.draw.line(icon, PURPLE, (14, 22), (24, 10), 3)
        return icon

    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        """Choose a Thai-capable Windows font, then fall back to a system font."""
        # Cache normal and bold sizes separately. Pygame's built-in bold style is
        # used so the selected font file can keep its Thai glyph coverage.
        cache_key = size * 2 + int(bold)
        if cache_key not in self.fonts:
            candidates = [
                Path("C:/Windows/Fonts/leelawui.ttf"),
                Path("C:/Windows/Fonts/tahoma.ttf"),
                Path("C:/Windows/Fonts/arial.ttf"),
            ]
            font_path = next((path for path in candidates if path.exists()), None)
            if font_path is None:
                font_path = next(
                    (Path(match) for family in ("Noto Sans Thai", "Tahoma", "Arial", "DejaVu Sans")
                     if (match := pygame.font.match_font(family))),
                    None,
                )
            result = pygame.font.Font(str(font_path), size) if font_path else pygame.font.SysFont("Arial", size)
            result.set_bold(bold)
            self.fonts[cache_key] = result
        return self.fonts[cache_key]

    def text(self, value: str, x: int, y: int, size: int = 20, color=CREAM, bold: bool = False) -> None:
        surface = self.font(size, bold).render(str(value), True, color)
        self.canvas.blit(surface, (x, y))

    def centered_text(self, value: str, rect: pygame.Rect, size: int = 20, color=CREAM, bold: bool = False) -> None:
        surface = self.font(size, bold).render(str(value), True, color)
        self.canvas.blit(surface, surface.get_rect(center=rect.center))

    def paragraph(
        self,
        value: str,
        rect: pygame.Rect,
        size: int = 18,
        color=CREAM,
        line_gap: int = 5,
        max_lines: int | None = None,
    ) -> int:
        font = self.font(size)
        lines = wrap_text(value, font, rect.width)
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines:
                last = lines[-1]
                while last and font.size(last + "…")[0] > rect.width:
                    last = last[:-1]
                lines[-1] = last + "…"
        y = rect.y
        for line in lines:
            self.text(line, rect.x, y, size, color)
            y += font.get_linesize() + line_gap
        return y

    def panel(self, rect: pygame.Rect, fill=PANEL, border=PURPLE_MID, radius: int = 18) -> None:
        pygame.draw.rect(self.canvas, fill, rect, border_radius=radius)
        pygame.draw.rect(self.canvas, border, rect, width=1, border_radius=radius)

    def button(
        self,
        label: str,
        rect: pygame.Rect,
        action: Callable[[], None],
        enabled: bool = True,
        primary: bool = False,
        small: bool = False,
    ) -> None:
        hovered = rect.collidepoint(self.pointer)
        if not enabled:
            fill, color = PURPLE_LIGHT, MUTED
        elif primary:
            fill, color = (ORANGE if hovered else (226, 128, 46)), PURPLE
        else:
            fill, color = (PURPLE_MID if hovered else PURPLE_LIGHT), CREAM
        pygame.draw.rect(self.canvas, fill, rect, border_radius=12)
        pygame.draw.rect(self.canvas, ORANGE if hovered and enabled else PURPLE_MID, rect, 1, border_radius=12)
        self.centered_text(label, rect, 17 if small else 19, color, bold=True)
        self.hit_targets.append((rect, action, enabled))

    def _fit_canvas(self) -> None:
        width, height = self.window.get_size()
        self.scale = min(width / BASE_SIZE[0], height / BASE_SIZE[1])
        drawn_w, drawn_h = int(BASE_SIZE[0] * self.scale), int(BASE_SIZE[1] * self.scale)
        self.offset = ((width - drawn_w) // 2, (height - drawn_h) // 2)

    def _logical_mouse(self, position: tuple[int, int]) -> tuple[int, int]:
        width, height = self.window.get_size()
        scale = min(width / BASE_SIZE[0], height / BASE_SIZE[1])
        if scale <= 0:
            return (0, 0)
        offset = ((width - int(BASE_SIZE[0] * scale)) // 2, (height - int(BASE_SIZE[1] * scale)) // 2)
        return (int((position[0] - offset[0]) / scale), int((position[1] - offset[1]) / scale))

    def start_setup(self, mode: str) -> None:
        self.mode = mode
        self.setup_names = "Storyteller" if mode == "solo" else "Player 1, Player 2"
        self.setup_error = ""
        self.include_condition = True
        self.screen = "setup"
        self.input_focus = True
        pygame.key.start_text_input()

    def start_game(self, players: list[str] | None = None) -> None:
        if players is None:
            names = [part.strip() for part in self.setup_names.split(",") if part.strip()]
            if self.mode == "solo":
                names = names[:1] or ["Storyteller"]
                if len(names) != 1:
                    self.setup_error = "Solo mode uses one player name."
                    return
            elif not 2 <= len(names) <= 4:
                self.setup_error = "Enter 2 to 4 names, separated by commas."
                return
            if len({name.casefold() for name in names}) != len(names):
                self.setup_error = "Use a different name for each player."
                return
            players = names
        self.last_players = players[:]
        self.game = GameState(self.idioms, self.scenarios, players, mode=self.mode)
        self.selected_idiom = self.game.current_hand[0] if self.game.current_hand else None
        self.screen = "game"
        self.story_scroll = 0
        self.input_text = ""
        self.input_focus = True
        self.revision_mode = False
        self.notice = "A random scenario is ready. Use the objective and optional condition to guide your story."
        self.notice_color = MUTED
        pygame.key.start_text_input()

    def restart_game(self) -> None:
        self.mode = "solo" if len(self.last_players) == 1 else "coop"
        self.start_game(self.last_players)

    def go_to_menu(self) -> None:
        self.game = None
        self.screen = "menu"
        self.input_focus = False
        pygame.key.stop_text_input()

    def handle_click(self, position: tuple[int, int]) -> None:
        self.pointer = self._logical_mouse(position)
        # A text field gets focus on click; buttons use the previous completed draw.
        if self.screen == "setup" and pygame.Rect(112, 324, 1056, 70).collidepoint(self.pointer):
            self.input_focus = True
            return
        if self.screen == "setup" and pygame.Rect(116, 458, 28, 28).collidepoint(self.pointer):
            self.toggle_condition()
            return
        if self.screen == "game":
            if self.game and self.game.pending_turn and self.revision_mode:
                input_rect = pygame.Rect(462, 674, 500, 54)
            elif not (self.game and self.game.pending_turn):
                input_rect = pygame.Rect(462, 639, 568, 65)
            else:
                input_rect = None
            if input_rect and input_rect.collidepoint(self.pointer):
                self.input_focus = True
                pygame.key.start_text_input()
                return
        for rect, action, enabled in reversed(self.hit_targets):
            if enabled and rect.collidepoint(self.pointer):
                action()
                return

    def submit_sentence(self) -> None:
        if not self.game:
            return
        if self.revision_mode:
            try:
                outcome = self.game.resolve("revise", self.input_text)
            except ValueError as error:
                self.notice, self.notice_color = str(error), RED
                return
            if not outcome["valid"]:
                self.notice, self.notice_color = outcome["validation"]["message"], RED
                return
            self._after_turn(outcome, "Revision accepted")
            return

        if not self.selected_idiom:
            self.notice, self.notice_color = "There are no idiom cards left in this hand.", RED
            return
        try:
            result = self.game.submit(self.selected_idiom, self.input_text)
        except ValueError as error:
            self.notice, self.notice_color = str(error), RED
            return
        validation = result["validation"]
        if not result["valid"]:
            self.notice, self.notice_color = validation["message"], RED
            return
        if result["pending"]:
            self.input_text = ""
            self.input_focus = False
            pygame.key.stop_text_input()
            self.notice = "Review the phrase together. Accept it, or raise an objection to discuss its meaning."
            self.notice_color = ORANGE
            return
        self._after_turn(result["outcome"], validation["message"])

    def _after_turn(self, outcome: dict, prefix: str = "Accepted") -> None:
        self.input_text = ""
        self.input_focus = True
        self.revision_mode = False
        if self.game and self.game.current_hand:
            self.selected_idiom = self.game.current_hand[0]
        else:
            self.selected_idiom = None
        points = outcome.get("points", 0)
        self.notice = f"{prefix}. +{points} points. Total score: {outcome.get('score', 0)}."
        self.notice_color = GREEN if points else MUTED
        pygame.key.start_text_input()

    def raise_objection(self) -> None:
        if not self.game:
            return
        try:
            self.game.open_objection()
            self.notice = "Objection opened. Compare the definition and example, then vote or revise."
            self.notice_color = ORANGE
        except ValueError as error:
            self.notice, self.notice_color = str(error), RED

    def accept_pending(self) -> None:
        if not self.game:
            return
        try:
            outcome = self.game.resolve("accept")
            self._after_turn(outcome, "Story turn accepted")
        except ValueError as error:
            self.notice, self.notice_color = str(error), RED

    def reject_pending(self) -> None:
        if not self.game:
            return
        try:
            outcome = self.game.resolve("reject")
            self._after_turn(outcome, "Turn rejected; the card was discarded")
        except ValueError as error:
            self.notice, self.notice_color = str(error), RED

    def begin_revision(self) -> None:
        if self.game and self.game.pending_turn:
            self.revision_mode = True
            self.input_text = self.game.pending_turn["sentence"]
            self.input_focus = True
            self.notice = "Edit the sentence, keep the idiom, and submit a five-word minimum revision."
            self.notice_color = ORANGE
            pygame.key.start_text_input()

    def end_game(self) -> None:
        if not self.game:
            return
        try:
            self.game.finish()
            self.screen = "results"
            self.input_focus = False
            pygame.key.stop_text_input()
        except ValueError as error:
            self.notice, self.notice_color = str(error), RED

    def handle_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            if self.screen in {"setup", "game", "results"}:
                self.go_to_menu()
            else:
                self.running = False
            return
        if event.key == pygame.K_F2 and self.screen == "game":
            self.restart_game()
            return
        if event.key == pygame.K_RETURN and self.input_focus:
            if self.screen == "game":
                self.submit_sentence()
            return
        if event.key == pygame.K_BACKSPACE and self.input_focus:
            if self.screen == "setup":
                self.setup_names = self.setup_names[:-1]
            elif self.screen == "game":
                self.input_text = self.input_text[:-1]

    def add_text_input(self, text: str) -> None:
        if not self.input_focus:
            return
        if self.screen == "setup":
            self.setup_names = (self.setup_names + text)[:100]
        elif self.screen == "game":
            self.input_text = (self.input_text + text)[:600]

    def draw_menu(self) -> None:
        self.canvas.fill(PURPLE)
        # Warm accent shapes add visual structure without external image assets.
        pygame.draw.circle(self.canvas, PURPLE_LIGHT, (1110, 160), 150)
        pygame.draw.circle(self.canvas, PURPLE_MID, (1110, 160), 112, width=2)
        pygame.draw.arc(self.canvas, ORANGE, pygame.Rect(1010, 60, 200, 200), 0.4, 4.9, 9)
        self.text("IDIOM EXPRESS", 112, 130, 27, ORANGE, True)
        self.text("Chaotic Tales", 108, 174, 62, CREAM, True)
        self.paragraph(
            "Learn English idioms by building silly stories. Play solo or pass the computer around for local co-op.",
            pygame.Rect(112, 258, 680, 78), 23, MUTED, 8, 3,
        )
        self.panel(pygame.Rect(105, 366, 520, 282), fill=PURPLE_LIGHT)
        self.text("Choose a game", 136, 392, 22, MUTED, True)
        self.button("เล่นคนเดียว  /  Solo Mode", pygame.Rect(136, 438, 452, 62), lambda: self.start_setup("solo"), primary=True)
        self.button("เล่นด้วยกัน  /  Co-op Mode", pygame.Rect(136, 516, 452, 62), lambda: self.start_setup("coop"))
        self.button("Exit", pygame.Rect(136, 594, 132, 42), lambda: setattr(self, "running", False), small=True)
        self.paragraph("33 idioms   •   10 random scenarios   •   English + Thai learning support", pygame.Rect(111, 704, 850, 35), 17, MUTED)
        self.text("PYTHON + PYGAME", 1030, 704, 15, MUTED, True)

    def draw_setup(self) -> None:
        self.canvas.fill(PURPLE)
        self.text("Set up your story", 94, 68, 38, CREAM, True)
        self.text("A random scenario will be selected when the game starts.", 96, 120, 19, MUTED)
        self.panel(pygame.Rect(78, 176, 1124, 516))
        mode_label = "Solo mode / เล่นคนเดียว" if self.mode == "solo" else "Co-op mode / เล่น 2–4 คน"
        self.text(mode_label, 112, 210, 24, ORANGE, True)
        self.text("Player name" if self.mode == "solo" else "Player names — separate names with commas", 112, 282, 20, CREAM)
        field = pygame.Rect(112, 324, 1056, 70)
        pygame.draw.rect(self.canvas, PURPLE, field, border_radius=12)
        pygame.draw.rect(self.canvas, ORANGE if self.input_focus else PURPLE_MID, field, 2, border_radius=12)
        shown = self.setup_names + ("|" if self.input_focus else "")
        self.paragraph(shown or "Click here and type a name", pygame.Rect(field.x + 18, field.y + 22, field.width - 36, 36), 21, CREAM)
        help_text = "Example: Maya, Ben, Jo" if self.mode == "coop" else "Press Start when your name is ready."
        self.text(help_text, 116, 408, 17, MUTED)
        checkbox = pygame.Rect(116, 458, 28, 28)
        pygame.draw.rect(self.canvas, ORANGE if self.include_condition else PURPLE_MID, checkbox, border_radius=5)
        if self.include_condition:
            pygame.draw.line(self.canvas, PURPLE, (checkbox.x + 6, checkbox.y + 14), (checkbox.x + 12, checkbox.y + 20), 3)
            pygame.draw.line(self.canvas, PURPLE, (checkbox.x + 12, checkbox.y + 20), (checkbox.x + 23, checkbox.y + 7), 3)
        self.button("Optional story condition / เงื่อนไขเสริม", pygame.Rect(158, 450, 405, 42), self.toggle_condition, small=True)
        self.paragraph("When enabled, try to include the scenario's extra condition. It is a creative challenge, not an automatic score check.", pygame.Rect(158, 499, 840, 50), 16, MUTED, 3, 2)
        if self.setup_error:
            self.text(self.setup_error, 116, 571, 18, RED)
        self.button("Back", pygame.Rect(116, 616, 140, 48), self.go_to_menu)
        self.button("Start game", pygame.Rect(865, 606, 303, 62), self.start_game, primary=True)
        self.text("Tip: click the name box, type normally, and use commas between Co-op names.", 116, 670, 14, MUTED)

    def toggle_condition(self) -> None:
        self.include_condition = not self.include_condition

    def draw_scenario_header(self, game: GameState) -> None:
        self.panel(pygame.Rect(20, 18, 1240, 188), fill=PURPLE_LIGHT)
        self.text(f"RANDOM SCENARIO  •  {game.scenario.get('difficulty', 'Mixed').upper()}", 44, 35, 15, ORANGE, True)
        self.text(game.scenario["title"], 44, 57, 28, CREAM, True)
        self.paragraph(game.scenario["description"], pygame.Rect(44, 100, 1180, 42), 17, MUTED, 2, 2)
        self.text("OBJECTIVE", 44, 153, 14, ORANGE, True)
        self.text(game.scenario["objective"], 44, 173, 16, CREAM)
        condition = game.scenario.get("special_condition", "")
        if condition and self.include_condition:
            label = "OPTIONAL CONDITION"
            label_surface = self.font(14, True).render(label, True, ORANGE)
            self.canvas.blit(label_surface, (680, 153))
            self.paragraph(condition, pygame.Rect(680, 173, 545, 28), 15, CREAM, 1, 1)

    def draw_card_details(self, game: GameState, rect: pygame.Rect) -> None:
        self.panel(rect, fill=PURPLE_LIGHT)
        idiom = game.idioms.get(self.selected_idiom or "")
        if not idiom:
            self.text("No cards remain in this hand.", rect.x + 16, rect.y + 18, 17, MUTED)
            return
        self.text(idiom["idiom"], rect.x + 15, rect.y + 12, 18, ORANGE, True)
        self.text(f"Difficulty {idiom['difficulty']}/3  •  {idiom['category']}", rect.x + 15, rect.y + 38, 13, MUTED)
        y = rect.y + 61
        self.text("MEANING", rect.x + 15, y, 12, MUTED, True)
        y = self.paragraph(idiom["definition"], pygame.Rect(rect.x + 15, y + 17, rect.width - 30, 39), 14, CREAM, 1, 2)
        self.text("ภาษาไทย", rect.x + 15, y + 2, 12, MUTED, True)
        y = self.paragraph(idiom["thai"], pygame.Rect(rect.x + 15, y + 19, rect.width - 30, 42), 14, CREAM, 1, 2)
        self.text("EXAMPLE", rect.x + 15, y + 1, 12, MUTED, True)
        self.paragraph(idiom["example"], pygame.Rect(rect.x + 15, y + 18, rect.width - 30, max(24, rect.bottom - y - 22)), 13, CREAM_DARK, 1, 2)

    def draw_game(self) -> None:
        game = self.game
        if not game:
            self.go_to_menu()
            return
        self.canvas.fill(PURPLE)
        self.draw_scenario_header(game)

        left = pygame.Rect(20, 220, 390, 560)
        right = pygame.Rect(426, 220, 834, 560)
        self.panel(left)
        self.panel(right)
        self.text("YOUR IDIOM HAND", 40, 237, 16, ORANGE, True)
        self.text(f"{game.current_player}'s turn" if game.mode == "coop" else "Choose a card", 40, 261, 15, MUTED)

        card_y = 290
        for index, idiom_id in enumerate(game.current_hand):
            idiom = game.idioms[idiom_id]
            rect = pygame.Rect(38, card_y + index * 48, 354, 40)
            selected = idiom_id == self.selected_idiom
            fill = PURPLE_MID if selected else PURPLE_LIGHT
            pygame.draw.rect(self.canvas, fill, rect, border_radius=9)
            if selected:
                pygame.draw.rect(self.canvas, ORANGE, rect, 2, border_radius=9)
            title = idiom["idiom"]
            if self.font(15, True).size(title)[0] > 265:
                while title and self.font(15, True).size(title + "…")[0] > 265:
                    title = title[:-1]
                title += "…"
            self.text(title, rect.x + 12, rect.y + 10, 15, CREAM, True)
            self.text(f"D{idiom['difficulty']}", rect.right - 50, rect.y + 10, 14, ORANGE, True)
            self.hit_targets.append((rect, lambda selected_id=idiom_id: self.select_card(selected_id), True))

        self.draw_card_details(game, pygame.Rect(38, 542, 354, 218))

        # Score and controls stay visible while the story grows.
        self.panel(pygame.Rect(444, 236, 798, 62), fill=PURPLE_LIGHT)
        self.text(f"SCORE  {game.score}", 460, 256, 18, ORANGE, True)
        self.text(f"TURNS  {game.rounds}", 594, 256, 17, CREAM, True)
        self.text(f"IDIOMS  {len(game.used_idioms)}/3", 710, 256, 16, CREAM)
        self.button("Restart", pygame.Rect(888, 246, 96, 42), self.restart_game, small=True)
        self.button("Menu", pygame.Rect(990, 246, 78, 42), self.go_to_menu, small=True)
        self.button("End game", pygame.Rect(1074, 246, 148, 42), self.end_game, enabled=game.pending_turn is None, small=True)

        story_rect = pygame.Rect(444, 310, 798, 274)
        self.panel(story_rect, fill=PURPLE_LIGHT)
        self.text("THE STORY SO FAR", 462, 326, 16, ORANGE, True)
        self.text("Accepted turns become part of the shared story.", 462, 348, 14, MUTED)
        visible = 4
        end_index = max(0, len(game.story) - self.story_scroll)
        start_index = max(0, end_index - visible)
        entries = game.story[start_index:end_index]
        row_y = 374
        if not entries:
            self.paragraph("Your story starts with the first accepted sentence. Pick an idiom card and write at least five words.", pygame.Rect(462, row_y, 746, 60), 16, MUTED, 3, 3)
        for entry in entries:
            self.text(f"{entry['player']}  •  {entry['idiom']['idiom']}  •  +{entry['points']}", 462, row_y, 14, ORANGE, True)
            self.paragraph(entry["sentence"], pygame.Rect(462, row_y + 20, 746, 35), 15, CREAM, 1, 2)
            row_y += 51
        if len(game.story) > visible:
            self.text("Mouse wheel scrolls story", 1010, 326, 12, MUTED)

        self.draw_composer(game, pygame.Rect(444, 596, 798, 164))

    def select_card(self, idiom_id: str) -> None:
        self.selected_idiom = idiom_id
        self.notice = ""
        self.input_focus = True

    def draw_composer(self, game: GameState, rect: pygame.Rect) -> None:
        self.panel(rect)
        self.text("WRITE THE NEXT SENTENCE", rect.x + 18, rect.y + 12, 15, ORANGE, True)
        if game.pending_turn:
            turn = game.pending_turn
            idiom = game.idioms[turn["idiom_id"]]
            text_top = rect.y + 35
            label = "REVISION" if self.revision_mode else "WAITING FOR CO-OP REVIEW"
            self.text(label, rect.x + 18, text_top, 13, MUTED, True)
            self.text(f"{turn['player']} used {idiom['idiom']}:", rect.x + 18, text_top + 20, 14, CREAM)
            if self.revision_mode:
                entry_rect = pygame.Rect(rect.x + 18, rect.y + 78, 500, 54)
                self.draw_input(entry_rect, self.input_text, self.input_focus, placeholder="Edit the sentence…")
                self.button("Submit revision", pygame.Rect(rect.x + 535, rect.y + 80, 205, 43), self.submit_sentence, primary=True, small=True)
                self.button("Back to vote", pygame.Rect(rect.x + 535, rect.y + 128, 205, 28), self.cancel_revision, small=True)
                self.paragraph(turn["sentence"], pygame.Rect(rect.x + 18, rect.y + 56, 495, 18), 12, MUTED, 0, 1)
                if self.notice:
                    self.text(self.notice, rect.x + 18, rect.y + 139, 13, self.notice_color)
            else:
                self.paragraph(turn["sentence"], pygame.Rect(rect.x + 18, text_top + 43, 490, 44), 15, CREAM, 1, 2)
                if game.objection_open:
                    self.text("Review: compare the card's meaning/example with the sentence.", rect.x + 18, rect.y + 112, 12, MUTED)
                    self.button("Accept", pygame.Rect(rect.x + 516, rect.y + 52, 90, 40), self.accept_pending, primary=True, small=True)
                    self.button("Revise", pygame.Rect(rect.x + 614, rect.y + 52, 90, 40), self.begin_revision, small=True)
                    self.button("Reject", pygame.Rect(rect.x + 712, rect.y + 52, 76, 40), self.reject_pending, small=True)
                    self.text("Rejected cards earn no points.", rect.x + 525, rect.y + 102, 12, MUTED)
                else:
                    self.button("Accept", pygame.Rect(rect.x + 550, rect.y + 62, 130, 42), self.accept_pending, primary=True, small=True)
                    self.button("Object", pygame.Rect(rect.x + 690, rect.y + 62, 105, 42), self.raise_objection, small=True)
                    self.text("Object opens a meaning check.", rect.x + 550, rect.y + 112, 12, MUTED)
                if self.notice:
                    self.text(self.notice, rect.x + 18, rect.y + 141, 12, self.notice_color)
            return

        entry_rect = pygame.Rect(rect.x + 18, rect.y + 43, 568, 65)
        self.draw_input(entry_rect, self.input_text, self.input_focus, placeholder="Write a sentence using the selected idiom…")
        self.button("Submit", pygame.Rect(rect.x + 602, rect.y + 51, 176, 45), self.submit_sentence, primary=True, small=True)
        help_text = "At least 5 words. Enter submits. Phrase matching checks the idiom, not whether its meaning fits."
        self.text(help_text, rect.x + 18, rect.y + 117, 12, MUTED)
        if self.notice:
            self.paragraph(self.notice, pygame.Rect(rect.x + 18, rect.y + 138, 750, 22), 13, self.notice_color, 0, 1)

    def draw_input(self, rect: pygame.Rect, value: str, focused: bool, placeholder: str) -> None:
        pygame.draw.rect(self.canvas, PURPLE, rect, border_radius=10)
        pygame.draw.rect(self.canvas, ORANGE if focused else PURPLE_MID, rect, 2 if focused else 1, border_radius=10)
        content = value[-80:] if value else placeholder
        self.paragraph(content + ("|" if focused else ""), pygame.Rect(rect.x + 12, rect.y + 10, rect.width - 24, rect.height - 12), 15, CREAM if value else MUTED, 2, 3)

    def cancel_revision(self) -> None:
        self.revision_mode = False
        self.input_focus = False
        self.notice = "Choose Accept or Reject, or reopen the sentence with Revise."
        self.notice_color = MUTED
        pygame.key.stop_text_input()

    def draw_results(self) -> None:
        game = self.game
        if not game:
            self.go_to_menu()
            return
        result = game.results()
        self.canvas.fill(PURPLE)
        self.text("STORY COMPLETE", 84, 56, 16, ORANGE, True)
        self.text("Chaotic Tales", 84, 84, 42, CREAM, True)
        self.panel(pygame.Rect(78, 158, 1124, 250), fill=PURPLE_LIGHT)
        self.text(f"{result['score']} points", 112, 190, 44, ORANGE, True)
        self.text(f"{result['rounds']} accepted turns  •  {result['unique_idioms']} different idioms", 116, 250, 20, CREAM)
        objective = "Objective bonus earned!" if result["objective_complete"] else "Use three different idioms for the story objective bonus."
        self.text(objective, 116, 292, 18, GREEN if result["objective_complete"] else MUTED)
        self.text(f"Scenario: {game.scenario['title']}", 116, 341, 17, CREAM)
        y = 434
        self.text("PLAYER POINTS", 112, y, 15, ORANGE, True)
        y += 28
        for player, score in result["player_scores"].items():
            self.text(f"{player}: {score}", 116, y, 18, CREAM)
            y += 30
        self.panel(pygame.Rect(600, 430, 590, 230), fill=PURPLE_LIGHT)
        self.text("STORY RECAP", 622, 448, 15, ORANGE, True)
        recap_y = 478
        recap_entries = result["story"][-4:]
        for entry in recap_entries:
            self.text(f"{entry['player']} • {entry['idiom']['idiom']}", 622, recap_y, 13, MUTED, True)
            self.paragraph(entry["sentence"], pygame.Rect(622, recap_y + 18, 540, 34), 14, CREAM, 1, 2)
            recap_y += 44
        self.button("Restart with same players", pygame.Rect(112, 690, 325, 58), self.restart_game, primary=True)
        self.button("Main menu", pygame.Rect(454, 690, 200, 58), self.go_to_menu)

    def draw(self) -> None:
        self.hit_targets = []
        self.pointer = self._logical_mouse(pygame.mouse.get_pos())
        if self.screen == "menu":
            self.draw_menu()
        elif self.screen == "setup":
            self.draw_setup()
        elif self.screen == "game":
            self.draw_game()
        elif self.screen == "results":
            self.draw_results()

        self.window.fill(PURPLE)
        width, height = self.window.get_size()
        self._fit_canvas()
        scaled_size = (int(BASE_SIZE[0] * self.scale), int(BASE_SIZE[1] * self.scale))
        scaled = pygame.transform.smoothscale(self.canvas, scaled_size)
        self.window.blit(scaled, self.offset)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type in {pygame.VIDEORESIZE, getattr(pygame, "WINDOWRESIZED", -1)}:
                    size = getattr(event, "size", None)
                    if size is None:
                        size = (getattr(event, "w", BASE_SIZE[0]), getattr(event, "h", BASE_SIZE[1]))
                    self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
                elif event.type == pygame.MOUSEMOTION:
                    self.pointer = self._logical_mouse(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.MOUSEWHEEL and self.screen == "game" and self.game:
                    self.story_scroll = max(0, min(len(self.game.story), self.story_scroll + event.y))
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
                elif event.type == pygame.TEXTINPUT:
                    self.add_text_input(event.text)
            self.draw()
        pygame.key.stop_text_input()
        pygame.quit()


if __name__ == "__main__":
    try:
        DesktopGame().run()
    except (OSError, ValueError) as error:
        print(f"Could not start Idiom Express: {error}", file=sys.stderr)
        raise SystemExit(1) from error