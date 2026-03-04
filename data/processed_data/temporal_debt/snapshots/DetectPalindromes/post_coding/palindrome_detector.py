'''

Core palindrome detection logic and data structures.

Includes:
- DetectionOptions: configuration for detection
- PalindromeMatch: result representation
- IndexMapper: map global offsets to (line, col)
- normalize_text, is_palindrome
- find_palindromic_words, find_palindromic_sentences, find_palindromic_lines
- detect_palindromes orchestration

'''

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DetectionOptions:
    check_words: bool = True
    check_sentences: bool = True
    check_lines: bool = True
    min_length: int = 3
    ignore_case: bool = True
    ignore_non_alnum: bool = True


@dataclass
class PalindromeMatch:
    category: str  # 'word' | 'sentence' | 'line'
    text: str  # original text slice
    normalized: str  # normalized text used for checking
    length: int  # length of normalized text
    line_no: int  # 1-based line number
    start_pos: int  # 0-based column start in line
    end_pos: int  # 0-based column end in line (exclusive)


class IndexMapper:
    def __init__(self, text: str):
        self.text = text
        self.line_starts = self._compute_line_starts(text)

    @staticmethod
    def _compute_line_starts(text: str):
        # 0 for first line
        starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                starts.append(i + 1)
        return starts

    def pos_to_line_col(self, pos: int):
        # Map global char index to (line_no 1-based, col 0-based)
        # Binary search in line_starts
        starts = self.line_starts
        lo, hi = 0, len(starts) - 1
        line_idx = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if starts[mid] <= pos:
                line_idx = mid
                lo = mid + 1
            else:
                hi = mid - 1
        line_no = line_idx + 1
        col = pos - starts[line_idx]
        return line_no, col


def normalize_text(text: str, ignore_case: bool = True, ignore_non_alnum: bool = True) -> str:
    s = text
    if ignore_non_alnum:
        # Keep only alphanumeric characters
        s = "".join(ch for ch in s if ch.isalnum())
    if ignore_case:
        s = s.casefold()
    return s


def is_palindrome(text: str, ignore_case: bool = True, ignore_non_alnum: bool = True) -> Optional[str]:
    """
    Returns normalized string if it's a palindrome, otherwise None.
    """
    norm = normalize_text(text, ignore_case=ignore_case, ignore_non_alnum=ignore_non_alnum)
    if norm and norm == norm[::-1]:
        return norm
    return None


def find_palindromic_words(
    text: str, min_length: int = 3, ignore_case: bool = True, ignore_non_alnum: bool = True
) -> List[PalindromeMatch]:
    results: List[PalindromeMatch] = []
    mapper = IndexMapper(text)
    # Word tokenizer: \b\w+\b captures word-like tokens including digits/underscore
    for m in re.finditer(r"\b\w+\b", text, flags=re.UNICODE):
        word = m.group(0)
        norm = normalize_text(word, ignore_case=ignore_case, ignore_non_alnum=ignore_non_alnum)
        if len(norm) >= min_length and norm == norm[::-1]:
            start_global, end_global = m.span()
            line_no, start_col = mapper.pos_to_line_col(start_global)
            _, end_col = mapper.pos_to_line_col(end_global)
            results.append(
                PalindromeMatch(
                    category="word",
                    text=word,
                    normalized=norm,
                    length=len(norm),
                    line_no=line_no,
                    start_pos=start_col,
                    end_pos=end_col,
                )
            )
    return results


def find_palindromic_lines(
    text: str, min_length: int = 3, ignore_case: bool = True, ignore_non_alnum: bool = True
) -> List[PalindromeMatch]:
    results: List[PalindromeMatch] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        norm = normalize_text(line, ignore_case=ignore_case, ignore_non_alnum=ignore_non_alnum)
        if len(norm) >= min_length and norm and norm == norm[::-1]:
            line_no = idx + 1
            results.append(
                PalindromeMatch(
                    category="line",
                    text=line,
                    normalized=norm,
                    length=len(norm),
                    line_no=line_no,
                    start_pos=0,
                    end_pos=len(line),
                )
            )
    return results


def find_palindromic_sentences(
    text: str, min_length: int = 3, ignore_case: bool = True, ignore_non_alnum: bool = True
) -> List[PalindromeMatch]:
    results: List[PalindromeMatch] = []
    mapper = IndexMapper(text)
    # Sentence-like segments delimited by punctuation or newline; keep simple segments
    # This pattern matches sequences not containing . ! ? or \n, optionally followed by a punctuation.
    pattern = re.compile(r"[^.!?\n]+[.!?]?", flags=re.UNICODE)
    for m in pattern.finditer(text):
        segment = m.group(0)
        # Skip empty or whitespace-only segments
        if not segment or segment.strip() == "":
            continue
        norm = normalize_text(segment, ignore_case=ignore_case, ignore_non_alnum=ignore_non_alnum)
        if len(norm) >= min_length and norm == norm[::-1]:
            start_global, end_global = m.span()
            line_no, start_col = mapper.pos_to_line_col(start_global)
            _, end_col = mapper.pos_to_line_col(end_global)
            results.append(
                PalindromeMatch(
                    category="sentence",
                    text=segment,
                    normalized=norm,
                    length=len(norm),
                    line_no=line_no,
                    start_pos=start_col,
                    end_pos=end_col,
                )
            )
    return results


def detect_palindromes(text: str, options: DetectionOptions) -> List[PalindromeMatch]:
    results: List[PalindromeMatch] = []
    if options.check_words:
        results.extend(
            find_palindromic_words(
                text,
                min_length=options.min_length,
                ignore_case=options.ignore_case,
                ignore_non_alnum=options.ignore_non_alnum,
            )
        )
    if options.check_sentences:
        results.extend(
            find_palindromic_sentences(
                text,
                min_length=options.min_length,
                ignore_case=options.ignore_case,
                ignore_non_alnum=options.ignore_non_alnum,
            )
        )
    if options.check_lines:
        results.extend(
            find_palindromic_lines(
                text,
                min_length=options.min_length,
                ignore_case=options.ignore_case,
                ignore_non_alnum=options.ignore_non_alnum,
            )
        )

    # Sort results: by line, then start pos, length descending for readability
    results.sort(key=lambda r: (r.line_no, r.start_pos, -r.length, r.category))
    return results
