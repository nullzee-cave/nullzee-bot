import discord
from discord.ext import commands

from helpers import constants
from helpers.colour import color
import sys
from datetime import datetime
import time
import asyncio
import random
import json
import math
from api_key import token, prefix, cogs
from perks.perkSystem import PerkError
import traceback
from helpers.utils import get_user, staff_only, TimeConverter, ItemNotFound

intents = discord.Intents.default()
intents.members = True


def fmtTime():
    _time = datetime.now()
    return _time.strftime("%b %d %Y %H:%M:%S")


# region colours
blue = color.BLUE
endc = color.END
bold = color.BOLD
purple = color.PURPLE
green = color.GREEN
red = color.RED
yellow = color.YELLOW


# endregion


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill="█", printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    if iteration == total:
        print(f'\r{purple}Loading Complete:             |{bar}| {percent}% {suffix}{endc}', end=printEnd)
    elif iteration in [0, 1]:
        print(f'\r{purple}{prefix} |{bar}| {percent}%   {suffix}{endc}', end=printEnd)
    else:
        print(f'\r{purple}{prefix} |{bar}| {percent}%  {suffix}{endc}', end=printEnd)


cooldown = {}
cooldowns = {}

bot = commands.Bot(command_prefix=prefix, case_insensitive=True, intents=intents)
bot.remove_command('help')



@bot.event
async def on_command_error(ctx, error):
    # if command has local error handler, return
    if hasattr(ctx.command, 'on_error'):
        return

        # get the original exception
    error = getattr(error, 'original', error)

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.BotMissingPermissions):
        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_perms]
        if len(missing) > 2:
            fmt = '{}, and {}'.format("**, **".join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        _message = 'I need the **{}** permission(s) to run this command.'.format(fmt)
        await ctx.send(_message)
        return
    if isinstance(error, commands.MissingRole) or isinstance(error, commands.MissingAnyRole):
        roles = error.missing_roles if isinstance(error, commands.MissingAnyRole) else [error.missing_role]
        return await ctx.send(embed=discord.Embed(title=":x: Error! You must have one of these roles: :x:",
                                                  description="\n".join(roles),
                                                  colour=0xff0000))

    if isinstance(error, commands.DisabledCommand):
        await ctx.send('This command has been disabled.')
        return

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send("This command is on cooldown, please retry in {}s.".format(math.ceil(error.retry_after)))
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.")
        return

    if isinstance(error, ItemNotFound):
        return await ctx.send(embed=error.embed())

    if isinstance(error, commands.UserInputError):
        # await ctx.send("Invalid input. Correct usage:")
        embed = discord.Embed(title=":x: Invalid Input!",
                              description=f"Correct usage: `-{ctx.command.qualified_name} {ctx.command.signature}`",
                              color=0xff0000)
        await ctx.send(embed=embed)
        # await ctx.send_help(ctx.command)
        return

    if isinstance(error, commands.NoPrivateMessage):
        try:
            await ctx.author.send('This command cannot be used in direct messages.')
        except discord.Forbidden:
            pass
        return

    if isinstance(error, commands.CheckFailure):
        # await ctx.send("You do not have permission to use this command.")
        return
    if isinstance(error, discord.Forbidden):
        return await ctx.send("I do not have permission to perform an action for that command")

    if isinstance(error, PerkError):
        return await error.send_error(ctx)
    #     # ignore all other exception types, but print them to stderr
    print("EXCEPTION TRACE PRINT:\n{}".format(
        "".join(traceback.format_exception(type(error), error, error.__traceback__))))


@bot.event
async def on_ready():
    print(f"{yellow}Loading the beast: {bot.user.name}!{endc}\n")
    time.sleep(1)
    l = len(cogs)
    printProgressBar(0, l, prefix=f'\nInitializing:                ', suffix='Complete', length=50)
    for i, cog in enumerate(cogs):
        time.sleep(0.3)
        printProgressBar(i + 1, l, prefix=f'Loading:{" " * (20 - len(cog))} {cog}', suffix='Complete', length=50)
        bot.load_extension(cog)
    print(f"{yellow}\nInitializing Bot, Please wait...{endc}\n")
    print(f'{green}Cogs loaded... Bot is now ready and waiting for prefix "."{endc}')

    print(f'{green}\n√ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √  {endc}')
    # status = (discord.Activity(type=discord.ActivityType.watching, name="nullzee"))
    # await bot.change_presence(activity=status)
    return


@bot.command(name='reload',
             description='Reloads bot',
             aliases=['-r'],
             hidden=True,
             case_insensitive=True)
@commands.guild_only()
@commands.has_guild_permissions(manage_roles=True)
async def reload(ctx):
    # await ctx.channel.purge(limit=int(1))
    """ Reloads cogs while bot is still online """
    user = ctx.author
    roles = ctx.message.author.roles
    server_id = ctx.guild.id
    updated_cogs = ''
    l = len(cogs)
    printProgressBar(0, l, prefix='\nInitializing:', suffix='Complete', length=50)
    for i, cog in enumerate(cogs):
        printProgressBar(i + 1, l, prefix='Progress:', suffix='Complete', length=50)
        bot.unload_extension(cog)
        print("Reloading", cog)
        bot.load_extension(cog)
        updated_cogs += f'{cog}\n'
    print(f"\n{purple}Initializing Bot, Please wait...{endc}\n")
    print(f'{green}Cogs loaded... Bot is now ready and waiting for prefix "."{endc}')
    await ctx.send(f"`Cogs reloaded by:` <@{user.id}>")


@bot.command()
@staff_only
async def command_cooldown(ctx, _time: TimeConverter):
    cooldowns[ctx.channel.id] = _time
    await ctx.send(f"Set command cooldown for {ctx.channel.mention} to {_time:,} seconds")


async def restrict_command_usage(ctx):
    if not ctx.guild:
        return True
    user = await get_user(ctx.author)
    not_blacklist = not ("command_blacklist" in user and ctx.command.name in user["command_blacklist"])
    staff_bypass = ctx.author.guild_permissions.manage_messages
    not_on_cooldown = True
    if ctx.channel.id in cooldowns and ctx.channel.id in cooldown:
        if ctx.command.name in cooldown[ctx.channel.id]:
            not_on_cooldown = cooldown[ctx.channel.id][ctx.command.name] + cooldowns[ctx.channel.id] < time.time()
            if not_on_cooldown:
                cooldown[ctx.channel.id][ctx.command.name] = time.time()
        else:
            cooldown[ctx.channel.id][ctx.command.name] = time.time()
    else:
        cooldown[ctx.channel.id] = {}
    level_bypass = user["level"] >= 50
    role_bypass = (roles := [z.id for z in
                             ctx.author.roles]) and 706285767898431500 in roles or 668724083718094869 in roles or 668736363297898506 in roles
    channel_allowed = ctx.channel.id in [668914397531602944] or ctx.channel.category.id in [constants.Channel.TICKETS]
    command_bypass = ctx.command.name in ["stab", "hug", "f", "claimroles", "purchase", "report", "sbinfo", "smh",
                                          "bonk"]
    cog_bypass = ctx.command.cog.qualified_name in ["Useless Commands"] if ctx.command.cog else False
    return staff_bypass or (not_blacklist and not_on_cooldown and (
                level_bypass or channel_allowed or command_bypass or role_bypass or cog_bypass))


bot.add_check(restrict_command_usage)

bot.run(token, bot=True, reconnect=True)
