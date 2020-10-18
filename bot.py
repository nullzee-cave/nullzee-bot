import discord
from discord.ext import commands
from helpers.colour import color
import sys
from datetime import datetime
import time
import asyncio
import random
import json
import math
from api_key import token, prefix


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


bot = commands.Bot(command_prefix=prefix, case_insensitive=True)
bot.remove_command('help')

cogs = ['cogs.level', 'cogs.util', 'cogs.moderation', 'cogs.giveaway','cogs.useless_commands']
# cogs = ['cogs.points']



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

    if isinstance(error, commands.DisabledCommand):
        await ctx.send('This command has been disabled.')
        return

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send("This command is on cooldown, please retry in {}s.".format(math.ceil(error.retry_after)))
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.")
        return

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
        await ctx.send("You do not have permission to use this command.")
        return


    #     # ignore all other exception types, but print them to stderr
    print('Ignoring exception in command {}: {}'.format(ctx.command, error), file=sys.stderr)


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
@commands.has_guild_permissions(administrator=True)
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


@bot.event
async def on_command(ctx):
    if ctx.channel.id == 667953033929293861 and 667953757954244628 not in [z.id for z in ctx.author.roles]:
        await ctx.send(f"{ctx.author.mention}, please do not use bot commands here")
        await asyncio.sleep(random.randint(1, 10))
        await ctx.message.delete()
    with open('UserCount.json') as f:
        users = json.load(f)
        if not str(ctx.author.id) in users["users"]:
            users["users"].append(str(ctx.author.id))
        with open('UserCount.json', 'w') as f:
            json.dump(users, f)


bot.run(token, bot=True, reconnect=True)
