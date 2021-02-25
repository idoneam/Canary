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

from discord.ext import commands

# Written by @le-potate


class ArgConverter:
    """
    The ArgConverter object holds a dictionary used by the convert function
    to pseudo-typecheck and cast a list of arguments using the given
    converters (see below for explanation), regardless of order
    (except if multiple converters match an argument, see below).
    When converting, converters are used at most once.
    Raises commands.BadArgument if not all required arguments were given,
    and if it was not possible to convert every given argument.

    Parameter: A dictionary where keys are a string representing the variable
    names, and values are a tuple with the converter and the default value.
    If no default value is given, the variable is required.

    The dictionary should be ordered, that is either an OrderedDict or
    any dictionary in Python 3.7+. This is because if there are multiple
    converters that match with the same argument during the convert function,
    the first one in the dictionary is used. Thus, unexpected results could
    happen in this case if the dict is unordered. If the dict is ordered,
    carefully think about how you order the keys, as this could also lead to
    unexpected results: for example, order doesn't matter if the two
    converters that can match an arg are to catch two discord users, but it
    would matter if there was a converter meant to catch any string, then a
    converter to catch an uppercase string, as the arguments ["HI", "hello"]
    will then raise an exception, since the "any" string converter is thes
    one used with "HI", and then the only remaining converter is the
    uppercase one, and so "hello" is not converted.
    -----------

    A converter is an object that tries to convert an argument to a certain
    class. If it can't, it raises discord.ext.commands.BadArgument. It takes
    as input a discord context and an argument.
    There are many default Discord Converters, for example
    commands.MemberConverter(). Otherwise, it is possible to make a converter
    by inheriting commands.Converter. For example, here is a converter that
    checks if an argument starts by "a" and returns the rest of the string
    if so

    class StartsByAConverter(commands.Converter):
        async def convert(self, ctx, argument):
            if not type(argument) is str:
                raise commands.BadArgument("Unexpected type")
            if argument[0] != a:
                raise commands.BadArgument("Argument doesn't start with 'a'")
            result = argument[1:]
            return result

    A converter could also simply check that an argument is of a certain type
    or has certain attributes and return the argument itself with no
    conversion, which would act like a pseudo-typecheck. It could also
    call another converter, for example stripping a certain argument and
    and trying to convert the remaining string to a discord member.

    Example use:

    from discord.ext.commands import MemberConverter, TextChannelConverter
    class StartsByAConverter(commands.Converter):
        (as above)
    @commands.command()
    async def example(self, ctx, *args):
      arg_converter = ArgConverter({"member": (MemberConverter(), None),
                                    "channel": (TextChannelConverter(), )
                                    "string_A": (FromConverter(), "hi"))
    try:
        args_dict = await arg_converter.convert(ctx, args)
    except commands.BadArgument as err:
        await ctx.send(err)
        return
    await ctx.send(f"{str(args_dict["member"])}, "
                   f"{args_dict["channel"]}, "
                   f"{args_dict["string_A"]}")

    Here are example inputs and what is sent in the server:
    `?example #channel`: None, #channel, hi
    `?example aword @someone #channel`: someone#1234, #channel, word
    `?example aword @someone"`:
    Invalid input: Missing required argument "channel"
    `?example #channel aword @someone woo`:
    Invalid input: Argument "woo" could not be converted
    """
    def __init__(self, converters_dict):
        self._converters_dict = converters_dict

    async def convert(self, ctx, arguments):
        """
        Match the arguments to the converters. If a converter is used,
        doesn't try to match it again. All required arguments must be
        given, and all arguments must be able to be converted.

        See the comment about dictionary order in the ArgConverter docstring

        Returns a dictionary with the variables as keys, and their values.
        """
        remaining_vars = self._converters_dict.copy()
        # initialize the converted dict with None values
        converted_arguments_dict = {}

        for arg in arguments:
            # keep track if the argument is converted. If it is not after
            # trying every converter, an error will be raised
            arg_converted = False
            for key in remaining_vars:
                try:
                    # try converting the argument
                    converted_arguments_dict[key] = await remaining_vars[key][0].convert(ctx, arg)
                    # if we did, delete the key from the converters dict
                    # as a converter
                    del remaining_vars[key]
                    arg_converted = True
                    break
                except commands.BadArgument:
                    # if this converted didn't work, we try the next
                    pass
            if not arg_converted:
                raise commands.BadArgument(f"Invalid input: Argument \"{arg}\" could not be converted")
        # if there are remaining variables, either set them to their default
        # values or raise commands.BadArgument if they are required
        for key in remaining_vars:
            if len(self._converters_dict[key]) == 1:
                raise commands.BadArgument(f"Invalid input: Missing required " f"argument {key}")
            else:
                converted_arguments_dict[key] = self._converters_dict[key][1]
        return converted_arguments_dict
