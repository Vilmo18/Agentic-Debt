'''

Utilities for reading text files with basic fallback encodings.

'''

from typing import List


def read_text_file(path: str) -> str:
    """
    Try reading text with several encodings, returning decoded string.
    Raises the last exception if all attempts fail.
    """
    encodings: List[str] = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    last_exc: Exception | None = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception as e:
            last_exc = e
            continue
    # Last resort: read binary and decode with 'utf-8' replacing errors
    try:
        with open(path, "rb") as f:
            data = f.read()
        return data.decode("utf-8", errors="replace")
    except Exception:
        if last_exc:
            raise last_exc
        raise
