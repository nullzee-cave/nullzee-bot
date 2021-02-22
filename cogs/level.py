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
from helpers.utils import min_level, get_user, Embed, getFileJson, leaderboard_pages, staff_only
from api_key import userColl
import pymongo


class Levelling(commands.Cog, name="levelling"):
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot: commands.Bot = bot
        self.update_multipliers()
        self.vc_tracker.start()
    
    def cog_unload(self):
        self.vc_tracker.cancel()

    @tasks.loop(minutes=1)
    async def vc_tracker(self):
        guild: discord.Guild = self.bot.get_guild(667953033929293855)
        timed_roles = getFileJson("levelroles")["vc"]
        for channel in filter(lambda x: isinstance(x, discord.VoiceChannel), guild.channels):
            channel: discord.VoiceChannel
            for member in channel.members:
                member: discord.Member
                if not member.bot:
                    user_data = await get_user(member)
                    await userColl.update_one({"_id": str(member.id)}, {"$inc": {"vc_minutes": 1}})
                    await member.add_roles(
                        *[guild.get_role(timed_roles[z]) for z in timed_roles if user_data["vc_minutes"] > int(z)])

    @commands.command()
    async def linkTwitch(self, ctx, username: str):
        await userColl.update_one({"_id": str(ctx.author.id)},
                                  {"$set": {"twitch_name": username.lower(), "twitch_verified": False}})
        await ctx.send(embed=discord.Embed(
            description=f"You have linked your discord account to your twitch account. In order to start gaining XP in Nullzee's twitch chat, you must type `-verify {ctx.author.id}` there.",
            colour=0x00ff00))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.pending and not after.pending:
            with open('levelroles.json') as f:
                levelroles = json.load(f)["levels"]
            roles = []
            userData = await userColl.find_one({"_id": str(after.id)})
            if not userData:
                return
            level = userData["level"]
            for lr in levelroles:
                if int(lr) > level:
                    break
                else:
                    roles.append(after.guild.get_role(int(levelroles[str(lr)])))
            if not roles:
                return
            await after.add_roles(*roles)

        def update_multipliers(self):
            with open('config.json') as f:
                config = json.load(f)
            self.multipliers = config["multipliers"]
            self.global_multiplier = config["global_multiplier"]

    @commands.command()
    @staff_only
    async def multiplier(self, ctx, channel: discord.TextChannel, value: float):
        if value < -0.5 or value > 10:
            return await ctx.send("please resign.")
        with open('config.json') as f:
            config = json.load(f)
        config["multipliers"][str(channel.id)] = value
        await ctx.send(f"set XP multiplier for {channel.mention} to {value}")
        with open('config.json', 'w') as f:
            json.dump(config, f)
        self.update_multipliers()

    @commands.command()
    @staff_only
    async def global_multiplier(self, ctx, value: float):
        if value < -0.5 or value > 10:
            return await ctx.send("please resign.")
        with open('config.json') as f:
            config = json.load(f)
        config["global_multiplier"] = value
        await ctx.send(f"set global XP multiplier to {value}")
        with open('config.json', 'w') as f:
            json.dump(config, f)
        self.update_multipliers()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author.id == 307468800125829120:
            return
        if not message.guild:
            return
        else:
            userData = await get_user(message.author)
            if str(message.channel.id) in self.multipliers:
                multiplier = self.multipliers[str(message.channel.id)]
            else:
                multiplier = 1
            multiplier *= self.global_multiplier
            if message.attachments:
                number = math.trunc(30 * multiplier)
            elif len("".join(message.content)) > 150:
                number = math.trunc(50 * multiplier)
            else:
                number = math.trunc(25 * multiplier)
            userData = await self.add_experience(userData, message.author, number)
            await self.level_up(message, userData, message.author)

    async def add_experience(self, userData, user, exp):
        if time.time() - userData["last_message"] > 30:
            points_bonus = 1 if userData["experience"] > userData["last_points"] + 1000 else 0
            await userColl.update_one({"_id": str(user.id)},
                                      {"$inc": {"experience": exp, "weekly": exp, "points": points_bonus},
                                       "$set": {"last_message": time.time(),
                                                "last_points": userData["experience"] + exp if points_bonus else
                                                userData["last_points"]}})
            return await userColl.find_one({"_id": str(user.id)})
        else:
            return await userColl.find_one({"_id": str(user.id)})

    async def level_up(self, ctx, userData, user):
        experience = userData["experience"]
        lvl_start = userData["level"]
        lvl_end = 50 * (lvl_start ** 1.5)
        if experience > lvl_end:
            await userColl.update_one({"_id": str(user.id)}, {"$inc": {"level": 1}, "$set": {"experience": 0,
                                                                                             "last_points": 0 - (
                                                                                                         experience - (
                                                                                                             userData[
                                                                                                                 "last_points"] + 100))}})
            await ctx.channel.send(f":tada: Congrats {user.mention}, you levelled up to level {lvl_start + 1}!")
            with open('levelroles.json') as f:
                levelroles = json.load(f)["levels"]
            if str(lvl_start + 1) in levelroles:
                role = ctx.guild.get_role(int(levelroles[str(lvl_start + 1)]))
                await user.add_roles(role)

    @commands.command(aliases=['level', "lvl"])
    async def rank(self, ctx, user: discord.Member = None):
        """View your or the mentioned user's level"""
        if not user:
            user = ctx.author
        userData = await userColl.find_one({"_id": str(user.id)})
        if not userData:
            return await ctx.send("This user has no level")
        string = f"XP: {str(round(userData['experience']))}/{str(round(50 * (round(userData['level']) ** 1.5)))}"
        string += f"\nWeekly XP: {str(round(userData['weekly']))}"
        string += f"\nPoints: {userData['points']}"
        string += f"\nTotal XP: {(sum([round(50 * z ** 1.5) for z in range(1, userData['level'])]) + userData['experience']):,}"
        string += f"\nMinutes in VC: {userData['vc_minutes']:,}"
        embed = await Embed(user, title=f"Level: {str(round(userData['level']))}", url="https://nullzee.ga",
                            description=string).user_colour()
        embed.set_author(name=user, icon_url=user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(aliases = ["howFarFromLevel"])
    async def hffl(self, ctx, wantedLevel: int):
        user = ctx.author
        userData = await userColl.find_one({"_id": str(user.id)})
        level = userData['level']
        xp = userData['experience']
        if wantedLevel <= level or wantedLevel > 500:
            await ctx.send("This number is invalid")
        else:
            def total_xp(y):
                return sum([round(50*z**1.5) for z in range(1, y)])
            def level_xp(x):
                return round(50*(x**1.5))
            desiredTotalXP = level_xp(wantedLevel)
            embed = await Embed(user, title = "XP Calculator").user_colour()
            embed.add_field(name = "Desired Level", value = f"XP until desired level: {(sum([round(50*z**1.5) for z in range(level, wantedLevel)])-xp):,}\nXP of desired level: {(level_xp(wantedLevel)):,}")
            embed.add_field(name = "Total XP Stats", value = f"Total XP of desired level: {(total_xp(wantedLevel)):,}\nYour total XP: {(total_xp(level)):,}", inline = False)
            embed.add_field(name = "Next Level", value = f"XP until next level: {(level_xp(level+1)-xp):,}\nXP of next level: {(level_xp(level+1)):,}", inline = False)
            await ctx.send(embed = embed)

    @commands.command(aliases=["wk"])
    @commands.guild_only()
    async def weekly(self, ctx):
        """View the server's weekly XP leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild, [z async for z in userColl.find({}).sort('weekly', pymongo.DESCENDING)], key="weekly", suffix=" XP")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(aliases=["vclb"])
    @commands.guild_only()
    async def vcleaderboard(self, ctx):
        """View the server's vc minute leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild, [z async for z in userColl.find({}).sort('vc_minutes', pymongo.DESCENDING)], key="vc_minutes", suffix=" minutes",
                                   title="Voice Activity leaderboard", field_name="Talk in a voice channel to gain time")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()
    
    @commands.command(aliases=["plb"])
    @commands.guild_only()
    async def pointsleaderboard(self, ctx):
        """View the server's points leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild, [z async for z in userColl.find({}).sort('points', pymongo.DESCENDING)], key="points", suffix=" points",
                                   title="Points leaderboard", field_name="Gain 1 point every 1000 XP")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()

    @commands.command(aliases=["lb"])
    @commands.guild_only()
    async def leaderboard(self, ctx):
        """View the server's XP leaderboard"""
        embeds = leaderboard_pages(self.bot, ctx.guild, [z async for z in userColl.find({}).sort('level', pymongo.DESCENDING)], prefix="level ")
        msg = await ctx.send(embed=embeds[0])
        await Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author).start()


    @commands.command(hidden=True)
    @staff_only
    async def weeklyReset(self, ctx):
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
        await self.bot.get_guild(667953033929293855).get_channel(667957285837864960).send(
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
    @staff_only
    async def levelBackup(self, ctx):
        if ctx.author.id != 564798709045526528:
            return
        with open('users.json') as f:
            users = json.load(f)
        async for user in userColl.find({}):
            users[str(user["_id"])] = user
        with open(f"backups/{datetime.datetime.now().strftime('%d%m%y')}.json", 'w+') as f:
            json.dump(users, f)
        await ctx.send("Backup created")

    @commands.command(hidden=True)
    @staff_only
    async def removeweekly(self, ctx, user: discord.Member, xp: int):
        if 667953757954244628 in [z.id for z in user.roles]:
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
        if 667953757954244628 in [z.id for z in user.roles]:
            return await ctx.send("Cannot remove XP from that user")
        if xp < 0:
            return await ctx.send("nice try")
        if (await userColl.find_one({"_id": str(user.id)}))["experience"] < xp:
            await userColl.update_one({"_id": str(user.id)}, {"$set": {"experience": 0}})
        else:
            await userColl.update_one({"_id": str(user.id)}, {"$inc": {"experience": -xp}})
        await ctx.send(f"removed {xp} xp from {user.mention}")



def setup(bot):
    bot.add_cog(Levelling(bot, False))
