# Idiom Express: Chaotic Tales — Pygame Edition

A local desktop storytelling game for learning English idioms. This version uses Python and Pygame only; it does not run a web server or use HTML, CSS, or JavaScript. The original Flask project is kept separately and remains untouched.

## Features

- Solo mode and local 2–4 player pass-and-play Co-op
- A random scenario, story objective, and optional creative condition
- Five-card hands with definitions, Thai meanings, examples, and difficulty stars
- Sentence checks for idiom phrase and a five-word minimum
- Co-op objection, accept, revise, and reject decisions
- Story recap, turn management, scoring, restart, and menu navigation
- Resizable Pygame window with a dark purple, orange, and warm cream palette
- 33 idioms and 10 scenarios loaded from editable JSON files

## Install and run

Python 3.10 or newer is required.

### Windows PowerShell

Open PowerShell in this project folder and run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks environment activation, use the venv Python directly:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

The game window opens on the local computer. There is no localhost address, browser, or deployment server.

## Controls

- Click **Solo Mode** or **Co-op Mode** in the main menu.
- In setup, type one name for Solo or 2–4 comma-separated names for Co-op.
- The story scenario is selected randomly when a game starts. The optional condition can be switched on or off before play.
- Click an idiom card to read its English definition, Thai meaning, example, and difficulty. Click the sentence field, type a sentence, then press **Enter** or click **Submit**.
- In Co-op, a valid sentence waits for a vote. **Object** opens a discussion using the card's definition and example. After an objection, the group may accept the sentence, revise it, or reject it. A rejected use consumes the card and earns no points.
- **End game** shows the results; **Restart** starts a fresh random story with the same players; **Menu** returns to the main menu. **Esc** returns to the menu and **F2** restarts during a game.
- Use the mouse wheel over the story panel to review older accepted turns.

## Scoring

- +10 for the first accepted use of an idiom in a story
- +5 for a three-star idiom's first accepted use
- +10 once the story uses three different idioms
- +3 in Co-op when consecutive accepted idioms share a category and the new sentence contains a story connector (for example, “then” or “because”)
- Rejected turns earn no points; using the same idiom again does not earn the first-use bonus

The validator checks phrase presence and sentence length. It does not automatically judge grammar or whether the idiom's meaning fits. Co-op players make that decision together through discussion.

## Project files

```text
idiom-express-desktop/
├── main.py                 # Pygame window, menu, screens, and input
├── game_logic.py           # JSON loading, validation, turns, objections, and scoring
├── data/
│   ├── idioms.json         # Idiom text, Thai meanings, examples, and difficulty
│   └── scenarios.json      # Random scenarios and optional conditions
├── tests/
│   └── test_game_logic.py  # Standard-library unit tests
├── requirements.txt
└── README.md
```

To add content, edit the JSON arrays and keep each item's existing fields. Idioms need `id`, `idiom`, `definition`, `thai`, `example`, `difficulty`, and `category`. Scenarios need `id`, `title`, `description`, `difficulty`, `objective`, and `special_condition`.

## Run tests

No Pygame window is needed for the core rules tests:

```powershell
python -m unittest discover -s tests -v
```

## Upload to GitHub

Create an empty repository on GitHub, open a terminal in this project folder, then run:

```bash
git init
git add .
git commit -m "Build Idiom Express Pygame desktop game"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Replace the remote URL with your repository URL. Submit the GitHub repository link to your teacher. `.gitignore` excludes the virtual environment and generated Python files.
