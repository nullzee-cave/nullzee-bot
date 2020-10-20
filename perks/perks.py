from perks.perkSystem import perk, PerkError
from discord.ext import commands
import discord
from api_key import userColl
from helpers.utils import get_user, Embed, getFileJson, saveFileJson
import datetime

@perk(name="AskNullzee", description="Ask Nullzee a question!", cost=5, aliases=["NullzeeQuestion", "askNull"],
      require_arg=True)
async def askNullzee(ctx, arg):
    msg = await ctx.guild.get_channel(738350726417219645).send(
        embed=discord.Embed(description=arg, color=0x00FF00)
            .set_author(name=ctx.author, icon_url=ctx.author.avatar_url))
    await ctx.send(embed=discord.Embed(title="Bought!", url=msg.jump_url, color=0x00FF00))


@perk(name="embedColour", description="Change the colour of your embeds!", cost=10,
      aliases=["embedColor", "commandColour"])
async def embedColour(ctx, arg):
    if not (len(arg.replace('#', '')) == 6):
        raise PerkError(embed=discord.Embed(title="Error!", description="please specify a valid hex code",
                                            color=discord.Color.red()))
    await get_user(ctx.author)
    await userColl.update_one({"_id": str(ctx.author.id)}, {"$set": {"embed_colour": arg.replace('#', '')}})


@perk(name="deadChatPing", description="Ping <@&749178299518943343> with a topic of your choice!", cost=15,
      aliases=["deadchat", "ping"], require_arg=True)
async def deadChat(ctx, arg):
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

@perk(name="staffNickChange", description = "Change a Staff's nick!", cost= 10, require_arg = True)
async def staffNickChange(ctx,arg):
    member = await commmands.MemberConverter.convert(arg)
    await ctx.send("What do you want to change their nick to?")
    try:
        nickChange = await self.bot.wait_for('message', check=check)
    content = nickChange.content
    if len(content) >= 32:
        await ctx.send('This nick is too long!')
    elif content.count('nigg') >= 1:
        await ctx.send('get banned nerd')
    else:
        await member.edit(nick=f'✰ {content}')
        await ctx.send(f"{member.mention}'s nick has been changed to ✰ {content}")
