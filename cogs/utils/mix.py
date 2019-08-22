import random


def generate_mix(string: str) -> str:
    return "".join([(c.upper() if random.randint(0, 1) else c.lower())
                    for c in string])
