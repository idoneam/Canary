import re
import pickle
from typing import List
import requests
from bs4 import BeautifulSoup

HANG_LIST: List[str] = [
    r"""  +---+
  |   |
      |
      |
      |
      |
========""", r"""
  +---+
  |   |
  O   |
      |
      |
      |
========""", r"""  +---+
  |   |
  O   |
  |   |
      |
      |
========""", r"""  +---+
  |   |
  O   |
 /|   |
      |
      |
========""", r"""  +---+
  |   |
  O   |
 /|\  |
      |
      |
========""", r"""  +---+
  |   |
  O   |
 /|\  |
 /    |
      |
========""", r"""  +---+
  |   |
  O   |
 /|\  |
 / \  |
      |
========"""
]

MAX_GUESSES: int = len(HANG_LIST)


def mk_word_dict(file_name):
    link_list = [
        elem for elem in BeautifulSoup(
            requests.get("https://www.enchantedlearning.com/wordlist/").
            content, "html.parser").find_all("table")[-6].find_all(
                "a", {"target": "_top"})
        if re.search(r"^/wordlist/([a-z]*)\.shtml$", elem["href"])
    ]
    word_dict = {}
    for link in link_list:
        link_name = re.findall(r"^/wordlist/([a-z]*)\.shtml$", link["href"])[0]
        word_list = [
            word.text.lower() for word in BeautifulSoup(
                requests.get(
                    f"https://www.enchantedlearning.com/{link['href']}").
                content, "html.parser").find_all("div",
                                                 {"class": "wordlist-item"})
        ]
        word_dict[link_name] = (word_list,
                                re.sub(r"[^a-z\",'/ ]", "",
                                       link.contents[0].lower()))
    with open(f"{file_name}.pickle", "wb") as dump_file:
        pickle.dump(word_dict, dump_file)


if __name__ == "__main__":
    mk_word_dict("hangman_dict")
