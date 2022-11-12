import random

__all__ = ["auto_incorrect"]


def _swap(s: str, i: int):
    """
    Given string s and index i, it swaps s[i] and s[i+1] and returns
    By @lazho
    """
    si = s[i]
    sj = s[i + 1]
    s = s[:i] + sj + si + s[i + 2 :]
    return s


def _repeat(s: str, i: int):
    """
    By @lazho
    """
    return s[:i] + s[i] + s[i:]


def _omit(s: str, i: int):
    """
    Given string s and index i, it omits the i-th character.
    By @lazho
    """
    return s[:i] + s[i + 1 :]


REPLACE_CASES: dict[str, str] = {
    "your": "you're",
    "you're": "your",
    "its": "it's",
    "it's": "its",
    "their": "theyre",
    "they're": "there",
    "there": "their",
    "lose": "loose",
    "loose": "lose",
    "chose": "choose",
    "choose": "chose",
    "effect": "affect",
    "affect": "effect",
    "definitely": "definately",
    "weather": "whether",
    "whether": "weather",
    "then": "than",
    "than": "then",
    "until": "untill",
    "an": "a",
    "the": "teh",
    "like": "liek",
    "fucking": "ducking",
    "sick": "dick",
    "gum": "cum",
}


def auto_incorrect(input_str: str):
    """
    By @lazho
    """
    chance = 99
    input_split: list[str] = input_str.split()

    output_str = ""

    for w in input_split:
        output_str += " "

        # Idiots don't use shift or capslock
        w = w.lower()

        # Rare chance of not doing anything
        if random.randrange(100) >= chance:
            output_str += w
            continue

        # Otherwise, jackpot

        # Special cases get priority
        if w in REPLACE_CASES:
            output_str += REPLACE_CASES[w]
        # Words less than 3 letters can't stand omit or swap
        elif len(w) >= 3:
            # Look for occurrence of "ie" and flip it if present
            i = w.find("ie")
            if i != -1:
                w = _swap(w, i)

            # Decide a random index
            i = random.randrange(len(w) - 1)

            # 1/3 chance between swap, omission, and repetition
            output_str += random.choice((_swap, _omit, _repeat))(w, i)
        # Leave short words be
        else:
            output_str += w

    return output_str.lstrip()
