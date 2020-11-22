from re import findall, search, sub
from pickle import dump
from requests import get
from bs4 import BeautifulSoup

HANG_LIST = [
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


def mk_word_dict(file_name):
    link_list = [
        elem for elem in BeautifulSoup(
            get("https://www.enchantedlearning.com/wordlist/").content,
            "html.parser").find_all("table")[-6].find_all(
                "a", {"target": "_top"})
        if search(r"^/wordlist/([a-z]*)\.shtml$", elem["href"])
    ]
    word_dict = {}
    for link in link_list:
        link_name = findall(r"^/wordlist/([a-z]*)\.shtml$", link["href"])[0]
        word_list = [
            word.text.lower() for word in BeautifulSoup(
                get(f"https://www.enchantedlearning.com/{link['href']}").
                content, "html.parser").find_all("div",
                                                 {"class": "wordlist-item"})
        ]
        word_dict[link_name] = (word_list,
                                sub(r"[^a-z\",'/ ]", "",
                                    link.contents[0].lower()))
    with open(f"{file_name}.pickle", "wb") as dump_file:
        dump(word_dict, dump_file)


if __name__ == "__main__":
    mk_word_dict("hangman_dict")
