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

from helpers import payloads
from helpers.constants import Role, Channel
from helpers.utils import stringToSeconds as sts, TimeConverter, RoleConverter, list_one, role_ids, list_every, get_user
from datetime import datetime
from EZPaginator import Paginator

from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

from api_key import userColl, giveawayColl


class Giveaway(commands.Cog, name="giveaway"):
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot
        self.auto_roll_giveaways.start()

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def create(self, ctx):
        "interactive giveaway setup"
        req = False
        role_reqs = []
        level = 0
        role_req_strategy = 1
        requirement_string = ''

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author

        await ctx.send("In which channel would you like to host the giveaway?")
        try:
            channel_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            channel = await commands.TextChannelConverter().convert(ctx, channel_msg.content)
            await ctx.send("How long will the giveaway last?")
            time_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            giveaway_time = await TimeConverter().convert(ctx, time_msg.content)
            await ctx.send("How many winners will there be?")
            winner_count_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            winner_count = int(winner_count_msg.content)
            if winner_count > 30:
                return await ctx.send("You cannot have that many winners!")
            await ctx.send("Which roles must users have in order to win? (comma-delimited list or `none`)")
            role_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            for role_string in role_msg.content.split(","):
                try:
                    role_reqs.append(await RoleConverter().convert(ctx, role_string.strip()))
                except commands.RoleNotFound:
                    pass
            if role_reqs:
                req = True
                if len(role_reqs) > 1:
                    await ctx.send("Must users have [1] all of these roles or [2] any one of them?")
                    role_req_strategy = int((await self.bot.wait_for("message", timeout=60.0, check=check)).content)

            await ctx.send("What is the minimum level that users must be in order to win?")
            level_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            if level_msg.content != "0" and level_msg.content.isdigit():
                level = int(level_msg.content)
                req = True
            if level > 70:
                return await ctx.send("That level is higher than the maximum allowed level requirement")
            await ctx.send("Must the winner be a current or previous financial supporter? `Y/N`")
            booster_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            req, booster = req, booster_msg.content.lower() == "y"
            await ctx.send("What is the giveaway for?")
            content_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            content = content_msg.content
            await ctx.send("Who funded this giveaway?")
            donor_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            donor = await commands.MemberConverter().convert(ctx, donor_msg.content)
            await ctx.send("Would you like me to ping the giveaway role? (`Y`/`N`)")
            ping_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            ping = ping_msg.content.lower() in ["yes", "y"]
        except asyncio.TimeoutError:
            return await ctx.send(f"giveaway creation timed out")
        donor_string = f"Donated by {donor.mention}" if donor else ""
        embed = discord.Embed(title=content, description=f"React with :tada: to enter!\n{donor_string}",
                              color=discord.Color.green()).set_footer(text=f"{winner_count} winners, ends at")
        giveaway_time += math.trunc(time.time())
        embed.timestamp = datetime.fromtimestamp(giveaway_time)
        if req:
            if role_reqs:
                if len(role_reqs) > 1:
                    requirement_string += "Must have the following roles: \n" if role_req_strategy == 1 else "Must have one of the following roles: \n"
                    requirement_string += "\n\t-".join([z.mention for z in role_reqs])
                else:
                    requirement_string = f"- Must have the role: {role_reqs[0].mention}\n"
            if level:
                requirement_string += f"- Must be at least level {level}"
            if booster:
                requirement_string += "- Must be a previous or current financial supporter"
            embed.add_field(name="Requirements:", value=requirement_string)
        if ping:
            msg = await channel.send("<@&735238184832860402>", embed=embed)
        else:
            msg = await channel.send(embed=embed)
        await msg.add_reaction(u"\U0001F389")
        payload = payloads.giveaway_payload(ctx, msg, channel=channel, giveaway_time=giveaway_time,
                                            winner_count=winner_count, role_req_strategy=role_req_strategy,
                                            roles=role_ids(role_reqs), level=level,
                                            booster=booster, content=content, donor=donor)
        await giveawayColl.insert_one(payload)
        await ctx.send(f"Giveaway created!\n{msg.jump_url}")
        await donor.add_roles(ctx.guild.get_role(
            Role.LARGE_GIVEAWAY_DONOR if ctx.channel.id == Channel.GIVEAWAY
            else Role.MINI_GIVEAWAY_DONOR
        ))

    async def check_requirements(self, giveaway, user):
        reqs = giveaway["requirements"]
        if reqs["booster"]:
            if not list_one(role_ids(user.roles), Role.BOOSTER, Role.TWITCH_SUB, Role.RETIRED):
                return False
        if reqs["roles"]:
            roles = [user.guild.get_role(role) for role in reqs["roles"]]
            if reqs["role_type"] == 2 and not list_one(role_ids(user.roles), *roles):
                return False
            elif reqs["role_type"] == 1 and not list_every(role_ids(user.roles), *roles):
                return False
        if reqs["level"]:
            user_data = await get_user(user)
            if user_data["level"] < reqs["level"]:
                return False
        return True

    async def roll_giveaway(self, guild, giveaway, winner_count=None):
        winner_count = winner_count or giveaway["winner_count"]
        channel = guild.get_channel(giveaway["channel"])
        message = await channel.fetch_message(int(giveaway["_id"]))
        donor = guild.get_member(giveaway["donor"])
        reaction_users = []
        if not channel or not message:
            await guild.get_channel(709820460162089061).send(f"GIVEAWAY FAILED: {giveaway['_id']}\nINTERNAL ERROR")
        for i in message.reactions:
            async for user in i.users():
                reaction_users.append(user)
        reaction_users = [z for z in reaction_users if isinstance(z, discord.Member)]
        winners = []
        await giveawayColl.update_one({"_id": giveaway["_id"]}, {"$set": {"active": False}})
        for count in range(winner_count):
            x = False
            attempts = 0
            while not x:
                this_winner = random.choice(reaction_users)
                x = await self.check_requirements(giveaway, this_winner) and this_winner not in winners
                attempts += 1
                if attempts > 50:
                    return await channel.send("Could not determine a winner.")
            winners.append(this_winner)
        embed = message.embeds[0]
        embed.set_footer(text=f"ended at:")
        embed.timestamp = datetime.now()
        winner_string = "\n".join([z.mention for z in winners])
        embed.description = f'Donated by: {donor.mention}\nWinners:{winner_string}'
        embed.colour = discord.Colour.darker_grey()
        await message.edit(embed=embed)
        await message.reply(
            f"Congratulations {', '.join([z.mention for z in winners])}, you won the **{giveaway['content']}**!!")
        for winner in winners:
            await winner.add_roles(message.guild.get_role(
                Role.LARGE_GIVEAWAY_WIN if message.channel.id == Channel.GIVEAWAY
                else Role.MINI_GIVEAWAY_WIN
            ))

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def roll(self, ctx, message: discord.Message):
        "roll a giveaway early"
        giveaway = await giveawayColl.find_one({"_id": message.id, "active": True})
        if giveaway:
            await ctx.send("rolling giveaway")
            await self.roll_giveaway(ctx.guild, giveaway)
        else:
            await ctx.send("Could not find that giveaway")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def gdelete(self, ctx, message: discord.Message):
        "delete a giveaway"
        giveaway = await giveawayColl.find_one({"active": True, "_id": message.id})
        if giveaway:
            await giveawayColl.update_one({"_id": message.id}, {"$set": {"active": False}})
            await ctx.send("Stopped the giveaway")
            try:
                msg = await ctx.guild.get_channel(int(giveaway["channel"])).fetch_message(giveaway["_id"])
                await msg.edit(content="*[giveaway deleted]*", embed=None)
            except:
                pass
        else:
            await ctx.send("Could not find that giveaway")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def reroll(self, ctx, message: discord.Message):
        "reroll one winner of a giveaway"
        giveaway = await giveawayColl.find_one({"active": False, "_id": message.id})
        if giveaway:
            await self.roll_giveaway(ctx.guild, giveaway, 1)
        else:
            await ctx.send("Could not find that giveaway")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def start(self, ctx, timer: TimeConverter, winners: str, donor: discord.Member, *, prize: str):
        "quickly start a giveaway with limited options"
        winners = int(winners.replace('w', ''))
        if winners > 10:
            return
        embed = discord.Embed(title=prize, description=f"React with :tada: to enter!\nDonated by {donor.mention}",
                              color=discord.Color.green()).set_footer(text=f"{winners} winners, ends at")
        timer += math.trunc(time.time())
        embed.timestamp = datetime.fromtimestamp(timer)
        msg = await ctx.channel.send(embed=embed)
        await msg.add_reaction(u"\U0001F389")
        payload = payloads.giveaway_payload(ctx, msg, channel=ctx.channel, giveaway_time=timer,
                                            winner_count=winners,
                                            content=prize, donor=donor)
        await giveawayColl.insert_one(payload)
        await ctx.message.delete()

    @tasks.loop(minutes=2)
    async def auto_roll_giveaways(self):
        giveaways = [z async for z in giveawayColl.find({"active": True})]
        for giveaway in giveaways:
            if time.time() > giveaway["ends"]:
                guild = self.bot.get_guild(667953033929293855)
                try:
                    await self.roll_giveaway(guild, giveaway)
                except Exception as e:
                    print("exception occurred rolling giveaway: {0.__class.__name__}\n-\n{0}--".format(e))


def setup(bot):
    bot.add_cog(Giveaway(bot, True))
