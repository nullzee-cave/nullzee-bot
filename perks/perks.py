from helpers.events import Emitter
from perks.perkSystem import perk, PerkError
from discord.ext import commands
import discord
from api_key import userColl
from helpers.utils import get_user, Embed, getFileJson, saveFileJson
import datetime
import asyncio
import time

last_ping = 0
staff_nick_changes = {}

@perk(name="AskNullzee", description="Ask Nullzee a question!", cost=10, aliases=["NullzeeQuestion", "askNull"],
      require_arg=True)
async def askNullzee(ctx, arg):
    msg = await ctx.guild.get_channel(738350726417219645).send(
        embed=await Embed(ctx.author, description=arg)
            .set_author(name=ctx.author, icon_url=ctx.author.avatar_url).user_colour())
    await ctx.send(embed=await Embed(ctx.author, title="Bought!", url=msg.jump_url).user_colour())


@perk(name="embedColour", description="Change the colour of your embeds!", cost=7,
      aliases=["embedColor", "commandColour"], require_arg=True)
async def embedColour(ctx, arg):
    if not (len(arg.replace('#', '')) == 6):
        raise PerkError(embed=discord.Embed(title="Error!", description="please specify a valid hex code",
                                            color=discord.Color.red()))
    await get_user(ctx.author)
    await userColl.update_one({"_id": str(ctx.author.id)}, {"$set": {"embed_colour": arg.replace('#', '')}})


@perk(name="deadChatPing", description="Ping <@&749178299518943343> with a topic of your choice!", cost=10,
      aliases=["deadchat", "ping","revive"], require_arg=True)
async def deadChat(ctx, arg):
    global last_ping
    if ctx.channel.slowmode_delay > 5:
        raise PerkError(msg="You cannot use that here")
    if last_ping + 1800 > time.time():
        raise PerkError(msg="This perk is on cooldown!")
    await ctx.send("<@&749178299518943343>", embed=await Embed(ctx.author, description=arg).set_author(name=ctx.author,
                                                                                                       icon_url=ctx.author.avatar_url).user_colour())
    last_ping = time.time()

@perk(name="qotd", description="Choose today's QOTD!", cost=10, require_arg=True)
async def qotd(ctx, arg):
    if (config := getFileJson('config'))["qotd"] >= (datetime.datetime.now() - datetime.datetime.utcfromtimestamp(0)).days:
        raise PerkError(msg="Error! QOTD has already been marked as done today")
    config["qotd"] = (datetime.datetime.now() - datetime.datetime.utcfromtimestamp(0)).days
    saveFileJson(config, 'config')
    embed = discord.Embed(description=arg, color=discord.Color.orange()).set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
    await ctx.guild.get_channel(668723004213166080).send(embed=embed)

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

@perk(name="staffNickChange", description = "Change a Staff's nick!", cost= 15, require_arg = True, aliases = ["bullyStaff","snc"])
async def staffNickChange(ctx, arg):
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
    if member.id in staff_nick_changes and staff_nick_changes[member.id]+600>time.time():
        raise PerkError(msg="You cannot change this staff member's nick yet, they are on cooldown.")
    await ctx.send("What do you want to change their nick to?")
    try:
        nickChange = await ctx.bot.wait_for('message', check=lambda msg: msg.channel.id == ctx.channel.id and msg.author.id == ctx.author.id, timeout=60)
    except asyncio.TimeoutError:
        raise PerkError(msg="timed out")
    content = nickChange.content
    if len(content) >= 30:
        raise PerkError(msg='This nick is too long!')
    elif content.count('nigg') >= 1:
        await ctx.send('get banned nerd')
    else:
        try:
            if ctx.guild.get_role(667953757954244628) in member.roles or ctx.guild.get_role(675031583954173986) in member.roles:
                await member.edit(nick=f'✰ {content}')
            else:
                raise PerkError("I can't change a twitch mod's nick!")
            staff_nick_changes[member.id] = time.time()
        except discord.Forbidden:
            raise PerkError(msg="I can't change an admin's nick!")
        try:
            await member.send(f'{ctx.author} changed your nick to {content} btw')
        except discord.Forbidden:
            pass

