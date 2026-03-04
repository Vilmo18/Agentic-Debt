'''

Provides the crossword puzzle dataset(s). For this application,
we include a fully consistent 5x5 "Sator Square" puzzle. The grid
has no black squares; each across word is identical to the down
word at the same order, ensuring valid crossings.

The puzzle includes:
- solution_rows: the final letter layout for the grid
- across_clues_by_answer: clue texts keyed by the across answer
- down_clues_by_answer: clue texts keyed by the down answer

'''

def get_puzzle():
    """
    Returns a dictionary describing a crossword puzzle, including
    the solution rows and clue texts for across and down answers.
    """
    solution_rows = [
        "SATOR",
        "AREPO",
        "TENET",
        "OPERA",
        "ROTAS",
    ]

    across_clues_by_answer = {
        "SATOR": 'Latin "sower"; starts the famous square',
        "AREPO": "Mysterious name from the Sator square",
        "TENET": "Belief or principle",
        "OPERA": "Stage works set to music",
        "ROTAS": "Wheels, in Latin",
    }

    down_clues_by_answer = {
        "SATOR": "Starts the Latin word square",
        "AREPO": "Name found in the palindromic Latin square",
        "TENET": "Doctrine",
        "OPERA": "Grand musical works",
        "ROTAS": "Rotating things, in Latin",
    }

    return {
        "name": "Sator Square Mini (5x5)",
        "solution_rows": solution_rows,
        "across_clues_by_answer": across_clues_by_answer,
        "down_clues_by_answer": down_clues_by_answer,
    }
