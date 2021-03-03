from discord.ext import commands, tasks
import discord
from achievements.achievements import achievements
from achievements.images import achievement_page, achievement_timeline, achievement_timeline_animated, BackgroundMeta, \
    image_preview, BackgroundConverter
from api_key import userColl
from helpers.constants import Role
from helpers.events import Emitter
from helpers.utils import get_user, ShallowContext, getFileJson
from math import ceil
import typing
import os
import json
import time

import imageio


class Achievements(commands.Cog):

    def __init__(self, bot):
        self.hidden = True
        self.bot: commands.Bot = bot
        self.emitter = Emitter()
        self.generate_static_pages()
        self.generate_static_previews()
        self.clear_image_cache.start()

    def cog_unload(self):
        self.clear_image_cache.cancel()

    @tasks.loop(minutes=1)
    async def clear_image_cache(self):
        for filename in os.listdir("image_cache/user_achievements"):
            if filename.endswith(".json"):
                with open(filename) as f:
                    cached_data = json.load(f)
                if cached_data["last_called"] + 600 < time.time():
                    for image_filename in cached_data["image_files"]:
                        os.remove(image_filename)
                    os.remove(filename)

    def generate_static_previews(self):
        data = BackgroundMeta.get()
        previews = []
        for bg in data:
            if BackgroundMeta.get()[bg].preview:
                previews.append(imageio.imread(image_preview(bg)))
        imageio.mimsave(f"image_cache/static_previews/animated.gif", previews, fps=0.5)

    def generate_static_pages(self):
        for i in range(ceil(len({k: v for k, v in achievements.items() if "hidden" not in v}) / 3)):
            achievement_page(i, f"image_cache/static_achievements/page_{i}.png")
        images = []
        for page in sorted(os.listdir("image_cache/static_achievements/")):
            file_path = os.path.join("image_cache/static_achievements/", page)
            images.append(imageio.imread(file_path))
        imageio.mimsave(f'image_cache/static_achievements/animated.gif', images, fps=0.5)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        ctx = await self.bot.get_context(message)
        await self.emitter.emit("message", ctx)
        if message.is_system() and "pinned a message to this channel" in message.system_content:
            ctx.author = (await message.channel.pins())[-1].author
            await self.emitter.emit("pinned_starred", ctx)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            await self.emitter.emit("update_roles", await ShallowContext.create(after), after.roles)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        await self.emitter.emit("command", ctx, ctx.command.name)

    @commands.command()
    async def achievements(self, ctx, page: int = None):
        try:
            file_loc = "image_cache/static_achievements/" + (f"page_{page - 1}.png" if page else "animated.gif")
            await ctx.send(file=discord.File(file_loc))
        except FileNotFoundError:
            await ctx.send("There aren't that many pages!")

    @commands.command()
    async def setBackground(self, ctx, background: str):
        bg = background.lower()
        if bg not in BackgroundMeta.get():
            return await ctx.send(f"{ctx.author.mention}, could not find that image")
        bg_data = BackgroundMeta.get()[bg]
        if not bg_data.claimable:
            return await ctx.send(f"{ctx.author.mention}, this image is not claimable")
        role_ids = [z.id for z in ctx.author.roles]
        role_checks = []
        if bg_data.role_req:
            for role in bg_data.role_req:
                role_checks.append(Role[role.upper()] in role_ids)
            if (bg_data.role_req_strategy == "all" and False in role_checks) or (True not in role_checks):
                return await ctx.send(f"{ctx.author.mention}, you do not have the required role(s) to claim this image")
        await userColl.update_one({"_id": str(ctx.author.id)}, {"$set": {"background_image": bg}})
        await ctx.send(f"{ctx.author.mention}, set your background image to `{bg}`")

    @commands.command()
    async def previewImage(self, ctx, image: BackgroundConverter = None):
        image = f"image_cache/static_previews/{image}.png" if image else "image_cache/static_previews/animated.gif"
        await ctx.send(file=discord.File(image))

    @commands.command()
    async def myachievements(self, ctx, user: typing.Optional[discord.Member] = None, page: int = None):
        user = user if user else ctx.author
        user_data = await get_user(user)
        user_data["background_image"] = user_data["background_image"] if "background_image" in user_data else "default"
        if not page:
            await achievement_timeline_animated(user, user_data)
            await ctx.send(file=discord.File(f"image_cache/user_achievements/{user.id}_animated.gif"))
        else:
            try:
                did_create = await achievement_timeline(user, user_data, page)
            except ValueError:
                return await ctx.send("You don't have that many pages!")
            user_page_path = f"image_cache/user_achievements/{user.id}"
            await ctx.send(file=discord.File(f"{user_page_path}_{page}.png"))
            if not did_create:
                return
            with open(f"{user_page_path}.json") as f:
                cache_data = json.load(f)
            cache_data["regen_animated"] = True
            with open(f"{user_page_path}.json", 'w') as f:
                json.dump(cache_data, f)


def setup(bot):
    bot.add_cog(Achievements(bot))
