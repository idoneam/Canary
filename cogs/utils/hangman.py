import pickle
from typing import List, Tuple, Dict
import requests
import discord
import random
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

LOSS_MISTAKES: int = len(HANG_LIST) - 1


def mk_animal_list() -> List[Tuple[str, str]]:
    animal_list_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_animal_names").content,
        "html.parser").find_all("tr")
    animal_list: List[Tuple[str, str]] = []
    for i in range(16, len(animal_list_soup)):
        curr_entry = animal_list_soup[i].find("td")
        if curr_entry:
            animal_name = curr_entry.find("a")
            img = BeautifulSoup(
                requests.get(
                    f"https://en.wikipedia.org{animal_name['href']}").content,
                "html.parser").find("img")
            if str(img["alt"]) == "Page semi-protected":
                img = BeautifulSoup(
                    requests.get(
                        f"https://en.wikipedia.org{animal_name['href']}").
                    content, "html.parser").find_all("img")[1]
            animal_list.append(
                (animal_name["title"].split(' (')[0], "https:" + img["src"]))
    return animal_list


def mk_country_list() -> List[Tuple[str, str]]:
    elem_list_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_sovereign_states").content,
        "html.parser").find("table", {
            "class": "sortable wikitable"
        }).find_all("tr")
    country_list: List[Tuple[str, str]] = []
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


def mk_element_list() -> List[Tuple[str, str]]:
    elem_list_soup = BeautifulSoup(
        requests.get(
            "https://en.wikipedia.org/wiki/List_of_chemical_elements").content,
        "html.parser").find_all("tr")
    elem_list: List[Tuple[str, str]] = []
    for i in range(4, 118):
        curr_entry = elem_list_soup[i].find_all("td")
        elem_name_entry = curr_entry[2].find("a")
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
            (f"{elem_name_entry.contents[0]} ({curr_entry[1].contents[0]})",
             elem_img))
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
            kino_list.append((str(kino_elem.contents[0]), kino_img))
    return kino_list


def mk_hm_embed_up_fn(category_name, word, lowered_word, not_guessed,
                      incorrect_guesses):
    field_name: str = f"hangman (category: {category_name})"
    first_line: str = " ".join(
        char if lowered_char not in not_guessed else "_"
        for char, lowered_char in zip(word, lowered_word))
    last_line: str = "incorrect guesses: "
    player_msg_list: List[str] = []
    num_mistakes: int = 0
    embed = discord.Embed(colour=random.randint(0, 16777215))
    embed.add_field(
        name=field_name,
        value=f"`{first_line}`\n```{HANG_LIST[num_mistakes]}```").set_footer(
            text=last_line)

    def heuf(new_msg,
             *,
             incorrect_guess: bool = False,
             correct_guess: bool = False,
             img_url: str = None) -> bool:
        nonlocal embed
        nonlocal player_msg_list

        player_msg_list.append(new_msg)
        player_msg_list = player_msg_list[-3:]

        if incorrect_guess:
            nonlocal last_line
            nonlocal num_mistakes
            last_line = f"""incorrect guesses: {", ".join("'"+char+"'" for char in sorted(incorrect_guesses))}"""
            num_mistakes += 1
            embed.set_footer(text=last_line)
        if correct_guess:
            nonlocal first_line
            first_line = " ".join(
                char if lowered_char not in not_guessed else "_"
                for char, lowered_char in zip(word, lowered_word))

        if img_url:
            embed.set_image(url=img_url)

        embed.set_field_at(0,
                           name=field_name,
                           value="`{0}`\n```{1}```\n{2}".format(
                               first_line, HANG_LIST[num_mistakes],
                               "\n".join(player_msg_list)))

        return bool(not_guessed) and num_mistakes < LOSS_MISTAKES

    return heuf, embed


def mk_hangman_dict(file_name) -> Dict[str, List[Tuple[str, str]]]:
    with open(f"pickles/premade/{file_name}.obj", "wb") as dump_file:
        pickle.dump(
            {
                "animal": (mk_animal_list(), "animals"),
                "country": (mk_country_list(), "country names"),
                "element": (mk_element_list(), "elements"),
                "movie": (mk_movie_list(), "movies")
            }, dump_file)


if __name__ == "__main__":
    mk_hangman_dict("hangman_dict")
