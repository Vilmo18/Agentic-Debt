'''
Optional Tkinter GUI for the chess engine.

Uses Unicode chess glyphs and allows click-to-move, including castling, en passant,
and promotion via a dialog.

Note: The primary entry point for terminal play is main.py. This GUI is optional and separate.
Run with:
  python3 gui.py
'''
import tkinter as tk
from tkinter import messagebox
from typing import Optional, List
from engine.board import Board
from engine.utils import piece_unicode
from engine.move import Move


class PromotionDialog(tk.Toplevel):
    def __init__(self, master, white_to_move: bool):
        super().__init__(master)
        self.title("Promote pawn")
        self.resizable(False, False)
        self.result: Optional[str] = None
        promos = ['Q', 'R', 'B', 'N']

        def choose(p):
            self.result = p if white_to_move else p.lower()
            self.destroy()

        tk.Label(self, text="Choose promotion:").pack(padx=10, pady=10)
        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)
        for p in promos:
            b = tk.Button(frame, text=p, width=4, command=lambda pp=p: choose(pp))
            b.pack(side=tk.LEFT, padx=5)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, 'result', 'Q' if white_to_move else 'q'), self.destroy()))


class ChessGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChatDev Chess")
        self.board = Board()
        self.board.setup_start_position()
        self.buttons: List[List[tk.Button]] = []
        self.selected: Optional[int] = None
        self.legal_targets: List[int] = []
        self.status_var = tk.StringVar()
        self.status_var.set("White to move")
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        board_frame = tk.Frame(self)
        board_frame.pack(padx=10, pady=10)
        for r in range(8):
            row_buttons = []
            for c in range(8):
                btn = tk.Button(board_frame, text="", font=("Arial", 20), width=3, height=1,
                                command=lambda rr=r, cc=c: self.on_click(rr, cc))
                btn.grid(row=r, column=c, sticky="nsew")
                row_buttons.append(btn)
            self.buttons.append(row_buttons)
        # Make grid cells expand evenly
        for i in range(8):
            board_frame.grid_rowconfigure(i, weight=1)
            board_frame.grid_columnconfigure(i, weight=1)
        status_frame = tk.Frame(self)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        tk.Button(status_frame, text="Restart", command=self.on_restart).pack(side=tk.RIGHT)

    def _refresh(self):
        # Update board buttons
        for r in range(8):
            for c in range(8):
                idx = r * 8 + c
                p = self.board.squares[idx]
                text = piece_unicode(p) if p else ''
                btn = self.buttons[r][c]
                btn.config(text=text)
                color = "#EEE" if (r + c) % 2 == 0 else "#8AA"
                if self.selected == idx:
                    color = "#CC6"
                elif idx in self.legal_targets:
                    color = "#6C6"
                btn.config(bg=color, activebackground=color)
        # Update status
        if self.board.is_checkmate():
            winner = "Black" if self.board.white_to_move else "White"
            self.status_var.set(f"Checkmate! {winner} wins.")
            messagebox.showinfo("Game Over", self.status_var.get())
        elif self.board.is_stalemate():
            self.status_var.set("Stalemate. Draw.")
            messagebox.showinfo("Game Over", self.status_var.get())
        else:
            check = self.board.in_check(self.board.white_to_move)
            turn = "White" if self.board.white_to_move else "Black"
            self.status_var.set(f"{turn} to move" + (" - Check" if check else ""))

    def on_restart(self):
        self.board.setup_start_position()
        self.selected = None
        self.legal_targets = []
        self._refresh()

    def on_click(self, row: int, col: int):
        idx = row * 8 + col
        if self.selected is None:
            p = self.board.squares[idx]
            if p is None:
                return
            if (p.isupper() and not self.board.white_to_move) or (p.islower() and self.board.white_to_move):
                return
            self.selected = idx
            legal_from = self.board.get_legal_moves_for_square(idx)
            self.legal_targets = [mv.to_sq for mv in legal_from]
            self._refresh()
        else:
            src = self.selected
            if idx == src:
                # deselect
                self.selected = None
                self.legal_targets = []
                self._refresh()
                return
            legal_from = [mv for mv in self.board.get_legal_moves_for_square(src) if mv.to_sq == idx]
            if not legal_from:
                # select new if piece belongs to side
                p = self.board.squares[idx]
                if p is not None and ((p.isupper() and self.board.white_to_move) or (p.islower() and not self.board.white_to_move)):
                    self.selected = idx
                    legal_from = self.board.get_legal_moves_for_square(idx)
                    self.legal_targets = [mv.to_sq for mv in legal_from]
                    self._refresh()
                else:
                    # invalid target; deselect
                    self.selected = None
                    self.legal_targets = []
                    self._refresh()
                return
            # Handle promotion if necessary
            chosen_move: Optional[Move] = None
            if any(mv.promotion is not None for mv in legal_from):
                dialog = PromotionDialog(self, self.board.white_to_move)
                self.wait_window(dialog)
                promo = dialog.result or ('Q' if self.board.white_to_move else 'q')
                for mv in legal_from:
                    if mv.promotion == promo:
                        chosen_move = mv
                        break
                if chosen_move is None:
                    # fallback to queen
                    for mv in legal_from:
                        if mv.promotion and mv.promotion.upper() == 'Q':
                            chosen_move = mv
                            break
            else:
                chosen_move = legal_from[0]
            self.board.make_move(chosen_move)  # type: ignore[arg-type]
            # Deselect and refresh
            self.selected = None
            self.legal_targets = []
            self._refresh()


def run_gui():
    app = ChessGUI()
    app.mainloop()


if __name__ == "__main__":
    run_gui()