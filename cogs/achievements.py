from discord.ext import commands, tasks
import discord
from achievements.achievements import achievements
from achievements.images import achievement_page, achievement_timeline
from helpers.events import Emitter
from helpers.utils import get_user
from math import ceil
import typing
import os
import json
import time


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
        self.clear_image_cache.start()

    def cog_unload(self):
        self.clear_image_cache.cancel()

    @tasks.loop(minutes=1)
    async def clear_image_cache(self):
        for filename in os.listdir("assets/user_achievements"):
            if filename.endswith(".json"):
                with open(filename) as f:
                    cached_data = json.load(f)
                if cached_data["last_called"] + 600 < time.time():
                    for image_filename in cached_data["image_files"]:
                        os.remove(image_filename)
                    os.remove(filename)

    def generate_static_pages(self):
        for i in range(ceil(len(achievements) / 3)):
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
        achievement_page(page - 1)
        await ctx.send(file=discord.File(f"assets/static_achievements/page_{page-1}.png"))

    @commands.command()
    async def myachievements(self, ctx, user: typing.Optional[discord.Member]=None, page=1):
        user = user if user else ctx.author
        user_data = await get_user(user)
        user_data["background"] = user_data["background"] if "background" in user_data else "default_background.png"
        try:
            await achievement_timeline(user, user_data, page)
        except ValueError:
            return await ctx.send("You don't have that many pages!")
        await ctx.send(file=discord.File(f"image_cache/user_achievements/{user.id}_{page}.png"))


def setup(bot):
    bot.add_cog(Achievements(bot))
