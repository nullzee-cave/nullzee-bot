from discord.ext import commands, tasks
from random import randint
import json
import asyncio
import discord
import aiohttp
import random
from discord.ext.commands.cooldowns import BucketType
import time
import math
import os
import datetime
from EZPaginator import Paginator
from helpers.utils import min_level, get_user, Embed, getFileJson, leaderboard_pages, staff_only, ShallowContext, \
    saveFileJson, clean_message_content, remove_emojis, event_hoster_or_staff, role_ids
from helpers.constants import Category, Role, Channel, Misc
from helpers.events import Emitter
from api_key import userColl
import pymongo


class Levelling(commands.Cog, name="levelling"):
    """The levelling system, and all related commands"""

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot: commands.Bot = bot
        self.update_multipliers()
        self.vc_tracker.start()
        self.boost_multiplier_end.start()

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
                    await userColl.update_one({"_id": str(member.id)}, {"$inc": {"vc_minutes": 1}})
                    to_add = [guild.get_role(int(Role.LevelRoles.VC_ROLES[z])) for z in Role.LevelRoles.VC_ROLES if user_data["vc_minutes"] > int(z) and int(Role.LevelRoles.VC_ROLES[z]) not in role_ids(member.roles)]
                    if not all(role is None for role in to_add):
                        await member.add_roles(*to_add)

    @commands.command()
    async def linkTwitch(self, ctx, username: str):
        """Link your twitch to your discord to start gaining xp in twitch chat"""
        await userColl.update_one({"_id": str(ctx.author.id)},
                                  {"$set": {"twitch_name": username.lower(), "twitch_verified": False}})
        await ctx.send(embed=discord.Embed(
            description=f"You have linked your discord account to your twitch account. In order to start gaining XP in Nullzee's twitch chat, you must type `-verify {ctx.author.id}` there.",
            colour=0x00ff00))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.pending and not after.pending:
            # roles = [after.guild.get_role(Role.LevelRoles.LEVELS["1"])]
            user_data = await userColl.find_one({"_id": str(after.id)})
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
        with open('config.json') as f:
            config = json.load(f)
        self.multipliers = config["multipliers"]
        self.global_multiplier = config["global_multiplier"]

    @commands.command(hidden=True)
    @staff_only
    async def multipliers(self, ctx):
        """Check current multipliers in all channels"""
        multipliers = f"Global: {self.global_multiplier}\n"
        multipliers += "\n".join([f"<#{z}> : {self.multipliers[z]}" for z in self.multipliers if
                                  (self.multipliers[z] != 1 and ctx.guild.get_channel(int(z)).category.id not in [Category.ARCHIVED_CHATS])])
        await ctx.send(embed=discord.Embed(title="Current XP multipliers", description=multipliers))

    @commands.command(hidden=True)
    @staff_only
    async def multiplier(self, ctx, channel: discord.TextChannel, value: float):
        """Change the xp multiplier of a channel"""
        if value < -0.5 or value > 10:
            return await ctx.send("please resign.")
        config = getFileJson()
        config["multipliers"][str(channel.id)] = value
        await ctx.send(f"set XP multiplier for {channel.mention} to {value}")
        saveFileJson(config)
        self.update_multipliers()

    @commands.command(hidden=True)
    @staff_only
    async def global_multiplier(self, ctx, value: float):
        """Change the global xp multiplier for the whole server"""
        if value < -0.5 or value > 10:
            return await ctx.send("please resign.")
        config = getFileJson()
        config["global_multiplier"] = value
        config["manual_multiplier"] = value != 1
        await ctx.send(f"set global XP multiplier to {value}")
        saveFileJson(config)
        self.update_multipliers()

    @tasks.loop(minutes=1)
    async def boost_multiplier_end(self):
        config = getFileJson()
        if config["boost_multiplier_end"] < time.time() and not config["manual_multiplier"]:
            config["global_multiplier"] = 1
            saveFileJson(config)
            self.update_multipliers()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.type == discord.MessageType.premium_guild_subscription:
            config = getFileJson()
            config["global_multiplier"] = 2
            config["boost_multiplier_end"] = max(config["boost_multiplier_end"] + 3600, time.time() + 3600)
            saveFileJson(config)
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
            await Emitter().emit('message', ctx, user_data=user_data)
            if str(message.channel.id) in self.multipliers:
                multiplier = self.multipliers[str(message.channel.id)]
            else:
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
                await userColl.update_one({"_id": str(message.author.id)},
                                          {"$inc": {"experience": exp, "weekly": weekly_exp, "points": points_bonus},
                                           "$set": {"last_message": time.time(),
                                                    "last_points": user_data["experience"] + exp if points_bonus else
                                                    user_data["last_points"]}})
                user_data = await userColl.find_one({"_id": str(message.author.id)})
            else:
                user_data = await userColl.find_one({"_id": str(message.author.id)})

            experience = user_data["experience"]
            lvl_start = user_data["level"]
            lvl_end = 50 * (lvl_start ** 1.5)
            if experience > lvl_end:
                await Emitter().emit("level_up", ctx, lvl_start + 1, user_data=user_data)
                await userColl.update_one({"_id": str(message.author.id)},
                                          {"$inc": {"level": 1}, "$set": {"experience": 0,
                                                                          "last_points": 0 - (
                                                                                  experience - (
                                                                                  user_data[
                                                                                      "last_points"] + 100))}})
                await message.channel.send(
                    f":tada: Congrats {message.author.mention}, you levelled up to level {lvl_start + 1}!")
                if str(lvl_start + 1) in Role.LevelRoles.LEVELS:
                    role = message.guild.get_role(int(Role.LevelRoles.LEVELS[str(lvl_start + 1)]))
                    await message.author.add_roles(role)

    @commands.command(aliases=['level', "lvl"])
    async def rank(self, ctx, user: discord.Member = None):
        """View your or the mentioned user's level"""
        if not user:
            user = ctx.author
        user_data = await userColl.find_one({"_id": str(user.id)})
        if not user_data:
            return await ctx.send("This user has no level")
        string = f"XP: {round(user_data['experience']):,}/{round(50 * (round(user_data['level']) ** 1.5)):,}"
        string += f"\nWeekly XP: {round(user_data['weekly']):,}"
        string += f"\nPoints: {user_data['points']:,}"
        string += f"\nTotal XP: {(sum([round(50 * z ** 1.5) for z in range(1, user_data['level'])]) + user_data['experience']):,}"
        string += f"\nMinutes in VC: {user_data['vc_minutes']:,}"
        embed = await Embed(user, title=f"Level: {str(round(user_data['level']))}", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=RickAstley",
                            description=string).user_colour()
        embed.set_author(name=user, icon_url=user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=["howFarFromLevel"])
    async def hffl(self, ctx, wanted_level: int = None):
        """View how far from a specific level you are, along with some other information"""
        user = ctx.author
        user_data = await userColl.find_one({"_id": str(user.id)})
        level = user_data['level']
        xp = user_data['experience']
        if wanted_level is None:
            wanted_level = level + 1
        elif wanted_level <= level or wanted_level > 500:
            return await ctx.send("This number is invalid")

        def total_xp(y):
            return sum([round(50 * z ** 1.5) for z in range(1, y)])

        def level_xp(x):
            return round(50 * (x ** 1.5))

        desired_total_xp = level_xp(wanted_level)
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

    @commands.command(aliases=["wk"])
    @commands.guild_only()
    async def weekly(self, ctx):
        """View the server's weekly XP leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild,
                                   [z async for z in userColl.find({}).sort('weekly', pymongo.DESCENDING)],
                                   key="weekly", suffix=" XP")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(aliases=["vclb"])
    @commands.guild_only()
    async def vcleaderboard(self, ctx):
        """View the server's vc minute leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild,
                                   [z async for z in userColl.find({}).sort('vc_minutes', pymongo.DESCENDING)],
                                   key="vc_minutes", suffix=" minutes",
                                   title="Voice Activity leaderboard",
                                   field_name="Talk in a voice channel to gain time")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(aliases=["plb"])
    @commands.guild_only()
    async def pointsleaderboard(self, ctx):
        """View the server's points leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild,
                                   [z async for z in userColl.find({}).sort('points', pymongo.DESCENDING)],
                                   key="points", suffix=" points",
                                   title="Points leaderboard", field_name="Gain 1 point every 1000 XP")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(aliases=["lb"])
    @commands.guild_only()
    async def leaderboard(self, ctx):
        """View the server's XP leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild, [z async for z in userColl.find({}).sort(
            [('level', pymongo.DESCENDING), ('experience', pymongo.DESCENDING)])], prefix="level ")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(hidden=True)
    @staff_only
    async def weeklyReset(self, ctx):
        """Reset everyone's weekly xp"""
        await ctx.send("resetting...")
        with open('users.json') as f:
            users = json.load(f)
        async for user in userColl.find({}):
            users[str(user["_id"])] = user
        # if (math.trunc(time.time()) + 604800) > users["config"]["week_start"]:
        with open(f"backups/{datetime.datetime.now().strftime('%d%m%y')}.json", 'w') as f:
            json.dump(users, f)
        await userColl.update_many({}, {"$set": {"weekly": 0}})
        # users["config"]["week_start"] = math.trunc(time.time())
        with open('users.json', 'w') as f:
            json.dump(users, f)
        await self.bot.get_guild(Misc.GUILD).get_channel(Channel.MOD_LOGS).send(
            embed=discord.Embed(description="Weekly XP leaderboard was reset", color=discord.Color.blue()))
        await ctx.send(
            embed=discord.Embed(description="Weekly XP leaderboard was reset", color=discord.Color.blue()))

    # @tasks.loop(hours=1)
    # async def weeklyreset(self):
    #     with open('users.json') as f:
    #         users = json.load(f)
    #     async for user in userColl.find({}):
    #         users[str(user["_id"])] = user
    #     if (math.trunc(time.time()) + 604800) > users["config"]["week_start"]:
    #         with open(f"backups/{datetime.datetime.now().strftime('%d%m%y')}.json", 'w') as f:
    #             json.dump(users, f)
    #         await userColl.update_many({}, {"$set": {"weekly": 0}})
    #         users["config"]["week_start"] = math.trunc(time.time())
    #         with open('users.json', 'w') as f:
    #             json.dump(users, f)
    #         await self.bot.get_guild(667953033929293855).get_channel(667957285837864960).send(embed=discord.Embed(description="Weekly XP leaderboard was reset"), color=discord.Color.blue())

    @commands.command(hidden=True)
    @commands.has_role(Role.ADMIN)
    async def levelBackup(self, ctx):
        """Create a backup of all user's levels"""
        if Role.ADMIN not in [z.id for z in ctx.author.roles]:
            return
        with open('users.json') as f:
            users = json.load(f)
        async for user in userColl.find({}):
            users[str(user["_id"])] = user
        with open(f"backups/{datetime.datetime.now().strftime('%d%m%y')}.json", 'w+') as f:
            json.dump(users, f)
        await ctx.send("Backup created")

    @commands.command(hidden=True)
    @event_hoster_or_staff
    async def removeweekly(self, ctx, user: discord.Member, xp: int):
        """Remove weekly xp from a user"""
        if Role.STAFF in [z.id for z in user.roles]:
            return await ctx.send("Cannot remove XP from that user")
        if xp < 0:
            return await ctx.send("nice try")
        if (await userColl.find_one({"_id": str(user.id)}))["weekly"] < xp:
            await userColl.update_one({"_id": str(user.id)}, {"$set": {"weekly": 0}})
        else:
            await userColl.update_one({"_id": str(user.id)}, {"$inc": {"weekly": -xp}})
        await ctx.send(f"removed {xp} weekly xp from {user.mention}")

    @commands.command(hidden=True)
    @staff_only
    async def removeXP(self, ctx, user: discord.Member, xp: int):
        """Remove xp from someone"""
        if Role.STAFF in [z.id for z in user.roles]:
            return await ctx.send("Cannot remove XP from that user")
        if xp < 0:
            return await ctx.send("nice try")
        if (await userColl.find_one({"_id": str(user.id)}))["experience"] < xp:
            await userColl.update_one({"_id": str(user.id)}, {"$set": {"experience": 0}})
        else:
            await userColl.update_one({"_id": str(user.id)}, {"$inc": {"experience": -xp}})
        await ctx.send(f"removed {xp} xp from {user.mention}")

    @commands.command(hidden=True)
    @commands.has_role(Role.ADMIN)
    async def setlevel(self, ctx, user: discord.Member, level: int):
        """
        Set a user to a specific level
        **For use in emergencies only**
        """
        if level <= 0:
            return await ctx.send("Cannot set a level below 1")
        elif level > 200:
            return await ctx.send("why did you think that would work")
        await userColl.update_one({"_id": str(user.id)}, {"$set": {"level": level, "experience": 0}})
        response_msg = await ctx.send(f"{user.mention} has been set to level `{level}`", allowed_mentions=discord.AllowedMentions(users=False))
        await ctx.message.delete()
        await asyncio.sleep(3)
        await response_msg.delete()


def setup(bot):
    bot.add_cog(Levelling(bot, False))
