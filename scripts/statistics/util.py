"""Helper functions for corpus statistics."""


def roman_to_int(roman: str) -> int:
    """Convert a Roman numeral string to int."""
    numeral_value = {
        "I": 1,
        "J": 1,
        "V": 5,
        "X": 10,
        "L": 50,
        "C": 100,
        "D": 500,
        "M": 1000,
    }
    total = 0
    intermediate = 0
    last_value = float("inf")
    for c in roman.upper():
        if c not in numeral_value:
            continue
        value = numeral_value.get(c, 0)
        # example: IX = -1 + 10 = 9
        if last_value < value:
            # exception: C leads to multiplication by 100
            # if our total is less than 1000
            if c == "C" and total < 1000:
                total += intermediate
                total *= 100
                intermediate = 0
            else:
                # subtraction mode
                intermediate = value - intermediate
        elif last_value == value:
            # same value, just add
            intermediate += value
        else:
            # addition mode ended, add intermediate to total
            total += intermediate
            intermediate = value
        last_value = value
    total += intermediate
    return total


def to_main_pos(pos: str) -> str:
    """
    Strip features from POS tag, keeping only the main tag(s).
    Handles compound tags joined by `|` and `+`.

    Example:
        ADP()+NOU-C()|PD()+NOU-C() -> ADP+NOU-C|PD+NOU-C
    """
    return "|".join(
        "+".join(p.split("(")[0] for p in option_pos.split("+"))
        for option_pos in pos.split("|")
    )
