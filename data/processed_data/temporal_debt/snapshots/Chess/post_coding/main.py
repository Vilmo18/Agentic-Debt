'''

Terminal-based two-player chess game supporting SAN input, castling, en passant, and promotion. 
Includes check and checkmate enforcement and an optional 'undo' and 'help' command. 
Primary entry point for Linux terminal play.

'''

import sys
from engine.board import Board
from engine.san import legal_moves_san_map, parse_user_input


def print_help(board: Board):
    san_map = legal_moves_san_map(board)
    unique_sans = sorted(set(s for s in san_map.keys() if s == s.lower()))  # base lowercase keys
    # Reconstruct display with unique canonical SAN from legal moves to avoid duplicates
    legal_moves = board.generate_legal_moves()
    display = []
    for mv in legal_moves:
        # generate canonical SAN for display using current board
        from engine.san import generate_san_for_move
        san = generate_san_for_move(board, mv, legal_moves)
        display.append(san)
    display = sorted(set(display))
    print("Legal moves (" + ("White" if board.white_to_move else "Black") + "):")
    print(", ".join(display))


def main():
    board = Board()
    board.setup_start_position()
    move_history = []

    print("Terminal Chess - SAN input (e.g., e4, Nf3, O-O, exd8=Q).")
    print("Commands: help, undo, quit")
    while True:
        board.print_board()
        if board.is_checkmate():
            print("Checkmate! " + ("Black" if board.white_to_move else "White") + " wins.")
            break
        if board.is_stalemate():
            print("Stalemate. Draw.")
            break
        if board.in_check(board.white_to_move):
            print("Check.")

        turn_str = "White" if board.white_to_move else "Black"
        try:
            user_in = input(f"{turn_str} to move > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_in:
            continue
        cmd = user_in.lower()
        if cmd in ("quit", "exit"):
            print("Exiting.")
            break
        if cmd == "help":
            print_help(board)
            continue
        if cmd == "undo":
            if not move_history:
                print("Nothing to undo.")
                continue
            move, state = move_history.pop()
            board.undo_move(move, state)
            continue

        move = parse_user_input(board, user_in)
        if move is None:
            print("Invalid move input or illegal in current position. Type 'help' to list legal moves.")
            continue

        state = board.make_move(move)
        move_history.append((move, state))

    return 0


if __name__ == "__main__":
    sys.exit(main())
