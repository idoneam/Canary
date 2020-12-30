# Copyright (C) idoneam (2016-2020)
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

import random
import regex as re

# Written by @le-potate

# A "string with placeholders" is a simple string like
# "hi %user%, this is the channel %channel%", which
# contains placeholders, here %user% and %channel%
# (See the PString class docstring to see available placeholders.)

# A p-string is composed of a "string with placeholders",
# and values for these placeholders. Printing a p-string will
# fill the string with these values.

# This utility is mostly used in cases where messages have to be set
# from the server
# For a simple example, a moderator might want to set the goodbye message
# to be one of "bye @someone" or "ciao @someone". They would thus set the
# goodbye_message to "%[bye, ciao]% %user%" from the server.
# Then, when a user leaves,
# `await ctx.send PString(goodbye_message, user=ctx.author)` would be used,
# which will send "bye @someone" or "ciao @someone"

# Another, more complex use is groups placeholders, which is most often used
# as part of input/output patterns. For example, there could be
# a custom reaction that takes a prompt "I like %1%" and sends a response
# "I don't like %1%". Then, if someone writes "I like apples" in the server,
# "I don't like apples" would be sent. This is done by making a
# PStringEncodings object with a list of input "strings with placeholders"
# and a list of output "strings with placeholders" (see PStringEncodings
# docstring). Calling PStringEncodings.parser on the content of a message will
# then detect if the message corresponds to some input
# "strings with placeholders", choose a random one, and create a filled
# output p-string with its corresponding output "string with placeholders".


def _convert_choice_list(choice_list_string, to_pattern_str=False, level=0):
    """
    Takes a string with choice list placeholders and converts them to
    either a string where the choices are made (default)
    or the regex pattern string (if to_pattern_str=True)

    Example:
    choice_list_string: "%[hi, hello %[world, you]%]% %[!,?]%"
    By default, the function would return something like
    "hi !" or "hello world ?" or "hello you !"
    If to_pattern_str=True, it will instead return
    "(hi|hello (world, you)) (!|?)"
    """
    # find the last starting position %[ and the first ]% after it
    last_start_pos = choice_list_string.rfind("%[")
    first_end_pos_after = choice_list_string.find("]%", last_start_pos + 1)
    # if either isn't found, return the input string (there's nothing to
    # convert in it)
    if last_start_pos == -1 or first_end_pos_after == -1:
        return choice_list_string
    # otherwise, split the content between %[ and ]% to get the list of choices
    # content is separated by commas, except when they are inside quotes
    choice_list_matches_iter = re.finditer(
        r'(?:^"?|, ?"?)\K(?:(?<=").+?(?=")|[^ ,][^,]*)',
        choice_list_string[last_start_pos + 2:first_end_pos_after])
    choice_list = [
        choice_match.group() for choice_match in choice_list_matches_iter
    ]
    # if to_pattern_str, any of these choices can match, thus this is
    # a regex pattern string of alternatives
    if to_pattern_str:
        choice = f"(?:{'|'.join(choice_list)})"
    # otherwise, pick a random element of the list
    else:
        choice = random.choice(choice_list)
    # replace everything between the %[ and ]% by the choice that was chosen
    # or the pattern, and return a call to the function itself since there
    # might still be pairs of %[ and ]% remaining
    choice_list_string = (choice_list_string[:last_start_pos] + choice +
                          choice_list_string[first_end_pos_after + 2:])
    return _convert_choice_list(choice_list_string, level=level + 1)


def _get_pattern_from_string(string, anywhere=False):
    """
    Takes a string with placeholders and returns the regex pattern
    By default, the pattern has start and end tokens, i.e. a string will have
    to match the pattern exactly
    If anywhere = True, the pattern doesn't have start/end tokens, i.e.
    the pattern can be contained anywhere in the string
    """
    # for every %1%, %2%, etc... up to %9%, replace them by regex
    # if-statement that will create named capture groups
    # g1, g2, etc.. up to g9 on their first occurrence, and back-reference
    # them on subsequent occurrences
    for i in range(1, 10):
        string = re.sub(f"%{i}%", f"(?(g{i})(?P=g{i})|(?P<g{i}>.+))", string)
    # convert the choice lists to patterns
    string = _convert_choice_list(string, to_pattern_str=True)
    # if the string must be exactly the pattern, add start and end tokens
    if not anywhere:
        string = f"^{string}$"
    # compile the regex pattern and return
    return re.compile(string)


class PString:
    def __init__(self, string, user=None, channel=None, groups=None):
        """
        A p-string is composed of a string with placeholders in it,
        and values for these placeholders. Printing a p-string will
        fill the string with these values.

        Arguments:
        - string: the string with placeholders

        - user (placeholder: %user%): should generally be used with something
        like ctx.author.mention but can be used with any string

        - channel (placeholder: %channel%): should generally be used with
        something like ctx.channel but can be used with any string

        - groups (placeholder: %1%, %2%, etc... up to %9%): for example, if
         there is a p-string with string "%1% likes %2%" and
         groups=["He", "apples"], printing the p-string will return
         "He likes apples"

        Other placeholder (not an argument):
        - choice list (%[a,b]%): a random value will be chosen from the list
        (here, either a or b). The values themselves can be choice lists
        (ex: %[hi, hello %[world, you]%]%) will print either
        "hi", "hello world" or "hello you"
        """
        self.string = string
        self.user = user
        self.channel = channel
        self.groups = groups

    def __str__(self):
        filled_string = self.string
        # replace the %user% and %channel% placeholders by their values
        if self.user:
            filled_string = re.sub("%user%", self.user, filled_string)
        if self.channel:
            filled_string = re.sub("%channel%", self.user, filled_string)
        # for every group placeholder, replace them by their value
        if self.groups:
            for i, group in enumerate(self.groups, 1):
                filled_string = re.sub(f"%{i}%", group, filled_string)
        # convert the choice lists
        filled_string = _convert_choice_list(filled_string)
        return filled_string


class PStringEncodings:
    def __init__(self, input_strings, output_strings, anywhere_values):
        """
        Used to encode a list of input strings with placeholders
        and a list of output strings with placeholders to
        a list of input regex patterns and output p_strings pairings.
        The parser method is then used with any string to return either
        None if it matches no input pattern, or a random corresponding filled
        output p-string if it matches some input patterns.

        Arguments:
        -input_strings: a list of input strings with placeholders. Note that
        this cannot include %user% and %channel% (these aren't values users
        can use themselves, they are more "system values"-like,
         usually getting replaced by some context values)

        -output_strings: a list of corresponding output strings with
        placeholders, must be the same length as input_strings

        -anywhere_values: boolean or list of booleans.
        If False, the pattern cannot be anywhere in the content for any
        input_strings, i.e. the input_strings will have to match exactly
        If True, the content can contain the input string pattern anywhere
        for all input_strings.
        If a list of booleans, an input string at a certain index can either
        be included anywhere in the content or not depending on if the
        corresponding anywhere value at this index is True or False.
        Must be the same length as input_strings
        """
        # if a boolean is given for anywhere_values, then for every
        # input/output pair the anywhere value is this boolean,
        # that is we create a list anywhere_values of the same
        # length filled with this bool
        if isinstance(anywhere_values, bool):
            anywhere_values = [anywhere_values] * len(input_strings)
        # the lists must all be the same length
        if not (len(input_strings) == len(output_strings) ==
                len(anywhere_values)):
            raise ValueError("input_strings, output_strings, "
                             "and anywhere_values (if not bool) "
                             "should be the same length")
        # get the list of input regex patterns
        self.patterns = [
            _get_pattern_from_string(input_string, anywhere=anywhere)
            for input_string, anywhere in zip(input_strings, anywhere_values)
        ]
        # the patterns_string is a big regex string that will be used to see
        # if there is any match in any p-strings before actually looping
        # (to save time)
        patterns_strings_list = [pattern.pattern for pattern in self.patterns]
        self.patterns_string = f"({'|'.join(patterns_strings_list)})"
        # get the list of pairings of input regex pattern and output p-strings
        self.patterns_and_p_strings = [
            (pattern, PString(output_string))
            for output_string, pattern in zip(output_strings, self.patterns)
        ]

    def parser(self, content, user=None, channel=None):
        """
        Return either None if the content matches no input pattern,
        or a random corresponding filled output p-string if it matches some
        input patterns. user and channel arguments can be provided if
        they might be needed in some of the output patterns.

        Arguments:
        -content: any string

        - user: should generally be used with something
        like ctx.author.mention but can be used with any string

        - channel: should generally be used with
        something like ctx.channel but can be used with any string
        """
        # first search the big patterns_string to see if anything matches
        if re.search(self.patterns_string, content):
            # choose a random iterator of match objects from those of all
            # the matching input regex pattern (i.e. we are choosing
            # which corresponding pattern to use)
            match_iter = random.choice([
                (pattern.finditer(content), p_string)
                for (pattern, p_string) in self.patterns_and_p_strings
                if pattern.search(content) is not None
            ])
            # for that random iterator of match objects choose a random
            # iteration (i.e. we are choosing which corresponding match
            # of this pattern in the content to use)
            match = (random.choice([match for match in match_iter[0]]),
                     match_iter[1])
            # fill the corresponding p-strings with the capture groups,
            # the user info and the channel info
            match[1].groups = [
                group for group in match[0].groups() if group is not None
            ]
            match[1].user = user
            match[1].channel = channel
            return match[1]
