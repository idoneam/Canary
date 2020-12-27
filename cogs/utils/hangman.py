import re
import pickle
from typing import List, Tuple, Dict
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

MAX_GUESSES: int = len(HANG_LIST) - 1


def mk_animal_list() -> List[Tuple[str, str]]:
    return None


def mk_mythical_list() -> List[Tuple[str, str]]:
    return None


def mk_country_list() -> List[Tuple[str, str]]:
    elem_list_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_sovereign_states").content,
        "html.parser").find("table", {
            "class": "sortable wikitable"
        }).find_all("tr")
    country_list: List[Tuple[str, str]] = []
    for i in range(4, 241):
        curr_table = elem_list_soup[i].find_all("td")
        if len(curr_table) != 4 or i in (227, 228, 229):
            continue
        country_name_entry = curr_table[0].find("a")
        country_name = str(country_name_entry.contents[0]).lower()
        if "," in country_name:
            comma_index = country_name.index(",")
            country_name = f"{country_name[comma_index+2:]} {country_name[:comma_index]}"
        country_list.append(
            (country_name,
             "https:" + BeautifulSoup(
                 requests.get(
                     f"https://en.wikipedia.org{country_name_entry['href']}").
                 content, "html.parser").find("table", {
                     "class": "infobox"
                 }).find("a", {
                     "class": "image"
                 }).find("img")["src"]))
    return country_list


def mk_element_list() -> List[Tuple[str, str]]:
    elem_list_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_chemical_elements").content,
        "html.parser").find_all("tr")
    elem_list: List[Tuple[str, str]] = []
    for i in range(4, 118):
        curr_table = elem_list_soup[i].find_all("td")
        elem_name_entry = curr_table[2].find("a")
        try:
            elem_img = "https:" + BeautifulSoup(
                requests.get(
                    f"https://en.wikipedia.org{elem_name_entry['href']}").
                content, "html.parser").find("table", {
                    "class": "infobox"
                }).find("a").find("img")["src"]
        except TypeError:
            elem_img = None
        elem_list.append(
            (f"{elem_name_entry.contents[0]} ({curr_table[1].contents[0]})".
             lower(), elem_img))
    return elem_list


def mk_movie_list() -> List[Tuple[str, str]]:
    kino_elem_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_years_in_film").content,
        "html.parser").find_all("i")
    kino_list: List[Tuple[str, str]] = []
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
            kino_list.append((str(kino_elem.contents[0]).lower(), kino_img))
    return kino_list


def mk_hangman_dict(file_name) -> Dict[str, List[Tuple[str, str]]]:
    with open(f"pickles/premade/{file_name}.obj", "wb") as dump_file:
        pickle.dump(
            {
                #"animal": (mk_animal_list(), "animals"),
                #"myth": (mk_mythical_list(), "mythical creatures"),
                "country": (mk_country_list(), "country names"),
                "element": (mk_element_list(), "elements"),
                "movie": (mk_movie_list(), "movies")
            }, dump_file)


if __name__ == "__main__":
    mk_hangman_dict("hangman_dict")
