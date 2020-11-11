from perks.perkSystem import perk, PerkError
from discord.ext import commands
import discord
from api_key import userColl
from helpers.utils import get_user, Embed, getFileJson, saveFileJson
import datetime
import asyncio


@perk(name="AskNullzee", description="Ask Nullzee a question!", cost=5, aliases=["NullzeeQuestion", "askNull"],
      require_arg=True)
async def askNullzee(ctx, arg):
    msg = await ctx.guild.get_channel(738350726417219645).send(
        embed=await Embed(ctx.author, description=arg)
            .set_author(name=ctx.author, icon_url=ctx.author.avatar_url).user_colour())
    await ctx.send(embed=await Embed(ctx.author, title="Bought!", url=msg.jump_url).user_colour())


@perk(name="embedColour", description="Change the colour of your embeds!", cost=10,
      aliases=["embedColor", "commandColour"], require_arg=True)
async def embedColour(ctx, arg):
    if not (len(arg.replace('#', '')) == 6):
        raise PerkError(embed=discord.Embed(title="Error!", description="please specify a valid hex code",
                                            color=discord.Color.red()))
    await get_user(ctx.author)
    await userColl.update_one({"_id": str(ctx.author.id)}, {"$set": {"embed_colour": arg.replace('#', '')}})


@perk(name="deadChatPing", description="Ping <@&749178299518943343> with a topic of your choice!", cost=15,
      aliases=["deadchat", "ping"], require_arg=True)
async def deadChat(ctx, arg):
    if ctx.channel.slowmode_delay > 5:
        raise PerkError(msg="You cannot use that here")
    await ctx.send("<@&749178299518943343>", embed=await Embed(ctx.author, description=arg).set_author(name=ctx.author,
                                                                                                       icon_url=ctx.author.avatar_url).user_colour())

@perk(name="qotd", description="Choose today's QOTD!", cost=10, require_arg=True)
async def qotd(ctx, arg):
    if (config := getFileJson('config'))["qotd"] >= (datetime.datetime.now() - datetime.datetime.utcfromtimestamp(0)).days:
        raise PerkError(msg="Error! QOTD has already been marked as done today")
    config["qotd"] = (datetime.datetime.now() - datetime.datetime.utcfromtimestamp(0)).days
    saveFileJson(config, 'config')
    embed = discord.Embed(description=arg, color=discord.Color.orange()).set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
    await ctx.guild.get_channel(668723004213166080).send(embed=embed)

@perk(name="waste", description="Waste your hard earned points!", cost=1)
async def waste(ctx, arg):
    await ctx.send(f"{ctx.author.mention} is a dumbass")

@perk(name="staffNickChange", description = "Change a Staff's nick!", cost= 10, require_arg = True, aliases = ["bullyStaff","snc"])
async def staffNickChange(ctx, arg):
    try:
        member: discord.Member = await commands.MemberConverter().convert(ctx, arg)
    except Exception as e:
        raise e
    if not member:
        raise commands.UserInputError()
    await ctx.send("What do you want to change their nick to?")
    if not member.guild_permissions.manage_messages:
        raise PerkError(msg="That user is not a staff member!")
    try:
        nickChange = await ctx.bot.wait_for('message', check=lambda msg: msg.channel.id == ctx.channel.id and msg.author.id == ctx.author.id)
    except asyncio.TimeoutError:
        raise PerkError(msg="timed out")
    content = nickChange.content
    if len(content) >= 30:
        raise PerkError(msg='This nick is too long!')
    elif content.count('nigg') >= 1:
        await ctx.send('get banned nerd')
    else:
        try:
            await member.edit(nick=f'✰ {content}')
            await member.send(f'{ctx.author} changed your nick to {content} btw')
        except discord.Forbidden:
            raise PerkError(msg="I can't change an admin's nick!")
        #await ctx.send(f"{member.mention}'s nick has been changed to ✰ {content}")
