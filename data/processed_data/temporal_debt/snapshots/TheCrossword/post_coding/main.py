'''

Main entry point for the Crossword Puzzle application.
Initializes the model with a built-in puzzle, sets up the GUI view,
and connects them via the controller.

'''

import tkinter as tk

from data import get_puzzle
from crossword_model import CrosswordModel
from crossword_view import CrosswordView
from crossword_controller import CrosswordController


def main():
    # Load puzzle data
    puzzle = get_puzzle()

    # Build model
    model = CrosswordModel(
        solution_rows=puzzle["solution_rows"],
        across_clues_by_answer=puzzle["across_clues_by_answer"],
        down_clues_by_answer=puzzle["down_clues_by_answer"],
        title=puzzle.get("name", "Crossword")
    )

    # Build view (Tk root window)
    root = tk.Tk()
    view = CrosswordView(root, title=model.title)

    # Build controller
    controller = CrosswordController(model, view)

    # Start Tkinter main loop
    root.mainloop()


if __name__ == "__main__":
    main()
