'''

Entry point for the NYT Strands-like puzzle implemented with Tkinter.
Launches the GUI application with a prebuilt puzzle.

'''

from strands.ui import StrandsApp
from strands.puzzle import default_puzzle
import tkinter as tk


def main():
    puzzle = default_puzzle()
    root = tk.Tk()
    app = StrandsApp(root, puzzle)
    root.mainloop()


if __name__ == "__main__":
    main()
