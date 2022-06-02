import discord
from discord.ext import commands

from helpers import constants
from helpers.colour import Colour
from datetime import datetime
import time
import math
from api_key import TOKEN, PREFIX, COGS
from helpers.constants import Role, Channel, Misc
from perks.perk_system import PerkError
import traceback
from helpers.utils import get_user, staff_only, TimeConverter, ItemNotFound, HelpError, GiveawayError

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


def fmt_time():
    _time = datetime.now()
    return _time.strftime("%b %d %Y %H:%M:%S")


# region colours

blue = Colour.BLUE
end_colour = Colour.END
bold = Colour.BOLD
purple = Colour.PURPLE
green = Colour.GREEN
red = Colour.RED
yellow = Colour.YELLOW

# endregion


def print_progress_bar(iteration, total, bar_prefix="", suffix="", decimals=1, length=100, fill="█", print_end="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + "-" * (length - filled_length)
    if iteration == total:
        print(f"\r{purple}Loading Complete:             |{bar}| {percent}% {suffix}{end_colour}", end="\n")
    elif iteration in [0, 1]:
        print(f"\r{purple}{bar_prefix} |{bar}| {percent}%   {suffix}{end_colour}", end=print_end)
    else:
        print(f"\r{purple}{bar_prefix} |{bar}| {percent}%  {suffix}{end_colour}", end=print_end)


cooldown = {}
cooldowns = {}


class DiscordBot(commands.Bot):
    async def setup_hook(self):
        for current_cog in self.extensions.copy():
            await self.unload_extension(current_cog)

        print(f"{yellow}Loading the beast: {self.user.name}!{end_colour}\n")
        time.sleep(1)
        length = len(COGS)
        print_progress_bar(0, length, bar_prefix=f"\nInitializing:                ", suffix="Complete", length=50)
        for i, cog in enumerate(COGS):
            time.sleep(0.3)
            print_progress_bar(i + 1, length, bar_prefix=f"Loading:{' ' * (20 - len(cog))} {cog}",
                               suffix="Complete", length=50)
            await self.load_extension(cog)
        print(f"{yellow}\n\nInitializing Bot, Please wait...{end_colour}\n")
        print(f"{green}Cogs loaded... Bot is now ready and waiting for prefix \"{PREFIX}\"{end_colour}")
        print(f"{green}\n√ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √  {end_colour}")


bot = DiscordBot(command_prefix=PREFIX, case_insensitive=True, intents=intents)
bot.remove_command("help")


@bot.event
async def on_thread_create(thread):
    await thread.join()


@bot.event
async def on_command_error(ctx, error):
    # if command has local error handler, return
    if hasattr(ctx.command, "on_error"):
        return

        # get the original exception
    error = getattr(error, "original", error)

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.BotMissingPermissions):
        missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]
        if len(missing) > 2:
            fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
        else:
            fmt = " and ".join(missing)
        _message = "I need the **{}** permission(s) to run this command.".format(fmt)
        return await ctx.send(_message)
    if isinstance(error, commands.MissingRole) or isinstance(error, commands.MissingAnyRole):
        if isinstance(error, commands.MissingAnyRole):
            roles = error.missing_roles
        else:
            roles = [error.missing_role]
        roles = [bot.get_guild(Misc.GUILD).get_role(z).mention for z in roles]
        embed = discord.Embed(title=":x: Error! You must have one of these roles: :x:",
                              description="\n".join(roles), colour=0xff0000)
        return await ctx.send(embed=embed)

    if isinstance(error, commands.DisabledCommand):
        return await ctx.send("This command has been disabled.")

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send("This command is on cooldown, please retry in {}s.".format(math.ceil(error.retry_after)))
        return

    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("You do not have permission to use this command.")

    if isinstance(error, ItemNotFound):
        return await ctx.send(embed=error.embed())

    if isinstance(error, commands.UserInputError):
        # await ctx.send_help(ctx.command)
        embed = discord.Embed(title=":x: Invalid Input!",
                              description=f"Correct usage: `{PREFIX}{ctx.command.qualified_name} {ctx.command.signature}`",
                              color=0xff0000)
        return await ctx.send(embed=embed)

    if isinstance(error, commands.NoPrivateMessage):
        try:
            await ctx.author.send("This command cannot be used in direct messages.")
        except discord.Forbidden:
            pass
        return

    if isinstance(error, commands.CheckFailure):
        # await ctx.send("You do not have permission to use this command.")
        return

    if isinstance(error, discord.Forbidden):
        return await ctx.send("I do not have permission to perform an action for that command")

    if isinstance(error, (PerkError, HelpError, GiveawayError)):
        return await error.send_error(ctx)

    # Ignore all other exception types, but print them to stderr
    print(f"EXCEPTION TRACE PRINT:\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}")


@bot.command(name="reload", aliases=["-r"], hidden=True)
@commands.guild_only()
@commands.has_guild_permissions(manage_roles=True)
async def reload_cogs(ctx):
    """ Reloads cogs while bot is still online """
    updated_cogs = ""
    length = len(COGS)
    print_progress_bar(0, length, bar_prefix="\nInitializing:", suffix="Complete", length=50)
    for i, cog in enumerate(COGS):
        print_progress_bar(i + 1, length, bar_prefix="Progress:", suffix="Complete", length=50)
        print("Reloading", cog)
        await bot.reload_extension(cog)
        updated_cogs += f"{cog}\n"
    print(f"\n{purple}Initializing Bot, Please wait...{end_colour}\n")
    print(f"{green}Cogs loaded... Bot is now ready and waiting for prefix \"{PREFIX}\"{end_colour}")
    await ctx.send(f"`Cogs reloaded by:` <@{ctx.author.id}>")


@bot.command(name="cooldown")
@staff_only
async def channel_command_cooldown(ctx, channel: discord.TextChannel = None, _time: TimeConverter = 0):
    channel = channel if channel is not None else ctx.channel
    cooldowns[channel.id] = _time
    # TODO: make and use an inverse of string_to_seconds() here to make it look nicer
    await ctx.send(f"Set command cooldown for {channel.mention} to {_time:,} seconds")


async def restrict_command_usage(ctx):
    if not ctx.guild or (hasattr(ctx, "is_help_command") and ctx.is_help_command is True):
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
                             ctx.author.roles]) and Role.RETIRED_SUPPORTER in roles or \
                                                    Role.BOOSTER in roles or Role.TWITCH_SUB in roles
    channel_allowed = ctx.channel.id in [Channel.BOT_COMMANDS, 981960190335258654] or \
                      ctx.channel.category.id in [constants.Channel.OPEN_TICKET]
    command_bypass = ctx.command.name in ["claimroles", "purchase", "report", "sbinfo"]
    cog_bypass = ctx.command.cog.qualified_name in ["Useless Commands"] if ctx.command.cog else False
    return staff_bypass or (not_blacklist and not_on_cooldown and (
           level_bypass or channel_allowed or command_bypass or role_bypass or cog_bypass))

bot.add_check(restrict_command_usage)

bot.run(TOKEN)
