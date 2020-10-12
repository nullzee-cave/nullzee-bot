from discord.ext import commands
perk_list = []


def register_perk(perk):
    perk_list.append(perk)


class Perk:
    def __init__(self):
        self.name = ""
        self.aliases = []
        self.description = ""
        self.cost = 0

    # def register_perk(self):
    #     perk_list.append(self)
    #     return self

    def match_name(self, arg):
        return arg.lower() == self.name.lower() or arg.lower() in [z.lower() for z in self.aliases]

    async def on_buy(self, ctx):
        raise NotImplementedError()


class PerkConverter(commands.Converter):
    async def convert(self, ctx, argument) -> Perk:
        for perk in perk_list:
            if perk.match_name(argument):
                return perk
        raise commands.UserInputError()
