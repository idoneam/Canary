import sys, random


# Credit to lazho for this function
def auto_incorrect(input_str):
    chance = 99
    input_str = input_str.split()

    specialCases = {
        "your": "you're",
        "you're": "your",
        "its": "it's",
        "it's": "its",
        "their": "they're",
        "they're": "there",
        "there": "their",
        "lose": "loose",
        "loose": "lose",
        "effect": "affect",
        "affect": "effect",
        "definitely": "definately",
        "weather": "whether",
        "whether": "weather",
        "then": "than",
        "an": "a",
        "the": "teh",
        "like": "liek"
    }

    outputStr = ""

    # Given string s and index i, it swaps s[i] and s[i+1] and returns
    def swap(s, i):
        si = s[i]
        sj = s[i + 1]
        s = s[:i] + sj + si + s[i + 2:]
        return s

    # Given string s and index i, it omits the i-th character.
    def omit(s, i):
        return s[:i] + s[i + 1:]

    for w in input_str:
        # Idiots don't use shift or capslock
        w = w.lower()
        # If jackpot
        if random.randrange(100) < chance:
            # Special cases get priority
            if w in specialCases:
                outputStr = outputStr + specialCases[w]
            # Words less than 3 letters can't stand omit or swap
            elif len(w) >= 3:
                # Decide a random index
                i = random.randrange(len(w) - 1)
                # 50/50 chance between omission and swap
                if random.randrange(2) == 1:
                    outputStr = outputStr + swap(w, i)
                else:
                    outputStr = outputStr + omit(w, i)
            # Leave short words be
            else:
                outputStr = outputStr + w
        else:
            outputStr = outputStr + w
        outputStr = outputStr + " "

    return outputStr