'''

A modest English word list (lowercase) used to validate "non-theme" words that
reward hints in the Strands puzzle. Words must be length >= 4 to count.

This is not exhaustive; you can expand as needed.

'''

WORDS = {
    # Common short words (4-7 letters)
    "soft", "ware", "wars", "sore", "rose", "rows", "soar", "toes", "tore", "tone",
    "twin", "twine", "tire", "wore", "wont", "went", "west", "wise", "wine",
    "ring", "wing", "wins", "wets", "swan", "sift", "swift", "snow", "sofa",
    "star", "start", "stare", "stew", "stow", "straw", "straws", "strawed",
    "stare", "stone", "store", "storm", "stomp", "snore", "snore", "snort",
    "snarl", "snarl", "snows", "snout", "swing", "swore", "sworn",

    "python", "rust", "ruby", "kotlin", "scala", "swift", "julia", "goat",
    "coal", "cola", "coal", "goal", "goals", "golf", "gore", "gone", "tone",
    "tango", "tangoes", "tangoed", "tang", "tangy", "tilt", "tilts", "tins",
    "into", "oint", "oints", "pith", "thin", "thing", "things", "thaw", "thaws",
    "thinly", "thorn", "thorns",

    "sort", "sorts", "salt", "sail", "sails", "salsa", "silo", "silos", "siloed",
    "alto", "altar", "altar", "alter", "alert", "alerts", "alerted",

    "iron", "irons", "irony", "ions", "loin", "loins", "loan", "loans", "luna",
    "lunar", "lure", "lures", "lured", "lute", "lutes",

    "java", "perl", "lisp", "pascal",

    # Add some more common words
    "tone", "tones", "tunes", "tune", "tuned", "tuner", "tug", "tugs",
    "tugs", "tang", "tangs", "torn", "torn", "tore", "torn", "tore", "torn",
    "ore", "ores", "earn", "earns", "earned", "earl", "earls",
    "farm", "farms", "farmer", "farmers", "frame", "frames", "framed",
    "form", "forms", "formed", "former", "forage", "forages", "forge", "forged",
    "range", "ranges", "rang", "rangy", "rangier", "anger", "angers", "angry",
    "anger", "anger", "anger", "anger", "anger", "anger",  # duplicates are harmless in a set

    "lion", "lions", "lioness", "loaner", "loaners", "lunar", "solar", "soar",
    "soars", "soared", "softer", "soften", "softened", "softener", "softer",
    "wear", "wears", "wean", "weans", "weaned", "warn", "warns", "warned",
    "earnest", "earn", "near", "nears", "nearer", "nearest", "ear", "ears",

    # Some longer random additions
    "software", "warfare", "angle", "angles", "angler", "anglers", "anger",
    "orange", "oranges", "forage", "strange", "stranger", "strangers",

    # Just to increase diversity
    "frost", "frosts", "frosted", "stone", "stones", "stoneware", "stare",
    "snare", "snares", "snared", "sinew", "sinews", "waste", "waster", "wasted",
    "waster", "wastes", "wasted", "waster", "waste", "wasted",
}
