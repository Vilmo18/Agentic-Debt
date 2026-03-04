'''

Main GUI entry point for the daily 4x4 word grouping puzzle game using Tkinter.
Builds the interface, loads a daily puzzle, and manages gameplay: selection,
submission, feedback, shuffling, mistakes, and revealing solved groups.
'''

import tkinter as tk
from tkinter import messagebox
from datetime import date
from typing import Dict, List, Set
import random

from puzzle import generate_daily_puzzle, get_color_for_difficulty, Puzzle
from utils import today_date_str


class GameApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Daily Connections - 4x4 Word Groups")
        self.resizable(False, False)

        # State variables
        self.puzzle: Puzzle = None
        self.date_str: str = today_date_str()
        self.remaining_words: List[str] = []
        self.selected_words: Set[str] = set()
        self.word_buttons: Dict[str, tk.Button] = {}
        self.solved_categories: Set[int] = set()
        self.mistakes: int = 0
        self.max_mistakes: int = 4
        self.game_finished: bool = False

        # Colors and styling
        self.bg_default = "#f0f0f0"
        self.bg_word = "#ffffff"
        self.bg_selected = "#ffe082"  # light amber
        self.bg_incorrect_flash = "#ef5350"
        self.bg_correct_flash = "#66bb6a"
        self.fg_default = "#333333"
        self.fg_muted = "#666666"
        self.font_word = ("Helvetica", 12, "bold")
        self.font_title = ("Helvetica", 16, "bold")
        self.font_small = ("Helvetica", 10)
        self.padding = 8

        self.configure(bg=self.bg_default)
        self.build_ui()
        # Load today's puzzle
        self.load_puzzle(generate_daily_puzzle(), self.date_str)

    def build_ui(self):
        # Header
        header = tk.Frame(self, bg=self.bg_default, padx=self.padding, pady=self.padding)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        self.title_label = tk.Label(header, text="Connections", font=self.font_title, bg=self.bg_default, fg=self.fg_default)
        self.title_label.grid(row=0, column=0, sticky="w")

        self.date_label = tk.Label(header, text="", font=self.font_small, bg=self.bg_default, fg=self.fg_muted)
        self.date_label.grid(row=0, column=1, sticky="e")

        # Status row
        status = tk.Frame(self, bg=self.bg_default, padx=self.padding)
        status.grid(row=1, column=0, sticky="ew")
        status.grid_columnconfigure(1, weight=1)

        self.mistakes_label = tk.Label(status, text="Mistakes: 0/4", font=self.font_small, bg=self.bg_default, fg=self.fg_default)
        self.mistakes_label.grid(row=0, column=0, sticky="w")

        self.feedback_label = tk.Label(status, text="", font=self.font_small, bg=self.bg_default, fg=self.fg_default)
        self.feedback_label.grid(row=0, column=1, sticky="e")

        # Solved groups area
        self.solved_frame = tk.Frame(self, bg=self.bg_default, padx=self.padding, pady=self.padding)
        self.solved_frame.grid(row=2, column=0, sticky="ew")
        # Create placeholders for up to 4 solved panels
        self.solved_panels: Dict[int, tk.Frame] = {}  # cat_id -> frame

        # Grid area
        self.grid_frame = tk.Frame(self, bg=self.bg_default, padx=self.padding, pady=self.padding)
        self.grid_frame.grid(row=3, column=0)

        # Controls
        controls = tk.Frame(self, bg=self.bg_default, padx=self.padding, pady=self.padding)
        controls.grid(row=4, column=0, sticky="ew")
        controls.grid_columnconfigure(4, weight=1)

        self.submit_btn = tk.Button(controls, text="Submit", command=self.submit_guess, state=tk.DISABLED)
        self.submit_btn.grid(row=0, column=0, padx=4)

        self.deselect_btn = tk.Button(controls, text="Deselect All", command=self.deselect_all)
        self.deselect_btn.grid(row=0, column=1, padx=4)

        self.shuffle_btn = tk.Button(controls, text="Shuffle", command=self.shuffle_words)
        self.shuffle_btn.grid(row=0, column=2, padx=4)

        self.reset_btn = tk.Button(controls, text="Reset Today", command=self.reset_today)
        self.reset_btn.grid(row=0, column=3, padx=4)

        help_btn = tk.Button(controls, text="How to Play", command=self.show_how_to_play)
        help_btn.grid(row=0, column=5, padx=4, sticky="e")

    def load_puzzle(self, puzzle: Puzzle, date_str: str):
        # Reset state
        self.puzzle = puzzle
        self.date_str = date_str
        self.remaining_words = list(puzzle.words)
        self.selected_words.clear()
        self.word_buttons.clear()
        self.solved_categories.clear()
        self.mistakes = 0
        self.game_finished = False

        # Update header/status
        self.date_label.config(text=f"Daily Puzzle: {self.date_str}")
        self.mistakes_label.config(text=f"Mistakes: {self.mistakes}/{self.max_mistakes}")
        self.feedback_label.config(text="")

        # Clear solved panels and grid
        for widget in self.solved_frame.winfo_children():
            widget.destroy()
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.solved_panels.clear()

        # Build empty 4 slots for solved panels (optional, we add as they are solved)
        # Render initial grid
        self.update_grid()
        self.submit_btn.config(state=tk.DISABLED)
        self.shuffle_btn.config(state=tk.NORMAL)

    def update_grid(self):
        # Destroy current buttons
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.word_buttons.clear()

        # Determine rows: keep 4 columns, rows = ceil(n/4)
        n = len(self.remaining_words)
        cols = 4
        rows = (n + cols - 1) // cols if n > 0 else 0

        # Create buttons row-major
        idx = 0
        for r in range(rows):
            for c in range(cols):
                if idx < n:
                    word = self.remaining_words[idx]
                    btn = tk.Button(self.grid_frame, text=word.upper(), width=16, height=2,
                                    bg=self.bg_word, fg=self.fg_default, font=self.font_word,
                                    relief=tk.RAISED,
                                    command=lambda w=word: self.on_word_click(w))
                    btn.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
                    self.word_buttons[word] = btn
                    # If selected prior to re-render, maintain highlight
                    if word in self.selected_words:
                        btn.config(bg=self.bg_selected)
                    idx += 1
                else:
                    # Empty placeholder to maintain grid shape (optional)
                    placeholder = tk.Label(self.grid_frame, text="", width=16, height=2, bg=self.bg_default)
                    placeholder.grid(row=r, column=c, padx=4, pady=4)

    def on_word_click(self, word: str):
        if self.game_finished:
            return
        if word not in self.remaining_words:
            return

        if word in self.selected_words:
            self.selected_words.remove(word)
            self.word_buttons[word].config(bg=self.bg_word)
        else:
            # Add and if over 4, pop the oldest selected
            self.selected_words.add(word)
            self.word_buttons[word].config(bg=self.bg_selected)
            if len(self.selected_words) > 4:
                # Remove an arbitrary previously selected word to keep max 4
                # Prefer to remove the one selected earliest; track order
                # We don't track order; instead, deselect a random currently selected different from the latest
                # Simpler: prevent adding beyond 4
                self.selected_words.remove(word)
                self.word_buttons[word].config(bg=self.bg_word)
                self.feedback("Select exactly four words.", transient=True)
        # Enable submit only when exactly four are selected
        if len(self.selected_words) == 4:
            self.submit_btn.config(state=tk.NORMAL)
        else:
            self.submit_btn.config(state=tk.DISABLED)

    def submit_guess(self):
        if self.game_finished:
            return
        if len(self.selected_words) != 4:
            self.feedback("Select exactly four words.", transient=True)
            return

        selection = list(self.selected_words)
        # Check if all 4 belong to the same category and that category not solved
        cat_ids = {self.puzzle.word_to_category[w] for w in selection}
        if len(cat_ids) == 1:
            cat_id = next(iter(cat_ids))
            if cat_id in self.solved_categories:
                # Already solved category; shouldn't be possible since words would be removed
                self.feedback("That group is already solved.", transient=True)
                return
            # Correct
            self.handle_correct_group(cat_id)
        else:
            # Incorrect
            self.handle_incorrect_guess(selection)

    def handle_correct_group(self, cat_id: int):
        category = self.puzzle.categories[cat_id]
        # Remove words from remaining
        for w in category.words:
            if w in self.remaining_words:
                self.remaining_words.remove(w)
        # Flash green on selected
        for w in list(self.selected_words):
            btn = self.word_buttons.get(w)
            if btn:
                btn.config(bg=self.bg_correct_flash)
        self.after(250, self.update_grid)

        # Clear selection
        self.selected_words.clear()
        self.submit_btn.config(state=tk.DISABLED)

        # Reveal category panel
        self.add_solved_panel(cat_id)

        self.solved_categories.add(cat_id)
        self.feedback(f"Correct: {category.name}", transient=False)

        # Check win
        if len(self.solved_categories) == 4:
            self.game_finished = True
            self.shuffle_btn.config(state=tk.DISABLED)
            self.feedback("You solved today's puzzle! Come back tomorrow.", transient=False)

    def handle_incorrect_guess(self, selected_words: List[str]):
        self.mistakes += 1
        self.mistakes_label.config(text=f"Mistakes: {self.mistakes}/{self.max_mistakes}")
        # Flash red on selected, then revert
        for w in selected_words:
            btn = self.word_buttons.get(w)
            if btn:
                btn.config(bg=self.bg_incorrect_flash)
        self.after(350, self._revert_selected_highlight)

        # Keep the selection highlighted after revert (select color)
        # Provide feedback
        remaining = self.max_mistakes - self.mistakes
        if remaining > 0:
            self.feedback(f"Incorrect. {remaining} mistake(s) left.", transient=True)
        else:
            self.feedback("No mistakes left. Revealing solution...", transient=False)
            self.game_over()

    def _revert_selected_highlight(self):
        # Restore selected highlight color
        for w in self.selected_words:
            btn = self.word_buttons.get(w)
            if btn:
                btn.config(bg=self.bg_selected)

    def add_solved_panel(self, cat_id: int):
        category = self.puzzle.categories[cat_id]
        panel = tk.Frame(self.solved_frame, bg=get_color_for_difficulty(category.difficulty), padx=8, pady=6, bd=1, relief=tk.SOLID)
        panel.pack(fill="x", pady=4)
        # Title and difficulty
        title = tk.Label(panel, text=f"{category.name} ({category.difficulty.title()})", bg=panel["bg"], fg="#000000", font=("Helvetica", 12, "bold"))
        title.pack(anchor="w")
        # Words
        words_label = tk.Label(panel, text=", ".join(w.upper() for w in category.words), bg=panel["bg"], fg="#000000", font=("Helvetica", 10))
        words_label.pack(anchor="w")
        self.solved_panels[cat_id] = panel

    def game_over(self):
        self.game_finished = True
        self.shuffle_btn.config(state=tk.DISABLED)
        self.submit_btn.config(state=tk.DISABLED)
        # Reveal all remaining categories
        remaining_cat_ids = [i for i in range(4) if i not in self.solved_categories]
        for cid in remaining_cat_ids:
            self.add_solved_panel(cid)
        # Disable all buttons
        for btn in self.word_buttons.values():
            btn.config(state=tk.DISABLED)
        messagebox.showinfo("Game Over", "You've used all mistakes. The remaining groups have been revealed.")

    def shuffle_words(self):
        if self.game_finished:
            return
        rng = random.Random()  # non-deterministic shuffle for the session
        rng.shuffle(self.remaining_words)
        self.update_grid()

    def deselect_all(self):
        # Clear selection and restore button backgrounds
        for w in list(self.selected_words):
            btn = self.word_buttons.get(w)
            if btn:
                btn.config(bg=self.bg_word)
        self.selected_words.clear()
        self.submit_btn.config(state=tk.DISABLED)

    def show_how_to_play(self):
        msg = (
            "Group the 16 words into 4 categories of 4 words each.\n"
            "- Select exactly four words and press Submit.\n"
            "- Correct groups are removed and revealed with their category.\n"
            "- You have at most 4 mistakes.\n"
            "- Shuffle rearranges the remaining words.\n"
            "- A new puzzle is generated every day.\n"
            "Tip: Words may seem to fit multiple categories, but there is only one correct solution."
        )
        messagebox.showinfo("How to Play", msg)

    def reset_today(self):
        # Reload the same day's puzzle deterministically
        self.load_puzzle(generate_daily_puzzle(), today_date_str())

    def feedback(self, text: str, transient: bool):
        self.feedback_label.config(text=text)
        if transient:
            # Clear after short delay
            self.after(1500, lambda: self.feedback_label.config(text=""))


if __name__ == "__main__":
    app = GameApp()
    app.mainloop()
