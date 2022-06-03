from discord.ext import commands, tasks
import asyncio
import discord
import random
import time
import math
import traceback

from helpers import payloads
from helpers.constants import Role, Channel, Misc
from helpers.utils import TimeConverter, RoleConverter, list_one, role_ids, list_every, \
    get_user, GiveawayError, staff_or_trainee
from datetime import datetime

from api_key import DEV_ID


class Giveaway(commands.Cog, name="Giveaway"):
    """The giveaway system, and all related commands"""

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot
        self.auto_roll_giveaways.start()

    async def get_input(self, ctx):
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author
        try:
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            if msg.content.lower() == "cancel":
                raise GiveawayError("Giveaway creation cancelled")
        except asyncio.TimeoutError:
            raise GiveawayError("Giveaway creation timed out!")
        return msg

    @commands.command(hidden=True)
    @staff_or_trainee
    async def create(self, ctx):
        """Interactive giveaway setup"""
        req = False
        role_reqs = []
        level = 0
        role_req_strategy = 1
        requirement_string = ""

        await ctx.send("In which channel would you like to host the giveaway?")
        channel_msg = await self.get_input(ctx)
        channel = await commands.TextChannelConverter().convert(ctx, channel_msg.content)

        await ctx.send("How long will the giveaway last?")
        time_msg = await self.get_input(ctx)
        giveaway_time = await TimeConverter().convert(ctx, time_msg.content)
        if giveaway_time < 10800 or \
          (giveaway_time > 604800 and channel.id not in [Channel.GIVEAWAY, Channel.STAFF_ANNOUNCEMENTS]) or \
          (giveaway_time > 1209600 and channel.id in [Channel.GIVEAWAY, Channel.STAFF_ANNOUNCEMENTS]):
            return await ctx.send(
                "Giveaways can last a minimum of 3 hours and a maximum of 1 week (or 2 for large giveaways).")

        await ctx.send("How many winners will there be?")
        winner_count_msg = await self.get_input(ctx)
        winner_count = int(winner_count_msg.content)
        if winner_count > 30:
            return await ctx.send("You cannot have that many winners!")

        await ctx.send("Which roles must users have in order to win? (comma-delimited list or `none`)")
        role_msg = await self.get_input(ctx)
        for role_string in role_msg.content.split(","):
            try:
                role_reqs.append(await RoleConverter().convert(ctx, role_string.strip()))
            except commands.RoleNotFound:
                pass

        if role_reqs:
            req = True
            if len(role_reqs) > 1:
                await ctx.send("Must users have [1] all of these roles or [2] any one of them?")
                role_req_strategy = await self.get_input(ctx)
                role_req_strategy = int(role_req_strategy.content)

        await ctx.send("What is the minimum level that users must be in order to win?")
        level_msg = await self.get_input(ctx)
        if level_msg.content != "0" and level_msg.content.isdigit():
            level = int(level_msg.content)
            req = True
        if level > 70:
            return await ctx.send("That level is higher than the maximum allowed level requirement")

        await ctx.send("Must the winner be a current or previous financial supporter? `Y/N`")
        booster_msg = await self.get_input(ctx)
        req, booster = req, booster_msg.content.lower() == "y"

        await ctx.send("What is the giveaway for?")
        content_msg = await self.get_input(ctx)
        content = content_msg.content

        await ctx.send("Who funded this giveaway?")
        donor_msg = await self.get_input(ctx)
        donor = await commands.MemberConverter().convert(ctx, donor_msg.content)

        await ctx.send("Would you like me to ping the giveaway role? (`Y`/`N`)")
        ping_msg = await self.get_input(ctx)
        ping = ping_msg.content.lower() in ["yes", "y"]

        donor_string = f"Donated by {donor.mention}" if donor else ""
        embed = discord.Embed(title=content, description=f"React with :tada: to enter!\n{donor_string}",
                              color=discord.Color.green()).set_footer(text=f"{winner_count} winners, ends at")
        giveaway_time += math.trunc(time.time())
        embed.timestamp = datetime.fromtimestamp(giveaway_time)
        if req:
            if role_reqs:
                if len(role_reqs) > 1:
                    requirement_string += "Must have the following roles: \n" if role_req_strategy == 1 else \
                                          "Must have one of the following roles: \n"
                    requirement_string += "\n".join([f"-{z.mention}" for z in role_reqs]) + "\n"
                else:
                    requirement_string = f"- Must have the role: {role_reqs[0].mention}\n"
            if level:
                requirement_string += f"- Must be at least level {level}\n"
            if booster:
                requirement_string += "- Must be a previous or current financial supporter\n"
            embed.add_field(name="Requirements:", value=requirement_string)
        if ping:
            msg = await channel.send(f"<@&{Role.GIVEAWAY_PING}>", embed=embed)
        else:
            msg = await channel.send(embed=embed)
        await msg.add_reaction(u"\U0001F389")
        payload = payloads.giveaway_payload(ctx, msg, channel=channel, giveaway_time=giveaway_time,
                                            winner_count=winner_count, role_req_strategy=role_req_strategy,
                                            roles=role_ids(role_reqs), level=level,
                                            booster=booster, content=content, donor=donor)
        await self.bot.giveaway_coll.insert_one(payload)
        await ctx.send(f"Giveaway created!\n{msg.jump_url}")
        await donor.add_roles(ctx.guild.get_role(
            Role.GODLY_GIVEAWAY_DONOR if ctx.channel.id == Channel.GIVEAWAY
            else Role.MINI_GIVEAWAY_DONOR
        ))

    @commands.command(hidden=True)
    @staff_or_trainee
    async def roll(self, ctx, message: discord.Message):
        """Roll a giveaway early"""
        giveaway = await self.bot.giveaway_coll.find_one({"_id": str(message.id), "active": True})
        if giveaway:
            await ctx.send("rolling giveaway")
            await self.roll_giveaway(ctx.guild, giveaway)
        else:
            await ctx.send("Could not find that giveaway")

    @commands.command(name="gdelete", hidden=True)
    @staff_or_trainee
    async def delete_giveaway(self, ctx, message: discord.Message):
        """Delete a giveaway"""
        giveaway = await self.bot.giveaway_coll.find_one({"active": True, "_id": str(message.id)})
        if giveaway:
            await self.bot.giveaway_coll.update_one({"_id": str(message.id)}, {"$set": {"active": False}})
            await ctx.send("Stopped the giveaway")
            try:
                msg = await ctx.guild.get_channel_or_thread(int(giveaway["channel"])).fetch_message(int(giveaway["_id"]))
                await msg.edit(content="*[giveaway deleted]*", embed=None)
            except:
                pass
        else:
            await ctx.send("Could not find that giveaway")

    @commands.command(name="gdeleteid", hidden=True)
    @staff_or_trainee
    async def delete_giveaway_by_id(self, ctx, _id: int):
        """
        Delete a giveaway by ID

        Added so I can stop manually deleting them when someone
        doesn't use the command and the bot starts throwing errors
        """
        giveaway = await self.bot.giveaway_coll.find_one({"active": True, "_id": str(_id)})
        if giveaway:
            await self.bot.giveaway_coll.update_one({"_id": str(_id)}, {"$set": {"active": False}})
            await ctx.send("Stopped the giveaway")
            try:
                msg = await ctx.guild.get_channel_or_thread(int(giveaway["channel"])).fetch_message(int(giveaway["_id"]))
                await msg.edit(content="*[giveaway deleted]*", embed=None)
            except discord.NotFound:
                pass
        else:
            await ctx.send("Could not find that giveaway")

    @commands.command(name="reroll", hidden=True)
    @staff_or_trainee
    async def reroll_giveaway(self, ctx, message: discord.Message):
        """Reroll one winner of a giveaway"""
        giveaway = await self.bot.giveaway_coll.find_one({"active": False, "_id": str(message.id)})
        if giveaway:
            await self.roll_giveaway(ctx.guild, giveaway, 1)
        else:
            await ctx.send("Could not find that giveaway")

    @commands.command(name="start", hidden=True)
    @commands.has_role(Role.ADMIN)
    async def start_giveaway(self, ctx, timer: TimeConverter, winners: str, donor: discord.Member, *, prize: str):
        """Quickly start a giveaway with limited options"""
        winners = int(winners.replace("w", ""))
        if winners > 10:
            return
        embed = discord.Embed(title=prize, description=f"React with :tada: to enter!\nDonated by {donor.mention}",
                              color=discord.Color.green())
        embed.set_footer(text=f"{winners} winners, ends at")
        timer += math.trunc(time.time())
        embed.timestamp = datetime.fromtimestamp(timer)
        msg = await ctx.channel.send(embed=embed)
        await msg.add_reaction(u"\U0001F389")
        payload = payloads.giveaway_payload(ctx, msg, channel=ctx.channel, giveaway_time=timer,
                                            winner_count=winners, content=prize, donor=donor)
        await self.bot.giveaway_coll.insert_one(payload)
        await ctx.message.delete()

    @tasks.loop(minutes=2)
    async def auto_roll_giveaways(self):
        giveaways = [z async for z in self.bot.giveaway_coll.find({"active": True})]
        for giveaway in giveaways:
            if time.time() > giveaway["ends"]:
                guild = self.bot.get_guild(Misc.GUILD)
                try:
                    await self.roll_giveaway(guild, giveaway)
                except Exception as e:
                    await self.bot.get_guild(Misc.GUILD).get_member(DEV_ID).send(f"\nGiveaway failed to roll: `{giveaway['_id']}`")
                    print(f"\nGiveaway failed to roll: {giveaway['_id']}")
                    print("".join(traceback.format_exception(type(e), e, e.__traceback__)))

    @auto_roll_giveaways.before_loop
    async def before_auto_roll_giveaways(self):
        await self.bot.wait_until_ready()

    async def check_requirements(self, giveaway, user):
        reqs = giveaway["requirements"]
        if reqs["booster"]:
            if not list_one(role_ids(user.roles), Role.BOOSTER, Role.TWITCH_SUB, Role.RETIRED_SUPPORTER):
                return False
        if reqs["roles"]:
            if reqs["role_type"] == 2 and not list_one(role_ids(user.roles), *reqs["roles"]):
                return False
            elif reqs["role_type"] == 1 and not list_every(role_ids(user.roles), *reqs["roles"]):
                return False
        if reqs["level"]:
            user_data = await get_user(self.bot, user)
            if user_data["level"] < reqs["level"]:
                return False
        return True

    async def roll_giveaway(self, guild, giveaway, winner_count=None):
        winner_count = winner_count or giveaway["winner_count"]
        channel = guild.get_channel_or_thread(giveaway["channel"])
        message = await channel.fetch_message(int(giveaway["_id"]))
        donor = guild.get_member(giveaway["donor"])
        reaction_users = []
        if not channel or not message:
            await guild.get_channel(Channel.STAFF_ANNOUNCEMENTS).send(
                f"GIVEAWAY FAILED: {giveaway['_id']}\nINTERNAL ERROR")
        for reaction in message.reactions:
            async for user in reaction.users():
                reaction_users.append(user)
        reaction_users = [z for z in reaction_users if isinstance(z, discord.Member)]
        winners = []
        await self.bot.giveaway_coll.update_one({"_id": giveaway["_id"]}, {"$set": {"active": False}})
        for count in range(winner_count):
            x = False
            attempts = 0
            while not x:
                this_winner = random.choice(reaction_users)
                x = await self.check_requirements(giveaway, this_winner) and this_winner not in winners
                attempts += 1
                if attempts > 50:
                    return await message.reply("Could not determine a winner.")
            winners.append(this_winner)
        embed = message.embeds[0]
        embed.set_footer(text=f"ended at:")
        embed.timestamp = datetime.now()
        winner_string = "\n".join([z.mention for z in winners])
        embed.description = f"Donated by: {donor.mention}\nWinners:{winner_string}"
        embed.colour = discord.Colour.darker_grey()
        await message.edit(embed=embed)
        await message.reply(
            f"Congratulations {', '.join([z.mention for z in winners])}, you won the **{giveaway['content']}**!!")
        for winner in winners:
            await winner.add_roles(message.guild.get_role(
                Role.LARGE_GIVEAWAY_WIN if message.channel.id == Channel.GIVEAWAY
                else Role.MINI_GIVEAWAY_WIN
            ))


async def setup(bot):
    await bot.add_cog(Giveaway(bot, True))
