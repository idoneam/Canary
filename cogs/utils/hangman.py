# Copyright (C) idoneam (2016-2021)
#
# This file is part of Canary
#
# Canary is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Canary is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Canary. If not, see <https://www.gnu.org/licenses/>.
import pickle
from typing import Optional
import requests
import discord
import random
from bs4 import BeautifulSoup

HANG_LIST: list[str] = [
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


def mk_animal_list() -> list[tuple[str, str]]:
    animal_list_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_animal_names").content,
        "html.parser").find_all("tr")
    animal_list: list[tuple[str, str]] = []
    for i in range(16, len(animal_list_soup)):
        curr_entry = animal_list_soup[i].find("td")
        if curr_entry is None:
            continue
        animal_name = curr_entry.find("a")
        animal_soup = BeautifulSoup(
            requests.get(
                f"https://en.wikipedia.org{animal_name['href']}").content,
            "html.parser")
        img_list = animal_soup.find_all("img")
        img_index = 0
        while str(img_list[img_index]["src"]).endswith(".svg.png"):
            img_index += 1
        animal_list.append((animal_name["title"].split(' (')[0],
                            "https:" + img_list[img_index]["src"]))
    return animal_list


def mk_country_list() -> list[tuple[str, str]]:
    elem_list_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_sovereign_states").content,
        "html.parser").find("table", {
            "class": "sortable wikitable"
        }).find_all("tr")
    country_list: list[tuple[str, str]] = []
    for i in range(4, 241):
        curr_entry = elem_list_soup[i].find_all("td")
        if len(curr_entry) != 4 or i in (227, 228, 229):
            continue
        country_name_entry = curr_entry[0].find("a")
        country_name = str(country_name_entry.contents[0])
        if "," in country_name:
            comma_index = country_name.index(",")
            country_name = f"{country_name[comma_index+2:]} {country_name[:comma_index]}"
        country_list.append((country_name, "https:" + BeautifulSoup(
            requests.get(
                f"https://en.wikipedia.org{country_name_entry['href']}").
            content, "html.parser").find("table", {
                "class": "infobox"
            }).find("a", {
                "class": "image"
            }).find("img")["src"]))
    return country_list


def mk_element_list() -> list[tuple[str, Optional[str]]]:
    elem_list_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_chemical_elements").content,
        "html.parser").find_all("tr")
    elem_list: list[tuple[str, Optional[str]]] = []
    for i in range(4, 118):
        curr_entry = elem_list_soup[i].find_all("td")
        elem_name_entry = curr_entry[2].find("a")
        try:
            elem_img: Optional[str] = "https:" + BeautifulSoup(
                requests.get(
                    f"https://en.wikipedia.org{elem_name_entry['href']}").
                content, "html.parser").find("table", {
                    "class": "infobox"
                }).find("a").find("img")["src"]
        except TypeError:
            elem_img = None
        elem_list.append((str(elem_name_entry.contents[0]), elem_img))
    return elem_list


def mk_movie_list() -> list[tuple[str, str]]:
    kino_elem_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_years_in_film").content,
        "html.parser").find_all("i")
    kino_list: list[tuple[str, str]] = []
    for i in range(195, len(kino_elem_soup)):
        kino_elem = kino_elem_soup[i].find("a")
        if kino_elem:
            try:
                kino_img = "https:" + BeautifulSoup(
                    requests.get(f"https://en.wikipedia.org{kino_elem['href']}"
                                 ).content, "html.parser").find(
                                     "table", {
                                         "class": "infobox"
                                     }).find("a", {
                                         "class": "image"
                                     }).find("img")["src"]
            except AttributeError:
                continue
            kino_list.append((str(kino_elem.contents[0]), kino_img))
    return kino_list


class HangmanState:
    def __init__(self, category_name: str,
                 word_list: list[tuple[str, Optional[str]]]):
        self.word, self.img = random.choice(word_list)
        self.lword = self.word.lower()
        self.not_guessed: set[str] = set(
            char for char in self.lword
            if char in "abcdefghijklmnopqrstuvwxyz")
        self.previous_guesses: set[str] = set()
        self.field_name: str = f"hangman (category: {category_name})"
        self.first_line: str = " ".join(
            char if lowered_char not in self.not_guessed else "_"
            for char, lowered_char in zip(self.word, self.lword))
        self.last_line: str = "previous guesses: "
        self.player_msg_list: list[str] = []
        self.num_mistakes: int = 0
        self.embed = discord.Embed(
            colour=random.randint(0, 0xFFFFFF)
        ).add_field(
            name=self.field_name,
            value=f"`{self.first_line}`\n```{HANG_LIST[self.num_mistakes]}```"
        ).set_footer(text=self.last_line)

    def full(self):
        self.first_line = " ".join(self.word)
        return len(self.not_guessed) > (len(set(self.lword)) / 2.5)

    def correct(self, guess: str) -> bool:
        self.previous_guesses.add(guess)
        self.not_guessed.remove(guess)
        self.last_line = f"""previous guesses: '{"', '".join(sorted(self.previous_guesses))}'"""
        self.embed.set_footer(text=self.last_line)
        self.first_line = " ".join(
            char if lowered_char not in self.not_guessed else "_"
            for char, lowered_char in zip(self.word, self.lword))

        return bool(self.not_guessed)

    def mistake(self, guess: str) -> bool:
        self.previous_guesses.add(guess)
        self.last_line = f"""previous guesses: '{"', '".join(sorted(self.previous_guesses))}'"""
        self.num_mistakes += 1
        self.embed.set_footer(text=self.last_line)

        return self.num_mistakes < 6

    def add_msg(self, new_msg):
        self.player_msg_list.append(new_msg)
        self.player_msg_list = self.player_msg_list[-3:]
        self.embed.set_field_at(0,
                                name=self.field_name,
                                value="`{0}`\n```{1}```\n{2}".format(
                                    self.first_line,
                                    HANG_LIST[self.num_mistakes],
                                    "\n".join(self.player_msg_list)))


def mk_hangman_dict(file_name):
    with open(f"data/premade/{file_name}.obj", "wb") as dump_file:
        pickle.dump(
            {
                "animal": (mk_animal_list(), "animals"),
                "country": (mk_country_list(), "country names"),
                "element": (mk_element_list(), "elements"),
                "movie": (mk_movie_list(), "movies")
            }, dump_file)


if __name__ == "__main__":
    mk_hangman_dict("hangman_dict")
