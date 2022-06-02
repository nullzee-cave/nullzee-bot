import typing

from discord.ext import commands, tasks
import json
import asyncio
import discord
import time
import math
import datetime
from EZPaginator import Paginator
from helpers.utils import get_user, Embed, get_file_json, leaderboard_pages, staff_only, ShallowContext, \
    save_file_json, clean_message_content, remove_emojis, event_hoster_or_staff, role_ids
from helpers.constants import Category, Role, Channel, Misc
from helpers.events import Emitter
from api_key import user_coll
import pymongo


class Levelling(commands.Cog, name="Levelling"):
    """The levelling system, and all related commands"""

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot: commands.Bot = bot
        self.multipliers = {}
        self.global_multiplier = 1.0
        self.update_multipliers()
        self.vc_tracker.start()
        self.boost_multiplier_end.start()
        self.check_level_one_role.start()

    def cog_unload(self):
        self.vc_tracker.cancel()

    @tasks.loop(minutes=1)
    async def vc_tracker(self):
        guild: discord.Guild = self.bot.get_guild(Misc.GUILD)
        for channel in filter(lambda x: isinstance(x, discord.VoiceChannel), guild.channels):
            channel: discord.VoiceChannel
            for member in channel.members:
                member: discord.Member
                if not member.bot:
                    user_data = await get_user(member)
                    await Emitter().emit("vc_minute_gain", await ShallowContext.create(member), user_data["vc_minutes"])
                    await user_coll.update_one({"_id": str(member.id)}, {"$inc": {"vc_minutes": 1}})
                    to_add = [guild.get_role(int(Role.LevelRoles.VC_ROLES[z])) for z in
                              Role.LevelRoles.VC_ROLES if user_data["vc_minutes"] > int(z) and
                              int(Role.LevelRoles.VC_ROLES[z]) not in role_ids(member.roles)]
                    if not all(role is None for role in to_add):
                        await member.add_roles(*to_add)

    @vc_tracker.before_loop
    async def before_vc_tracker(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def check_level_one_role(self):
        guild = self.bot.get_guild(Misc.GUILD)
        role = guild.get_role(int(Role.LevelRoles.LEVELS["1"]))
        for member in guild.members:
            if not member.pending and role not in member.roles:
                await member.add_roles(role)

    @check_level_one_role.before_loop
    async def before_check_level_one_role(self):
        await self.bot.wait_until_ready()

    @commands.command(name="linktwitch")
    async def link_twitch(self, ctx, username: str):
        """Link your twitch to your discord to start gaining xp in twitch chat"""
        await user_coll.update_one({"_id": str(ctx.author.id)},
                                   {"$set": {"twitch_name": username.lower(), "twitch_verified": False}})
        await ctx.send(embed=discord.Embed(
            description=f"You have linked your discord account to your twitch account. "
                        f"In order to start gaining XP in Nullzee's twitch chat, you must type "
                        f"`-verify {ctx.author.id}` there.",
            colour=0x00ff00))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # TODO: make sure this actually works
        # This is so unbelievably scuffed and broken that it's not even funny
        if before.pending and not after.pending:
            # roles = [after.guild.get_role(Role.LevelRoles.LEVELS["1"])]
            user_data = await user_coll.find_one({"_id": str(after.id)})
            # role_ids = []
            if user_data:
                level = user_data["level"]
                for lr in Role.LevelRoles.LEVELS:
                    if int(lr) > level:
                        break
                    else:
                        role = after.guild.get_role(int(Role.LevelRoles.LEVELS[str(lr)]))
                        if role not in after.roles:
                            await after.add_roles(role)
                            # roles.append(role)
                        # role_ids.append(int(Role.LevelRoles.LEVELS[str(lr)]))
                # await after.add_roles(*roles)

    def update_multipliers(self):
        with open("config.json") as f:
            config = json.load(f)
        self.multipliers = config["multipliers"]
        self.global_multiplier = config["global_multiplier"]

    @commands.command(hidden=True)
    @staff_only
    async def multipliers(self, ctx):
        """Check current multipliers in all channels"""
        multipliers = f"Global: {self.global_multiplier}\n"
        multipliers += "\n".join([f"<#{z}> : {self.multipliers[z]}" for z in self.multipliers if
                                  (self.multipliers[z] != 1 and
                                   ctx.guild.get_channel_or_thread(int(z)).category.id not in [Category.ARCHIVED_CHATS])])
        await ctx.send(embed=discord.Embed(title="Current XP multipliers", description=multipliers))

    @commands.command(hidden=True)
    @staff_only
    async def multiplier(self, ctx, channel: typing.Union[discord.TextChannel, discord.Thread], value: float):
        """Change the xp multiplier of a channel"""
        if value < -0.5 or value > 10:
            return await ctx.send("please resign.")
        config = get_file_json()
        config["multipliers"][str(channel.id)] = value
        await ctx.send(f"Set XP multiplier for {channel.mention} to {value}")
        save_file_json(config)
        self.update_multipliers()

    @commands.command(hidden=True)
    @staff_only
    async def global_multiplier(self, ctx, value: float):
        """Change the global xp multiplier for the whole server"""
        if value < -0.5 or value > 10:
            return await ctx.send("please resign.")
        config = get_file_json()
        config["global_multiplier"] = value
        config["manual_multiplier"] = value != 1
        await ctx.send(f"Set global XP multiplier to {value}")
        save_file_json(config)
        self.update_multipliers()

    @tasks.loop(minutes=1)
    async def boost_multiplier_end(self):
        config = get_file_json()
        if config["boost_multiplier_end"] < time.time() and not config["manual_multiplier"]:
            config["global_multiplier"] = 1
            save_file_json(config)
            self.update_multipliers()

    @boost_multiplier_end.before_loop
    async def before_boost_multiplier_end(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.type == discord.MessageType.premium_guild_subscription:
            config = get_file_json()
            config["global_multiplier"] = 2
            config["boost_multiplier_end"] = max(config["boost_multiplier_end"] + 3600, time.time() + 3600)
            save_file_json(config)
            self.update_multipliers()
        if not message.guild:
            return
        if isinstance(message.author, discord.Member) and \
                int(Role.LevelRoles.LEVELS["1"]) not in role_ids(message.author.roles) and not message.author.pending:
            await message.author.add_roles(message.guild.get_role(int(Role.LevelRoles.LEVELS["1"])))
        if message.author.bot:
            return
        else:
            user_data = await get_user(message.author)
            ctx = await self.bot.get_context(message)
            await Emitter().emit("message", ctx, user_data=user_data)
            multiplier = None
            if str(message.channel.id) in self.multipliers:
                multiplier = self.multipliers[str(message.channel.id)]
            elif isinstance(message.channel, discord.Thread):
                if str(message.channel.parent) in self.multipliers and \
                   self.multipliers[str(message.channel.parent)] < 1:
                    multiplier = self.multipliers[str(message.channel.parent)]
            if multiplier is None:
                multiplier = 1
            if message.attachments:
                base_exp = 30
            elif len("".join(remove_emojis(clean_message_content(message.content)))) > 150:
                base_exp = 50
            else:
                base_exp = 25
            exp = math.trunc(multiplier * self.global_multiplier * base_exp)
            weekly_exp = math.trunc(
                self.global_multiplier * base_exp) if message.channel.id in Misc.NO_WEEKLY_MULTIPLIER_CHANNELS else exp
            if time.time() - user_data["last_message"] > 30:
                points_bonus = 1 if user_data["experience"] > user_data["last_points"] + 1000 else 0
                if points_bonus:
                    await Emitter().emit("point_earned", ctx, user_data["points"] + 1, user_data=user_data)
                await user_coll.update_one({"_id": str(message.author.id)},
                                           {"$inc": {"experience": exp, "weekly": weekly_exp, "points": points_bonus},
                                           "$set": {"last_message": time.time(),
                                                    "last_points": user_data["experience"] + exp if points_bonus else
                                                    user_data["last_points"]}})
                user_data = await user_coll.find_one({"_id": str(message.author.id)})
            else:
                user_data = await user_coll.find_one({"_id": str(message.author.id)})

            experience = user_data["experience"]
            lvl_start = user_data["level"]
            lvl_end = 50 * (lvl_start ** 1.5)
            if experience > lvl_end:
                await Emitter().emit("level_up", ctx, lvl_start + 1, user_data=user_data)
                await user_coll.update_one({"_id": str(message.author.id)},
                                           {"$inc": {"level": 1},
                                            "$set": {
                                                "experience": 0,
                                                "last_points": 0 - (experience - (user_data["last_points"] + 100))
                                            }})
                await message.channel.send(
                    f":tada: Congrats {message.author.mention}, you levelled up to level {lvl_start + 1}!")
                    
                if str(lvl_start + 1) in Role.LevelRoles.LEVELS:
                    role = message.guild.get_role(int(Role.LevelRoles.LEVELS[str(lvl_start + 1)]))
                    await message.author.add_roles(role)

    @commands.command(aliases=["rank", "lvl"])
    async def level(self, ctx, user: discord.Member = None):
        """View your or the mentioned user's level"""
        if not user:
            user = ctx.author
        user_data = await user_coll.find_one({"_id": str(user.id)})
        if not user_data:
            return await ctx.send("This user has no level")
        string = f"XP: {round(user_data['experience']):,}/{round(50 * (round(user_data['level']) ** 1.5)):,}"
        string += f"\nWeekly XP: {round(user_data['weekly']):,}"
        string += f"\nPoints: {user_data['points']:,}"
        string += f"\nTotal XP: {(sum([round(50 * z ** 1.5) for z in range(1, user_data['level'])]) + user_data['experience']):,}"
        string += f"\nMinutes in VC: {user_data['vc_minutes']:,}"
        
        embed = Embed(user,
                            title=f"Level: {str(round(user_data['level']))}",
                            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=RickAstley",
                            description=string)
        await embed.user_colour()
        embed.set_author(name=user, icon_url=user.avatar)
        await ctx.send(embed=embed)

    @commands.command(name="hffl", aliases=["howfarfromlevel"])
    async def how_far_from_level(self, ctx, wanted_level: int = None):
        """View how far from a specific level you are, along with some other information"""
        user = ctx.author
        user_data = await user_coll.find_one({"_id": str(user.id)})
        level = user_data["level"]
        xp = user_data["experience"]
        if wanted_level is None:
            wanted_level = level + 1
        elif wanted_level <= level or wanted_level > 500:
            return await ctx.send("This number is invalid")

        def total_xp(y):
            return sum([round(50 * z ** 1.5) for z in range(1, y)])

        def level_xp(x):
            return round(50 * (x ** 1.5))

        embed = await Embed(user, title="XP Calculator").user_colour()
        embed.add_field(name="Desired Level",
                        value=f"XP until desired level: {(sum([round(50 * z ** 1.5) for z in range(level, wanted_level)]) - xp):,}\nXP of desired level: {(level_xp(wanted_level)):,}")
        embed.add_field(name="Total XP Stats",
                        value=f"Total XP of desired level: {(total_xp(wanted_level)):,}\nYour total XP: {(total_xp(level) + xp):,}",
                        inline=False)
        embed.add_field(name="Next Level",
                        value=f"XP until next level: {(level_xp(level) - xp):,}\nXP of next level: {(level_xp(level + 1)):,}",
                        inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="weekly", aliases=["wk"])
    @commands.guild_only()
    async def weekly_leaderboard(self, ctx):
        """View the server's weekly XP leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild,
                                   [z async for z in user_coll.find({}).sort("weekly", pymongo.DESCENDING)],
                                   key="weekly", suffix=" XP")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(name="vcleaderboard", aliases=["vclb"])
    @commands.guild_only()
    async def vc_leaderboard(self, ctx):
        """View the server's vc minute leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild,
                                   [z async for z in user_coll.find({}).sort("vc_minutes", pymongo.DESCENDING)],
                                   key="vc_minutes", suffix=" minutes",
                                   title="Voice Activity leaderboard",
                                   field_name="Talk in a voice channel to gain time")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(name="pointsleaderboard", aliases=["plb"])
    @commands.guild_only()
    async def points_leaderboard(self, ctx):
        """View the server's points leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild,
                                   [z async for z in user_coll.find({}).sort("points", pymongo.DESCENDING)],
                                   key="points", suffix=" points",
                                   title="Points leaderboard", field_name="Gain 1 point every 1000 XP")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(aliases=["lb"])
    @commands.guild_only()
    async def leaderboard(self, ctx):
        """View the server's XP leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild, [z async for z in user_coll.find({}).sort(
            [("level", pymongo.DESCENDING), ("experience", pymongo.DESCENDING)])], prefix="level ")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(name="weeklyreset", aliases=["resetweekly"], hidden=True)
    @staff_only
    async def weekly_reset(self, ctx):
        """Reset everyone's weekly xp"""
        await ctx.send("Resetting...")
        with open("users.json") as f:
            users = json.load(f)
        async for user in user_coll.find({}):
            users[str(user["_id"])] = user
        # if (math.trunc(time.time()) + 604800) > users["config"]["week_start"]:
        with open(f"backups/{datetime.datetime.now().strftime('%d%m%y')}.json", "w") as f:
            json.dump(users, f)
        await user_coll.update_many({}, {"$set": {"weekly": 0}})
        # users["config"]["week_start"] = math.trunc(time.time())
        with open("users.json", "w") as f:
            json.dump(users, f)
        embed = discord.Embed(description="Weekly XP leaderboard was reset", color=discord.Color.blue())
        await self.bot.get_guild(Misc.GUILD).get_channel(Channel.MOD_LOGS).send(embed=embed)
        await ctx.send(embed=embed)

    # @tasks.loop(hours=1)
    # async def weeklyreset(self):
    #     with open("users.json") as f:
    #         users = json.load(f)
    #     async for user in userColl.find({}):
    #         users[str(user["_id"])] = user
    #     if (math.trunc(time.time()) + 604800) > users["config"]["week_start"]:
    #         with open(f"backups/{datetime.datetime.now().strftime('%d%m%y')}.json", "w") as f:
    #             json.dump(users, f)
    #         await userColl.update_many({}, {"$set": {"weekly": 0}})
    #         users["config"]["week_start"] = math.trunc(time.time())
    #         with open("users.json", "w") as f:
    #             json.dump(users, f)
    #         await self.bot.get_guild(667953033929293855).get_channel(667957285837864960).send(embed=discord.Embed(description="Weekly XP leaderboard was reset"), color=discord.Color.blue())
    #
    # @weekly_reset.before_loop
    # async def before_weekly_reset(self):
    #     await self.bot.wait_until_ready()

    @commands.command(name="levelbackup", hidden=True)
    @commands.has_role(Role.ADMIN)
    async def level_backup(self, ctx):
        """Create a backup of all user's levels"""
        if Role.ADMIN not in [z.id for z in ctx.author.roles]:
            return
        with open("users.json") as f:
            users = json.load(f)
        async for user in user_coll.find({}):
            users[str(user["_id"])] = user
        with open(f"backups/{datetime.datetime.now().strftime('%d%m%y')}.json", "w+") as f:
            json.dump(users, f)
        await ctx.send("Backup created")

    @commands.command(name="removeweekly", hidden=True)
    @event_hoster_or_staff
    async def remove_weekly(self, ctx, user: discord.Member, xp: int):
        """Remove weekly xp from a user"""
        if Role.STAFF in [z.id for z in user.roles]:
            return await ctx.send("Cannot remove XP from that user")
        if xp < 0:
            return await ctx.send("nice try")
        if (await user_coll.find_one({"_id": str(user.id)}))["weekly"] < xp:
            await user_coll.update_one({"_id": str(user.id)}, {"$set": {"weekly": 0}})
        else:
            await user_coll.update_one({"_id": str(user.id)}, {"$inc": {"weekly": -xp}})
        await ctx.send(f"removed {xp} weekly xp from {user.mention}")

    @commands.command(name="removexp", hidden=True)
    @staff_only
    async def remove_xp(self, ctx, user: discord.Member, xp: int):
        """Remove xp from someone"""
        if Role.STAFF in [z.id for z in user.roles]:
            return await ctx.send("Cannot remove XP from that user")
        if xp < 0:
            return await ctx.send("nice try")
        if (await user_coll.find_one({"_id": str(user.id)}))["experience"] < xp:
            await user_coll.update_one({"_id": str(user.id)}, {"$set": {"experience": 0}})
        else:
            await user_coll.update_one({"_id": str(user.id)}, {"$inc": {"experience": -xp}})
        await ctx.send(f"removed {xp} xp from {user.mention}")

    @commands.command(name="setlevel", hidden=True)
    @commands.has_role(Role.ADMIN)
    async def set_level(self, ctx, user: discord.Member, level: int):
        """
        Set a user to a specific level
        **For use in emergencies only**
        """
        if level <= 0:
            return await ctx.send("Cannot set a level below 1")
        elif level > 200:
            return await ctx.send("why did you think that would work")
        await user_coll.update_one({"_id": str(user.id)}, {"$set": {"level": level, "experience": 0}})
        response_msg = await ctx.send(f"{user.mention} has been set to level `{level}`",
                                      allowed_mentions=discord.AllowedMentions(users=False))
        await ctx.message.delete()
        await asyncio.sleep(3)
        await response_msg.delete()


async def setup(bot):
    await bot.add_cog(Levelling(bot, False))
