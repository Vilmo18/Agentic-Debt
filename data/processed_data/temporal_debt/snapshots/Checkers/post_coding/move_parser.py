'''

Move notation parser for Checkers (Draughts).
Accepts inputs like "b6-c5" (move) or "c3:e5:g7" (multi-capture).
Supported separators: '-', ':', 'x', spaces, and 'to'.

'''

from typing import List, Tuple


class MoveParseError(Exception):
    pass


class MoveParser:
    @staticmethod
    def parse(text: str) -> List[Tuple[int, int]]:
        if not isinstance(text, str) or not text.strip():
            raise MoveParseError("Empty input.")

        # Normalize separators to spaces
        norm = text.lower().strip()
        norm = norm.replace('-', ' ')
        norm = norm.replace(':', ' ')
        norm = norm.replace('x', ' ')
        norm = norm.replace('to', ' ')
        parts = [p for p in norm.split() if p]

        coords: List[Tuple[int, int]] = []
        for token in parts:
            if len(token) != 2 or token[0] < 'a' or token[0] > 'h' or token[1] < '1' or token[1] > '8':
                raise MoveParseError(f"Invalid square: {token}")
            col_char = token[0]
            row_char = token[1]
            c = ord(col_char) - ord('a')  # a->0, h->7
            # Convert row char to board index: '1' bottom -> row 7, '8' top -> row 0
            r = 8 - int(row_char)
            coords.append((r, c))

        if len(coords) < 2:
            raise MoveParseError("Specify at least source and destination squares.")
        # Ensure moves only on board squares (parsing already enforces)
        return coords
