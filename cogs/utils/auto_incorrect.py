import sys, random


# Credit to lazho for this function
def auto_incorrect(input_str):
    chance = 99
    input_str = input_str.split()

    special_cases = {
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
        "gum": "cum"
    }

    output_str = ""

    # Given string s and index i, it swaps s[i] and s[i+1] and returns
    def swap(s, i):
        si = s[i]
        sj = s[i + 1]
        s = s[:i] + sj + si + s[i + 2:]
        return s

    def repeat(s, i):
        return s[:i] + s[i] + s[i:]

    # Given string s and index i, it omits the i-th character.
    def omit(s, i):
        return s[:i] + s[i + 1:]

    for w in input_str:
        # Idiots don't use shift or capslock
        w = w.lower()
        # If jackpot
        if random.randrange(100) < chance:
            # Special cases get priority
            if w in special_cases:
                output_str = output_str + special_cases[w]
            # Words less than 3 letters can't stand omit or swap
            elif len(w) >= 3:
                # Look for occurence of "ie" and flip it if present
                i = w.find("ie")
                if i != -1:
                    w = w[:i] + "ei" + w[i + 2:]

                # Decide a random index
                i = random.randrange(len(w) - 1)
                # 50/50 chance between omission and swap
                choice = random.randrange(3)
                if choice == 0:
                    output_str = output_str + swap(w, i)
                elif choice == 1:
                    output_str = output_str + omit(w, i)
                elif choice == 2:
                    output_str = output_str + repeat(w, i)
            # Leave short words be
            else:
                output_str = output_str + w
        else:
            output_str = output_str + w
        output_str = output_str + " "

    return output_str