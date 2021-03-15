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

from helpers.constants import Role, Channel
from helpers.utils import stringToSeconds as sts
from datetime import datetime
from EZPaginator import Paginator

from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

from api_key import userColl, giveawayColl


class giveaway(commands.Cog, name="giveaway"):
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot
        self.giveawayCheck.start()

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def create(self, ctx):
        "interactive giveaway setup"
        req = False
        reqstring = ''
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author
        await ctx.send("In which channel would you like to host the giveaway?")
        try:
            channelmsg = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Giveaway creation timed out")
        if channelmsg.channel_mentions:
            channel = channelmsg.channel_mentions[0]
        else:
            channel = discord.utils.get(ctx.guild.channels, name=channelmsg.content)
        if not channel:
            return await ctx.send("Could not find that channel. Giveaway creation cancelled")
        await ctx.send("How long will the giveaway last?")
        try:
            timemsg = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Giveaway creation timed out")
        giveawayTime = sts(timemsg.content)
        if not giveawayTime:
            return await ctx.send("Could not work out that time. Giveaway creation cancelled")
        await ctx.send("How many winners will there be?")
        try:
            winnerCountMsg = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Giveaway creation timed out")
        winnerCount = int(winnerCountMsg.content)
        if winnerCount > 30:
            return
        await ctx.send("Which role must users have in order to win?")
        try:
            rolemsg = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Giveaway creation timed out")
        if rolemsg.role_mentions:
            role = rolemsg.role_mentions[0]
            roleid = role.id
            reqstring += f'Must have the {role.mention} role\n'
            req = True
        else:
            role = discord.utils.get(ctx.guild.roles, name=rolemsg.content)
            if role:
                reqstring += f'Must have the {role.mention} role\n'
                roleid = role.id
                req = True
            else:
                roleid = None
        await ctx.send("What is the minimum level that users must be in order to win?")
        try:
            levelmsg = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Giveaway creation timed out")
        if levelmsg.content != "0":
            try:
                level = int(levelmsg.content)
                req = True
                reqstring += f'Must be at least level {level}\n'
            except ValueError:
                return await ctx.send("That's not a number well done")
        else:
            level = 0
        if level > 70:
            return
        await ctx.send("Must the winner be a current or previous server booster? `Y/N`")
        try:
            boosterMsg = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Giveaway creation timed out")
        if boosterMsg.content.lower() == "y":
            req = True
            booster = True
            reqstring += "Must be a current or previous server booster\n"
        else:
            booster = False
        await ctx.send("What is the giveaway for?")
        try:
            contentmsg = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Giveaway creation timed out")
        content = contentmsg.content
        await ctx.send("Who funded this giveaway?")
        try:
            donormsg = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Giveaway creation timed out")
        if donormsg.mentions:
            donor = donormsg.mentions[0]
        else:
            return await ctx.send("You did not mention a user. Giveaway creation cancelled")
        await ctx.send("Would you like me to ping the giveaway role? (`Y`/`N`)")
        try:
            pingmsg = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Giveaway creation timed out")
        if pingmsg.content.lower() == "yes" or pingmsg.content.lower() == "y":
            ping = True
        else:
            ping = False
        if donor:
            donstring = f"Donated by: {donor.mention}"
        else:
            donstring = ''
        embed = discord.Embed(title=content, description=f"React with :tada: to enter!\n{donstring}", color=discord.Color.green()).set_footer(text=f"{winnerCount} winners, ends at")
        giveawayTime += math.trunc(time.time())
        embed.timestamp = datetime.fromtimestamp(giveawayTime)
        if req:
            embed.add_field(name="Requirements:", value=reqstring)
        if ping:
            msg = await channel.send("<@&735238184832860402>", embed=embed)
        else:
            msg = await channel.send(embed=embed)
        await msg.add_reaction(u"\U0001F389")
        payload = {"_id": msg.id, "active": True, "mod": ctx.author.id, "channel": channel.id, "ends": giveawayTime, "winnercount": winnerCount, "role": roleid, "level": level, "booster": booster, "content": content, "donor": donor.id}
        await ctx.send(f"Giveaway created!\n{msg.jump_url}")
        await donor.add_roles(ctx.guild.get_role(
            Role.LARGE_GIVEAWAY_DONOR if ctx.channel.id == Channel.GIVEAWAY
            else Role.MINI_GIVEAWAY_DONOR
        ))

    async def reqcheck(self, giveaway, user):
        if giveaway["booster"]:
            if 668724083718094869 in [z.id for z in user.roles] or 706285767898431500 in [z.id for z in user.roles]:
                booster = True
            else:
                booster = False
        else:
            booster = True
        if giveaway["role"]:
            if giveaway["role"] in [z.id for z in user.roles]:
                role = True
            else:
                return False
        else:
            role = True
        if giveaway["level"]:

            try:
                #if users[str(user.id)]["level"] >= giveaway["level"]:
                if (userData := await userColl.find_one({"_id": str(user.id)})) and userData["level"] >= giveaway["level"]:
                    level = True
                else:
                    level = False
            except KeyError:
                level = False
        else:
            level = True
        return role and level and booster


    async def rollGiveaway(self, guild, giveaway):
        channel = guild.get_channel(giveaway["channel"])
        message = await channel.fetch_message(int(id))
        donor = guild.get_member(giveaway["donor"])
        reactionusers = []
        if not channel or not message:
            await guild.get_channel(709820460162089061).send(f"GIVEAWAY FAILED: {id}\nINTERNAL ERROR")
        for i in message.reactions:
            async for user in i.users():
                reactionusers.append(user)
        #reactions = [z.user for z in message.reactions if str(z.emoji) == u"\U0001F389"]
        reactionusers = [z for z in reactionusers if isinstance(z, discord.Member)]
        winners = []
        winrole = guild.get_role(672141836567183413)
        for count in range(giveaway["winnercount"]):
            # print(f"{count} something here")
            x = False
            attempts = 0
            while not x:
                thisWinner = random.choice(reactionusers)
                x = await self.reqcheck(giveaway, thisWinner) and thisWinner not in winners
                attempts += 1
                if attempts > 50:
                    return await channel.send("Could not determine a winner.")
            winners.append(thisWinner)
            await thisWinner.add_roles(winrole)
        winnerstring = "\n".join([z.mention for z in winners])
        embed = message.embeds[0]
        embed.set_footer(text=f"ended at:")
        embed.timestamp = datetime.now()
        embed.description = f'Donated by: {donor.mention}\nWinners:{winnerstring}'
        embed.color = discord.Color.darker_grey()
        await message.edit(embed=embed)
        await message.reply(f"Congratulations {', '.join([z.mention for z in winners])}, you won the **{giveaway['content']}**!!")
        await giveawayColl.update_one({"_id": giveaway["_id"]}, {"$set": {"active": False}})
        for winner in winners:
            await winner.add_roles(message.guild.get_role(
                Role.LARGE_GIVEAWAY_WIN if message.channel.id == Channel.GIVEAWAY
                else Role.MINI_GIVEAWAY_WIN
            ))
        # with open('giveaways.json', 'w') as f:
        #     json.dump(giveaways, f)
    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def roll(self, ctx, id:int):
        "roll a giveaway early"
        giveaways = [z async for z in giveawayColl.find({"active": True})]
        for giveaway in giveaways:
            if id == giveaway["_id"]:
                await self.rollGiveaway(ctx.guild, giveaway)
                await ctx.send("rolling giveaway")
            else:
                await ctx.send("Could not find that giveaway")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def gdelete(self, ctx, id:int):
        "delete a giveaway"
        giveaways = [z async for z in giveawayColl.find({"active": True})]
        for giveaway in giveaways:
            if id == giveaway["_id"]:
                await giveawayColl.update_one({"_id": id}, {"$set": {"active": False}})
                await ctx.send("Stopped the giveaway")
                try:
                    msg = await ctx.guild.get_channel(int(giveaway["channel"])).fetch_message(giveaway["_id"])
                    await msg.edit(content="*[giveaway deleted]*")
                except:
                    pass
            else:
                await ctx.send("Could not find that giveaway")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def reroll(self, ctx, id:int):
        "reroll one winner of a giveaway"
        giveaways = [z async for z in giveawayColl.find({"active": False})]
        for giveaway in giveaways:
            if id == giveaway["_id"]:
                #await self.rollGiveaway(ctx.guild, giveaways, id)
                await ctx.send("rolling giveaway")
                winners = []
                channel = ctx.guild.get_channel(giveaway["channel"])
                message = await channel.fetch_message(id)
                donor = ctx.guild.get_member(giveaway["donor"])
                reactionusers = []
                for i in message.reactions:
                    async for user in i.users():
                        reactionusers.append(user)
                x = False
                attempts = 0
                while not x:
                    attempts += 1
                    if attempts > 30:
                        return await channel.send("Could not determine a winner")
                    thisWinner = random.choice(reactionusers)
                    x = await self.reqcheck(giveaway, thisWinner) if not thisWinner.bot else False
                await thisWinner.add_roles(ctx.guild.get_role(672141836567183413))
                winners = [thisWinner]
                winnerstring = "\n".join([z.mention for z in winners])
                embed = message.embeds[0]
                embed.set_footer(text=f"ended at:")
                embed.timestamp = datetime.now()
                embed.title += " (rerolled)"
                embed.color = discord.Color.darker_grey()
                await message.edit(embed=embed)
                await message.reply(f"Congratulations {', '.join([z.mention for z in winners])}, you won the **{giveaway['content']}**!!")
                for winner in winners:
                    await winner.add_roles(ctx.guild.get_role(
                        Role.LARGE_GIVEAWAY_WIN if ctx.channel.id == Channel.GIVEAWAY
                        else Role.MINI_GIVEAWAY_WIN
                    ))
            else:
                await ctx.send("Could not find that giveaway")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def start(self, ctx, timer:str, winners:str, donor:discord.Member, *, prize:str):
        "quickly start a giveaway with limited options"
        giveawayTime = sts(timer)
        winners = winners.replace('w', '')
        if int(winners) > 10:
            return
        donstring = f"Donated by {donor.mention}"
        embed = discord.Embed(title=prize, description=f"React with :tada: to enter!\n{donstring}", color=discord.Color.green()).set_footer(text=f"{winners} winners, ends at")
        giveawayTime += math.trunc(time.time())
        embed.timestamp = datetime.fromtimestamp(giveawayTime)
        msg = await ctx.channel.send(embed=embed)
        await msg.add_reaction(u"\U0001F389")
        payload = {"_id": msg.id, "active": True, "mod": ctx.author.id, "channel": ctx.channel.id, "ends": giveawayTime, "winnercount": int(winners), "role": None, "level": None, "content": prize, "donor": donor.id}
        await giveawayColl.insert_one(payload)
        await ctx.message.delete()

    @tasks.loop(minutes=2)
    async def giveawayCheck(self):
        giveaways = [z async for z in giveawayColl.find({"active": True})]
        active_giveaways = {}
        for giveaway in giveaways:
            if time.time() > giveaway["ends"]:
                guild = self.bot.get_guild(667953033929293855)
                await giveawayColl.update_one({"_id": giveaway["_id"]}, {"$set": {"active": False}})
                try:
                    await self.rollGiveaway(guild, giveaway)
                except Exception as e:
                    print("exception occurred rolling giveaway: {0.__class.__name__}\n-\n{0}--".format(e))
            

def setup(bot):
    bot.add_cog(giveaway(bot, True))
