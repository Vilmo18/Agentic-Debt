'''
Mastermind GUI

This module provides a Tkinter-based graphical user interface for the classic
Mastermind code-breaking game. It uses MastermindGame from game_logic.py to handle
the core game logic and renders a visual board of guesses with feedback pegs.

Features:
- Color palette for selecting guess colors.
- Current guess area with slots, Undo, Clear, and Submit actions.
- Board showing the history of guesses and feedback (black=exact, white=partial).
- Status bar displaying attempts left and game messages.
- New Game option to restart at any time.
'''
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import List, Dict, Tuple

from game_logic import MastermindGame


class MastermindGUI:
    """
    Tkinter GUI for the Mastermind game.

    - Uses a palette of colors for the user to build guesses.
    - Displays history rows with guess colors and feedback pegs.
    - Notifies the player about win/lose conditions and supports starting new games.
    """

    # Define an ordered palette of color keys mapped to hex values for display.
    PALETTE: Dict[str, str] = {
        "red": "#e74c3c",
        "green": "#27ae60",
        "blue": "#3498db",
        "yellow": "#f1c40f",
        "orange": "#e67e22",
        "purple": "#9b59b6",
        "cyan": "#1abc9c",
        "pink": "#ff6b9a",
    }

    CODE_LENGTH: int = 4
    MAX_ATTEMPTS: int = 10
    ALLOW_DUPLICATES: bool = True

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the GUI and start a new game."""
        self.root = root

        # Game logic instance
        self.game = MastermindGame(
            code_length=self.CODE_LENGTH,
            colors=list(self.PALETTE.keys()),
            max_attempts=self.MAX_ATTEMPTS,
            allow_duplicates=self.ALLOW_DUPLICATES,
        )

        # UI State
        self.current_guess: List[str] = []
        self.history_rows: List[tk.Frame] = []

        # Build UI sections
        self.build_menu()
        self.build_status_bar()
        self.build_current_guess_area()
        self.build_palette()
        self.build_board()

        # Start first game
        self.start_new_game()

    # ---------- UI Construction ----------

    def build_menu(self) -> None:
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        game_menu = tk.Menu(menubar, tearoff=0)
        game_menu.add_command(label="New Game", command=self.start_new_game)
        game_menu.add_separator()
        game_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="Game", menu=game_menu)
        self.root.config(menu=menubar)

    def build_status_bar(self) -> None:
        """Create a status bar that shows attempts left and messages."""
        self.status_frame = tk.Frame(self.root, padx=8, pady=6)
        self.status_frame.grid(row=0, column=0, sticky="ew")
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Welcome to Mastermind!")
        self.status_label = tk.Label(
            self.status_frame, textvariable=self.status_var, anchor="w", font=("Arial", 12)
        )
        self.status_label.pack(fill="x")

    def build_current_guess_area(self) -> None:
        """Create the area for building the current guess with control buttons."""
        self.guess_frame = tk.LabelFrame(self.root, text="Current Guess", padx=8, pady=8)
        self.guess_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.root.grid_rowconfigure(1, weight=0)

        # Slots for current guess
        self.slot_canvases: List[tk.Canvas] = []
        slots_container = tk.Frame(self.guess_frame)
        slots_container.grid(row=0, column=0, padx=4)

        for i in range(self.CODE_LENGTH):
            c = tk.Canvas(slots_container, width=44, height=44, highlightthickness=0)
            c.grid(row=0, column=i, padx=6)
            c.bind("<Button-1>", lambda e, idx=i: self._clear_slot(idx))
            self.slot_canvases.append(c)

        btns_container = tk.Frame(self.guess_frame)
        btns_container.grid(row=0, column=1, padx=12)

        self.submit_btn = tk.Button(btns_container, text="Submit", width=10, command=self.on_submit)
        self.undo_btn = tk.Button(btns_container, text="Undo", width=10, command=self.on_undo)
        self.clear_btn = tk.Button(btns_container, text="Clear", width=10, command=self.on_clear)

        self.submit_btn.grid(row=0, column=0, padx=4)
        self.undo_btn.grid(row=0, column=1, padx=4)
        self.clear_btn.grid(row=0, column=2, padx=4)

    def build_palette(self) -> None:
        """Create a palette of color buttons for selecting guess colors."""
        self.palette_frame = tk.LabelFrame(self.root, text="Palette", padx=8, pady=8)
        self.palette_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.root.grid_rowconfigure(2, weight=0)

        # Place buttons in a row
        self.palette_buttons: Dict[str, tk.Button] = {}
        for idx, (key, hex_color) in enumerate(self.PALETTE.items()):
            btn = tk.Button(
                self.palette_frame,
                text=key.capitalize(),
                bg=hex_color,
                activebackground=hex_color,
                fg="black",
                width=10,
                relief="raised",
                command=lambda k=key: self.on_color_select(k),
            )
            btn.grid(row=0, column=idx, padx=4, pady=2)
            self.palette_buttons[key] = btn

    def build_board(self) -> None:
        """Create the board showing the history of guesses and feedback pegs."""
        self.board_frame = tk.LabelFrame(self.root, text="Board", padx=8, pady=8)
        self.board_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.root.grid_rowconfigure(3, weight=1)

        # Scrollable area for history rows
        self.board_canvas = tk.Canvas(self.board_frame, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.board_frame, orient="vertical", command=self.board_canvas.yview)
        self.rows_container = tk.Frame(self.board_canvas)

        self.rows_container.bind(
            "<Configure>",
            lambda e: self.board_canvas.configure(scrollregion=self.board_canvas.bbox("all"))
        )
        self.board_canvas.create_window((0, 0), window=self.rows_container, anchor="nw")
        self.board_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.board_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    # ---------- UI Helpers and Drawing ----------

    def refresh_ui(self) -> None:
        """Refresh buttons and slots based on current state."""
        self.draw_guess_slots()
        self.update_status()

        ready = len(self.current_guess) == self.CODE_LENGTH
        can_interact = not self.game.is_over()
        self.submit_btn.config(state=tk.NORMAL if ready and can_interact else tk.DISABLED)
        self.undo_btn.config(state=tk.NORMAL if self.current_guess and can_interact else tk.DISABLED)
        self.clear_btn.config(state=tk.NORMAL if self.current_guess and can_interact else tk.DISABLED)

        for key, btn in self.palette_buttons.items():
            btn.config(state=tk.NORMAL if can_interact and len(self.current_guess) < self.CODE_LENGTH else tk.DISABLED)

    def update_status(self) -> None:
        """Update the status label to reflect attempts left or game outcome."""
        if self.game.has_won():
            self.status_var.set("You cracked the code! Congratulations!")
        elif self.game.is_over():
            secret = " ".join([c.capitalize() for c in self.game.reveal_secret()])
            self.status_var.set(f"Out of attempts. Secret was: {secret}")
        else:
            self.status_var.set(f"Attempts left: {self.game.remaining_attempts()}")

    def draw_guess_slots(self) -> None:
        """Draw the current guess slots."""
        for i, canvas in enumerate(self.slot_canvases):
            color_key = self.current_guess[i] if i < len(self.current_guess) else None
            self._draw_disc(canvas, self.PALETTE.get(color_key, None), radius=18)

    def _draw_disc(self, canvas: tk.Canvas, fill_color: str | None, radius: int = 14) -> None:
        """Draw a colored circular disc on the given canvas."""
        canvas.delete("all")
        w = int(canvas["width"])
        h = int(canvas["height"])
        x0 = (w - 2 * radius) // 2
        y0 = (h - 2 * radius) // 2
        x1 = x0 + 2 * radius
        y1 = y0 + 2 * radius

        if fill_color:
            canvas.create_oval(x0, y0, x1, y1, fill=fill_color, outline="#333333", width=2)
        else:
            # Empty slot: draw outline only
            canvas.create_oval(x0, y0, x1, y1, fill="#f0f0f0", outline="#bbbbbb", width=2)

    def _clear_slot(self, idx: int) -> None:
        """Clear a specific slot in the current guess by index."""
        if self.game.is_over():
            return
        if 0 <= idx < len(self.current_guess):
            # Remove the color from this position and shift left any following colors
            del self.current_guess[idx]
        self.refresh_ui()

    # ---------- Event Handlers ----------

    def on_color_select(self, color_key: str) -> None:
        """Handle selection of a color from the palette."""
        if self.game.is_over():
            return
        if len(self.current_guess) < self.CODE_LENGTH:
            self.current_guess.append(color_key)
            self.refresh_ui()

    def on_submit(self) -> None:
        """Submit the current guess to the game logic and update the board."""
        if len(self.current_guess) != self.CODE_LENGTH or self.game.is_over():
            return

        guess = list(self.current_guess)  # Copy
        exact, partial = self.game.evaluate_guess(guess)

        # Add to board
        row_index = len(self.game.get_history())
        self.add_history_row(guess, exact, partial, row_index)

        # Reset current guess
        self.current_guess = []
        self.refresh_ui()

        # Check game end conditions
        if self.game.has_won():
            self.end_game(win=True)
        elif self.game.is_over():
            self.end_game(win=False)

    def on_clear(self) -> None:
        """Clear the current guess."""
        if self.game.is_over():
            return
        self.current_guess = []
        self.refresh_ui()

    def on_undo(self) -> None:
        """Remove the last selected color from the current guess."""
        if self.game.is_over():
            return
        if self.current_guess:
            self.current_guess.pop()
            self.refresh_ui()

    # ---------- Board Rendering ----------

    def add_history_row(self, guess: List[str], exact: int, partial: int, index: int) -> None:
        """Add a single row to the history board showing guess and feedback pegs."""
        row = tk.Frame(self.rows_container, pady=4)
        row.pack(fill="x", padx=4)

        # Attempt label
        attempt_lbl = tk.Label(row, text=f"{index}.", width=4, anchor="e", font=("Arial", 11))
        attempt_lbl.pack(side="left")

        # Guess discs
        discs_container = tk.Frame(row)
        discs_container.pack(side="left", padx=6)
        for color_key in guess:
            c = tk.Canvas(discs_container, width=32, height=32, highlightthickness=0)
            c.pack(side="left", padx=4)
            self._draw_disc(c, self.PALETTE[color_key], radius=13)

        # Spacer
        spacer = tk.Frame(row, width=10)
        spacer.pack(side="left")

        # Feedback pegs
        peg_canvas = tk.Canvas(row, width=48, height=48, highlightthickness=0)
        peg_canvas.pack(side="left", padx=6)
        self.draw_pegs(peg_canvas, exact, partial)

    def draw_pegs(self, canvas: tk.Canvas, exact: int, partial: int) -> None:
        """Draw feedback pegs (black for exact, white for partial) in a 2x2 grid."""
        canvas.delete("all")
        # Positions for 4 pegs in 2x2 grid
        positions = [(12, 12), (36, 12), (12, 36), (36, 36)]
        r = 6
        colors = ["black"] * exact + ["white"] * partial
        for i, pos in enumerate(positions):
            if i < len(colors):
                fill = colors[i]
            else:
                fill = "#dddddd"  # Empty peg
            x, y = pos
            canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline="#333333", width=1)

    # ---------- Game Flow ----------

    def end_game(self, win: bool) -> None:
        """Handle end-of-game UI state and display a message."""
        for btn in self.palette_buttons.values():
            btn.config(state=tk.DISABLED)
        self.submit_btn.config(state=tk.DISABLED)
        self.undo_btn.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.DISABLED)

        secret = " ".join([c.capitalize() for c in self.game.reveal_secret()])
        if win:
            messagebox.showinfo("You Win!", f"Congratulations, you cracked the code!\n\nSecret: {secret}")
        else:
            messagebox.showinfo("Game Over", f"Out of attempts.\n\nThe secret was: {secret}")

    def start_new_game(self) -> None:
        """Start a new game and reset UI components."""
        # Reset logic
        self.game.new_game()
        self.current_guess = []

        # Clear board
        for child in self.rows_container.winfo_children():
            child.destroy()

        # Re-enable palette
        for btn in self.palette_buttons.values():
            btn.config(state=tk.NORMAL)

        self.refresh_ui()