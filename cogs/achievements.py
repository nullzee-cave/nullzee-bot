from discord.ext import commands
import discord
from achievements.achievements import achievements
from achievements.images import achievement_page
from helpers.events import Emitter
from PIL import Image, ImageDraw, ImageFont
from math import ceil


class ShallowContext:
    def __init__(self):
        self.channel = None
        self.author = None
        self.guild = None

    @classmethod
    async def create(cls, member: discord.Member):
        self = cls()
        self.channel = (member.dm_channel or await member.create_dm())
        self.author = member
        self.guild = member.guild
        return self

    async def send(self, *args, **kwargs):
        return await self.channel.send(*args, **kwargs)

class Achievements(commands.Cog):

    def __init__(self, bot):
        self.hidden = True
        self.bot: commands.Bot = bot
        self.emitter = Emitter()
        self.generate_static_pages()

    def generate_static_pages(self):
        for i in range(ceil(len(achievements)/3)):
            achievement_page(i, f"assets/static_achievements/page_{i}.png")

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.emitter.emit("message", await self.bot.get_context(message))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            await self.emitter.emit("update_roles", await ShallowContext.create(after), after.roles)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        await self.emitter.emit("command", ctx, ctx.command.name)

    @commands.command()
    async def achievement(self, ctx, page: int):
        achievement_page(page-1)
        # await ctx.send(file=discord.File("image.png"))
        await ctx.send(file=discord.File(f"assets/static_achievements/page_{page+1}.png"))


def setup(bot):
    bot.add_cog(Achievements(bot))
