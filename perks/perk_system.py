import typing

from discord.ext import commands

perk_list = []


def register_perk(_perk):
    perk_list.append(_perk)


class Perk:
    def __init__(self, name, aliases, description, cost, require_arg, func):
        self.name = name
        self.aliases = aliases
        self.description = description
        self.cost = cost
        self.require_arg = require_arg
        self.on_buy = func

    def match_name(self, arg):
        return arg.lower() == self.name.lower() or arg.lower() in [z.lower() for z in self.aliases]


def perk(*, name: str = None, aliases=None, description: str = None,
         cost: typing.Union[int, str] = 0, require_arg: bool = False):
    name = name

    def decorator(func):
        _name = name if name else func.__name__
        _aliases = aliases if aliases else []
        this_perk = Perk(_name, _aliases, description, cost, require_arg, func)
        register_perk(this_perk)

        def wrapper(*args, **kwargs):
            pass

        return wrapper

    return decorator


class PerkConverter(commands.Converter):
    async def convert(self, ctx, argument) -> Perk:
        for _perk in perk_list:
            if _perk.match_name(argument):
                return _perk
        raise commands.UserInputError()


class PerkError(Exception):
    def __init__(self, msg=None, embed=None):
        self.message = msg
        self.embed = embed

    async def send_error(self, ctx):
        await ctx.send(self.message, embed=self.embed)
