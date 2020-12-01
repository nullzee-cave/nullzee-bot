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
from helpers.utils import min_level, get_user, Embed
from api_key import userColl
import pymongo


class level(commands.Cog, name="levelling"):
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot
        self.update_multipliers()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        with open('levelroles.json') as f:
            levelroles = json.load(f)
        roles = []
        userData = await userColl.find_one({"_id": str(member.id)})
        if not userData:
            return
        level = userData["level"]
        for lr in levelroles:
            if int(lr) > level:
                break
            else:
                roles.append(member.guild.get_role(int(levelroles[str(lr)])))
        if not roles:
            return
        await asyncio.sleep(600)
        await member.add_roles(*roles)

    def update_multipliers(self):
        with open('config.json') as f:
            config = json.load(f)
        self.multipliers = config["multipliers"]
        self.global_multiplier = config["global_multiplier"]

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
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
    @commands.has_guild_permissions(manage_messages=True)
    async def global_multiplier(self, ctx, value: float):
        if value < -0.5 or value > 10:
            return await ctx.send("please resign.")
        with open('config.json') as f:
            config = json.load(f)
        config["global_multiplier"]= value
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
                                       "$set": {"last_message": time.time(), "last_points": userData["experience"] + exp if points_bonus else userData["last_points"]}})
            return await userColl.find_one({"_id": str(user.id)})
        else:
            return await userColl.find_one({"_id": str(user.id)})

    async def level_up(self, ctx, userData, user):
        experience = userData["experience"]
        lvl_start = userData["level"]
        lvl_end = 50 * (lvl_start ** 1.5)
        if experience > lvl_end:
            await userColl.update_one({"_id": str(user.id)}, {"$inc": {"level": 1}, "$set": {"experience": 0, "last_points": 0 - (experience - (userData["last_points"] + 100))}})
            await ctx.channel.send(f":tada: Congrats {user.mention}, you levelled up to level {lvl_start + 1}!")
            with open('levelroles.json') as f:
                levelroles = json.load(f)
            if str(lvl_start + 1) in levelroles:
                role = ctx.guild.get_role(int(levelroles[str(lvl_start + 1)]))
                await user.add_roles(role)

    @commands.command(aliases=['level'])
    async def rank(self, ctx, user: discord.Member = None):
        """View your or the mentioned user's level"""
        if not user:
            user = ctx.author
        userData = await userColl.find_one({"_id": str(user.id)})
        if not userData:
            return await ctx.send("This user has no level")
        embed = await Embed(user, title=f"Level: {str(round(userData['level']))}",
                              description=f"XP: {str(round(userData['experience']))}/{str(round(50 * (round(userData['level']) ** 1.5)))}\nWeekly XP: {str(round(userData['weekly']))}\nPoints: {userData['points']}").user_colour()
        embed.set_author(name=user, icon_url=user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def weekly(self, ctx):
        """View the server's weekly XP leaderboard"""
        embed = discord.Embed(color=0x00FF00).set_author(name="Nullzee's cave leaderboard", icon_url=ctx.guild.icon_url)
        count = 1
        contents = [embed]
        string = ''
        embedcount = 0
        info = [z async for z in userColl.find().sort('weekly', pymongo.DESCENDING)]
        for number, user in enumerate(info):
            if count < 225:
                if ctx.guild.get_member(int(user["_id"])):
                    string += f'**{count}:  {str(ctx.guild.get_member(int(user["_id"])))}** - {str(round(user["weekly"]))} XP \n'
                count += 1
                if count % 15 == 0:
                    contents[embedcount].add_field(name="Gain XP by chatting", value=string, inline=False)
                    contents[embedcount].set_footer(text=f"page {embedcount + 1} of 15")
                    embedcount += 1
                    if embedcount < 15:
                        contents.append(discord.Embed(color=0x00FF00))
                        contents[embedcount].set_author(name="Nullzee's cave leaderboard", icon_url=ctx.guild.icon_url)
                    string = ''
            else:
                for i, e in enumerate(contents):
                    e.set_footer(text=f"page {i + 1} of {len(contents)}")
                msg = await ctx.send(embed=contents[0])
                pages = Paginator(self.bot, msg, embeds=contents, timeout=180, use_extend=True, only=ctx.author)
                await pages.start()
                return

    @commands.command(hidden=True)
    @commands.has_guild_permissions(manage_messages=True)
    async def weeklyReset(self, ctx):
        await ctx.send("resetting...")
        with open('users.json') as f:
            users = json.load(f)
        async for user in userColl.find({}):
            users[str(user["_id"])] = user
        if (math.trunc(time.time()) + 604800) > users["config"]["week_start"]:
            with open(f"backups/{datetime.datetime.now().strftime('%d%m%y')}.json", 'w') as f:
                json.dump(users, f)
            await userColl.update_many({}, {"$set": {"weekly": 0}})
            users["config"]["week_start"] = math.trunc(time.time())
            with open('users.json', 'w') as f:
                json.dump(users, f)
            await self.bot.get_guild(667953033929293855).get_channel(667957285837864960).send(
                embed=discord.Embed(description="Weekly XP leaderboard was reset"), color=discord.Color.blue())
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
    @commands.has_guild_permissions(manage_messages=True)
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
    @commands.has_guild_permissions(manage_messages=True)
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
    @commands.has_guild_permissions(manage_messages=True)
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

    @commands.command()
    async def leaderboard(self, ctx):
        """View the server's XP leaderboard"""
        embed = discord.Embed(color=0x00FF00).set_author(name="Nullzee's cave leaderboard", icon_url=ctx.guild.icon_url)
        count = 1
        contents = [embed]
        string = ''
        embedcount = 0
        info = [z async for z in userColl.find().sort('level', pymongo.DESCENDING)]
        for number, user in enumerate(info):
            if count < 225:
                if ctx.guild.get_member(int(user["_id"])):
                    string += f'**{count}:  {str(ctx.guild.get_member(int(user["_id"])))}** - level {str(round(user["level"]))}\n'
                count += 1
                if count % 15 == 0:
                    contents[embedcount].add_field(name="Gain XP by chatting", value=string, inline=False)
                    contents[embedcount].set_footer(text=f"page {embedcount + 1} of 15")
                    embedcount += 1
                    if embedcount < 15:
                        contents.append(discord.Embed(color=0x00FF00))
                        contents[embedcount].set_author(name="Nullzee's cave leaderboard", icon_url=ctx.guild.icon_url)
                    string = ''
            else:
                for i, e in enumerate(contents):
                    e.set_footer(text=f"page {i + 1} of {len(contents)}")
                msg = await ctx.send(embed=contents[0])
                pages = Paginator(self.bot, msg, embeds=contents, timeout=180, use_extend=True, only=ctx.author)
                await pages.start()
                return


def setup(bot):
    bot.add_cog(level(bot, False))
