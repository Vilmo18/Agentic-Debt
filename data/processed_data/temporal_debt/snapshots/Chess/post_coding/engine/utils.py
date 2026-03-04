'''

Utility helpers for chess engine: coordinate conversions, piece helpers, and unicode mapping.

'''

FILES = "abcdefghijklmnopqrstuvwxyz"


def index_to_coord(idx: int):
    row = idx // 8
    col = idx % 8
    return row, col


def coord_to_index(row: int, col: int) -> int:
    return row * 8 + col


def index_to_square(idx: int) -> str:
    row, col = index_to_coord(idx)
    file_char = "abcdefgh"[col]
    rank_char = str(8 - row)
    return f"{file_char}{rank_char}"


def square_to_index(s: str) -> int:
    s = s.strip().lower()
    if len(s) != 2 or s[0] not in "abcdefgh" or s[1] not in "12345678":
        raise ValueError("Invalid square notation")
    col = ord(s[0]) - ord('a')
    row = 8 - int(s[1])
    return coord_to_index(row, col)


def is_white(piece: str) -> bool:
    return piece.isupper()


UNICODE_MAP = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
}


def piece_unicode(piece: str) -> str:
    return UNICODE_MAP.get(piece, ' ')
