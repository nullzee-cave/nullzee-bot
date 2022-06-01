from helpers.events import Emitter
from perks.perk_system import perk, PerkError
from discord.ext import commands
import discord
from api_key import user_coll
from helpers.utils import get_user, Embed, get_file_json, save_file_json, list_one
from helpers.constants import Role, Channel
import datetime
import asyncio
import time

last_ping = 0
last_rainbow = 0
staff_nick_changes = {}


@perk(name="AskNullzee", aliases=["NullzeeQuestion", "askNull"], description="Ask Nullzee a question!",
      cost=10, require_arg=True)
async def ask_nullzee(ctx, arg):
    embed = Embed(ctx.author, description=arg)
    await embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url).user_colour()
    msg = await ctx.guild.get_channel(Channel.ASK_NULLZEE).send(embed=embed)
    await ctx.send(embed=await Embed(ctx.author, title="Bought!", url=msg.jump_url).user_colour())


@perk(name="EmbedColour", aliases=["embedcolor", "commandcolour"], description="Change the colour of your embeds!",
      cost=7, require_arg=True)
async def embed_colour(ctx, arg):
    if not (len(arg.replace("#", "")) == 6):
        raise PerkError(embed=discord.Embed(title="Error!", description="please specify a valid hex code",
                                            color=discord.Color.red()))
    await get_user(ctx.author)
    await user_coll.update_one({"_id": str(ctx.author.id)}, {"$set": {"embed_colour": arg.replace("#", "")}})


@perk(name="DeadChatPing", aliases=["deadchat", "ping", "revive", "dcp"],
      description=f"Ping <@&{Role.DEAD_CHAT_PING}> with a topic of your choice!", cost=10, require_arg=True)
async def dead_chat(ctx, arg):
    global last_ping
    if ctx.channel.slowmode_delay > 5:
        raise PerkError(msg="You cannot use that here")
    if last_ping + 7200 > time.time():
        raise PerkError(msg="This perk is on cooldown!")
    embed = Embed(ctx.author, description=arg)
    await embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url).user_colour()
    await ctx.send(f"<@&{Role.DEAD_CHAT_PING}>", embed=embed)
    last_ping = time.time()


@perk(name="QOTD", description="Choose today's QOTD!", cost=10, require_arg=True)
async def qotd(ctx, arg):
    if (config := get_file_json("config"))["qotd"] >= (
                  datetime.datetime.now() - datetime.datetime.utcfromtimestamp(0)).days:
        raise PerkError(msg="Error! QOTD has already been marked as done today")
    config["qotd"] = (datetime.datetime.now() - datetime.datetime.utcfromtimestamp(0)).days
    save_file_json(config, "config")
    embed = discord.Embed(description=arg, color=discord.Color.orange())
    embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
    await ctx.guild.get_channel(Channel.STAFF_CHAT).send(embed=embed)


@perk(name="waste", description="Waste your hard earned points!", cost="dynamic", require_arg=True)
async def waste(ctx, arg):
    try:
        val = int(arg)
    except ValueError as e:
        raise commands.UserInputError() from e
    if val < 1:
        raise PerkError(msg="Nope, you can't give yourself points.")
    exact_funnies = {
        69: "nice.",
        420: "NIIIIIIIIIIIIICE"
    }
    idiocy_scale = {
        1: "{} is dumb",
        5: "{} is stupid",
        10: "{} is an idiot",
        25: "{} has some brain damage",
        50: "{} has a deep fried brain",
        100: "{} is still a fetus",
        150: "disabled people feel sorry for {}",
        300: "{} is a danger to society",
        500: "{} cannot read for their life",
        1000: "WHERE DID {} GET THIS MANY POINTS"
    }
    if val in exact_funnies:
        await ctx.send(exact_funnies[val])
        return val
    idiocy_level = 1
    for idiocy_milestone in idiocy_scale:
        if val < idiocy_milestone:
            break
        idiocy_level = idiocy_milestone
    await ctx.send(idiocy_scale[idiocy_level].format(ctx.author.mention))
    await Emitter().emit("waste", ctx, val)
    return val


@perk(name="StaffNickChange", aliases=["bullystaff", "snc"], description="Change a Staff's nick!",
      cost=15, require_arg=True)
async def staff_nick_change(ctx, arg):
    try:
        member: discord.Member = await commands.MemberConverter().convert(ctx, arg)
    except Exception as e:
        raise e
    if not member:
        raise commands.UserInputError()
    if not member.guild_permissions.manage_messages:
        raise PerkError(msg="That user is not a staff member!")
    if member.bot:
        raise PerkError(msg="You cannot rename a bot!")
    if member.id in staff_nick_changes and staff_nick_changes[member.id] + 600 > time.time():
        raise PerkError(msg="You cannot change this staff member's nick yet, they are on cooldown.")
    await ctx.send("What do you want to change their nick to?")
    try:
        nick_change = await ctx.bot.wait_for("message",
                                             check=lambda msg: msg.channel.id == ctx.channel.id and
                                                               msg.author.id == ctx.author.id,
                                             timeout=60)
    except asyncio.TimeoutError:
        raise PerkError(msg="timed out")
    content = nick_change.content
    if len(content) >= 30:
        raise PerkError(msg="This nick is too long!")
    elif content.count("nigg") >= 1:
        await ctx.send("get banned nerd")
    else:
        try:
            if list_one(member.roles, [ctx.guild.get_role(Role.STAFF), ctx.guild.get_role(Role.TRAINEE)]):
                await member.edit(nick=f"✰ {content}")
            else:
                raise PerkError(msg="I can't change a twitch mod's nick!")
            staff_nick_changes[member.id] = time.time()
        except discord.Forbidden:
            raise PerkError(msg="I can't change an admin's nick!")
        try:
            await member.send(f"{ctx.author} changed your nick to {content} btw")
        except discord.Forbidden:
            pass


@perk(name="rainbow", aliases=["rolecolour"], description=f"Change the colour of the <@&{Role.RAINBOW}> role",
      cost=10, require_arg=True)
async def rainbow_role(ctx: commands.Context, arg: str):
    global last_rainbow
    if time.time() - last_rainbow < 60 * 15:
        raise PerkError(msg="This perk is on cooldown!")
    try:
        colour: discord.Colour = await commands.ColourConverter().convert(ctx, arg)
    except commands.BadArgument as e:
        raise PerkError(msg="Invalid colour") from e
    await ctx.guild.get_role(Role.RAINBOW).edit(colour=colour)
    last_rainbow = time.time()
