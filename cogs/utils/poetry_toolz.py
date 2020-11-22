from random import choice
from typing import Dict, List, Tuple
from re import sub, findall, fullmatch
from pickle import dump


def make_rev_gen_dict(ord_word_list: List[str]) -> Dict[str, List[str]]:
    """
    Returns a dict containing as keys words and as values a list of words
    that preceded instances of the key word.
    Takes as argument an ordered list of words from some text.
    """
    prv_word_map: Dict[str, List[str]] = {}
    for index, word in enumerate(ord_word_list):
        if word not in prv_word_map:
            prv_word_map[word] = []
        if index > 0:
            prv_word_map[word].append(ord_word_list[index - 1])
    return prv_word_map


def make_rhyme_dict(word_list: List[str],
                    end_len: int = 4) -> Dict[str, List[str]]:
    """
    Returns a dict containing as keys word endings and as values
    a list of words that match that ending.
    Takes as argument a list of words from some text, as well
    as an optional integer, indicating the length of the end slice.
    """
    rhyme_dict: Dict[str, List[str]] = {}
    for word in word_list:
        stripped_word: str = strip_non_alph_and_lower(word)
        end_slice: str = stripped_word[end_len:]
        if end_slice not in rhyme_dict:
            rhyme_dict[end_slice] = []
        if stripped_word not in rhyme_dict[end_slice]:
            rhyme_dict[end_slice].append(stripped_word)
    return rhyme_dict


def strip_non_alph_and_lower(inp_string: str) -> str:
    return sub("[^a-z]", "", inp_string.lower())


def syll_count(word_list: List[str]) -> int:
    """
    Returns the total amount of syllables in each word in the list of words
    supplied as argument.
    Takes as argument a list of strings (words).
    """
    total_syll_count: int = 0
    for word in word_list:
        curr_word_syll_count: int = 0
        stripped_word: str = strip_non_alph_and_lower(word)
        for index, char in enumerate(stripped_word):
            if char in "eyouioa" and (
                    not (index > 0 and stripped_word[index - 1] in "euioa")
            ) and (not (char == "e" and index == len(stripped_word) - 1)):
                curr_word_syll_count += 1
        total_syll_count += max(1, curr_word_syll_count)
    return total_syll_count


def parse_poem_config(config_str: str) -> List[Tuple[str, int]]:
    """
    Parses a string containing representing a poem configuration, returning
    a valid configuration used for poem generation.
    Raises ValueError in cases where supplied string is invalid.
    Valid config strings match the following regex: ^(?:[a-zA-Z][0-9]+ )*[a-zA-Z][0-9]+$
    """
    if fullmatch(r"(?:[a-zA-Z][0-9]+ )*[a-zA-Z][0-9]+", config_str) is None:
        raise ValueError
    config_list: List[Tuple[str, int]] = []
    for line_config in findall(r"[a-zA-Z][0-9]+", config_str):
        line_sylls: int = int(line_config[1:])
        if line_sylls == 0:
            raise ValueError
        config_list.append((line_config[0], line_sylls))
    return config_list


class RevTextGen():
    def __init__(self, word_dict: Dict[str, List[str]]):
        self.word_dict = word_dict
        self.word_list = list(word_dict.keys())

    def get_prev_word(self, seed: str) -> Tuple[str, bool]:
        if seed in self.word_dict:
            return choice(self.word_dict[seed]), True
        return choice(self.word_list), False

    def rev_gen(self, text_len: int, strict_gen: bool = True):
        curr_word: str = choice(self.word_list)
        gen_words: List[str] = [curr_word]
        if strict_gen:
            do_loop: bool = False
            while True:
                for _ in range(text_len - 1):
                    curr_word, good_gen = self.get_prev_word(curr_word)
                    if good_gen:
                        gen_words.append(curr_word)
                    else:
                        do_loop = True
                        break
                if not do_loop:
                    break
        else:
            for _ in range(text_len - 1):
                curr_word, _ = self.get_prev_word(curr_word)
                gen_words.append(curr_word)
        return gen_words[::-1]


class PoetryGen(RevTextGen):
    def __init__(self, word_dict: Dict[str, List[str]],
                 rhyme_dict: Dict[str, List[str]]):
        super().__init__(word_dict)
        self.rhyme_dict = rhyme_dict
        self.rhyme_list = list(rhyme_dict.keys())

    def mk_poem(self,
                poem_config: List[Tuple[str, int]],
                strict_gen: bool = True,
                max_attempts: int = 3,
                min_rhyme_mult: int = 5) -> List[str]:
        poem_list = [""] * len(poem_config)
        rhyme_pos_table: Dict[str, List[int]] = {}
        for index, elem in enumerate(poem_config):
            if elem[0] not in rhyme_pos_table:
                rhyme_pos_table[elem[0]] = []
            rhyme_pos_table[elem[0]].append(index)
        for _, rhyme_pos_list in rhyme_pos_table.items():
            line_amount = len(rhyme_pos_list)
            gen_sucess: List[bool] = [False] * line_amount
            group_list: List[str] = []
            while False in gen_sucess:
                gen_sucess = [False] * line_amount
                group_list = []
                group_endings = self.rhyme_dict[choice(self.rhyme_list)]
                if line_amount > 1:
                    while len(group_endings) < min_rhyme_mult * line_amount:
                        group_endings = self.rhyme_dict[choice(
                            self.rhyme_list)]
                for index, pos in enumerate(rhyme_pos_list):
                    line_sylls = poem_config[pos][1]
                    curr_line: List[str] = [choice(group_endings)]
                    while syll_count(curr_line) < line_sylls:
                        curr_word, good_gen = self.get_prev_word(curr_line[-1])
                        if strict_gen and not good_gen:
                            break
                        curr_line.append(curr_word)
                    attempt_counter = 0
                    while syll_count(
                            curr_line
                    ) != line_sylls and attempt_counter < max_attempts:
                        curr_line.pop()
                        if len(curr_line) == 0:
                            curr_line = [choice(group_endings)]
                        else:
                            curr_word, good_gen = self.get_prev_word(
                                curr_line[-1])
                            if strict_gen and not good_gen:
                                break
                            curr_line.append(curr_word)
                        attempt_counter += 1
                    if syll_count(curr_line) == line_sylls:
                        gen_sucess[index] = True
                        group_list.append(" ".join(curr_line[::-1]))
            for index, pos in enumerate(rhyme_pos_list):
                poem_list[pos] = group_list[index]
        return poem_list


if __name__ == "__main__":
    with open("__GITIGNOREME__megasource.txt", "r") as txt_f:
        word_arr = txt_f.read().split()
        markov, rhyme_map = make_rev_gen_dict(word_arr), make_rhyme_dict(
            word_arr)
        with open("rev_markov.pickle", "wb") as m_file:
            dump(markov, m_file)
        with open("rhyme_dict.pickle", "wb") as r_file:
            dump(rhyme_map, r_file)
