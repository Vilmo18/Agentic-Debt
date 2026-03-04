'''
Terminal entry point for ChatDev Chess.

Play from the Linux terminal using SAN (standard algebraic notation) such as:
  e4, Nf3, O-O, exd5, e8=Q
or coordinate moves:
  e2e4, g7g8q

Features:
- Full legal move generation with check and checkmate enforcement
- Castling (O-O / O-O-O), en passant, and pawn promotion
- SAN listing for current legal moves
- Simple commands: moves, help, quit/exit

Usage:
  python3 main.py
'''
from engine.board import Board
from engine.san import parse_user_input, generate_san_for_move


def print_status(board: Board) -> None:
    turn = "White" if board.white_to_move else "Black"
    check = board.in_check(board.white_to_move)
    print(f"{turn} to move" + (" - Check!" if check else ""))


def main() -> None:
    board = Board()
    board.setup_start_position()
    print("ChatDev Chess - Terminal Mode")
    print("Enter moves in SAN (e.g., e4, Nf3, O-O, exd5, e8=Q) or coordinates (e2e4, g7g8q).")
    print("Type 'moves' to list legal moves, 'help' for help, 'quit' to exit.\n")

    while True:
        board.print_board()

        if board.is_checkmate():
            winner = "Black" if board.white_to_move else "White"
            print(f"Checkmate! {winner} wins.")
            break
        if board.is_stalemate():
            print("Stalemate. Draw.")
            break

        print_status(board)
        try:
            text = input("Your move > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not text:
            continue
        t = text.lower()
        if t in ("quit", "exit"):
            print("Goodbye.")
            break
        if t == "help":
            print("Examples: e4, Nf3, O-O, exd5, e8=Q, g7g8q")
            print("Commands: moves (list legal moves), quit/exit")
            continue
        if t == "moves":
            mlist = board.generate_legal_moves()
            sans = [generate_san_for_move(board, m, mlist) for m in mlist]
            print("Legal moves:", ", ".join(sorted(sans)))
            continue

        mv = parse_user_input(board, text)
        if mv is None:
            print("Invalid or illegal move. Try again.")
            continue

        # Show SAN for the move before making it
        san_played = generate_san_for_move(board, mv)
        board.make_move(mv)
        print(f"Played: {san_played}\n")


if __name__ == "__main__":
    main()