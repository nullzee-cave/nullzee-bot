from typing import Optional, Literal

import discord
from discord import Object, app_commands
from discord.app_commands import AppCommandError
from discord.ext import commands, tasks
from discord.ext.commands import Greedy

from helpers import constants
from helpers.colour import Colour
from datetime import datetime
import time
import math
from motor.motor_asyncio import AsyncIOMotorClient
from api_key import TOKEN, PREFIX, COGS, CONNECTION_STRING
from helpers.constants import Role, Channel, Misc
from perks.perk_system import PerkError
import traceback
from helpers.utils import get_user, staff_only, TimeConverter, ItemNotFound, HelpError, GiveawayError, staff_check

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

_global_cooldown = commands.CooldownMapping.from_cooldown(3, 1, commands.BucketType.member)


class DiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cluster = None
        self.db = None
        self.user_coll = None
        self.moderation_coll = None
        self.giveaway_coll = None

        self._global_cooldown = None

        self.initialisation_vars = {}

    async def setup_hook(self):
        self.cluster = AsyncIOMotorClient(CONNECTION_STRING)
        self.db = self.cluster["nullzee"]
        self.user_coll = self.db["users"]
        self.moderation_coll = self.db["moderation"]
        self.giveaway_coll = self.db["giveaways"]

        self._global_cooldown = _global_cooldown

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

        self.is_bot_initialised.start()

    @tasks.loop(seconds=3)
    async def is_bot_initialised(self):
        if "cogs.tickets" in COGS and \
           not ("ticket_inner_views" in self.initialisation_vars and self.initialisation_vars["ticket_inner_views"]):
            return False

        print(f"{green}Cogs loaded... Bot is now ready and waiting for prefix \"{PREFIX}\"{end_colour}")
        print(f"{green}\n√ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √  {end_colour}")

        self.is_bot_initialised.stop()


bot = DiscordBot(command_prefix=PREFIX, case_insensitive=True, intents=intents)
bot.remove_command("help")


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


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: AppCommandError):
    if isinstance(error, app_commands.errors.CheckFailure):
        return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

    # Ignore all other exception types, but print them to stderr
    print(f"EXCEPTION TRACE PRINT:\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}")


@bot.event
async def on_message(message):
    if not (message.author.bot or staff_check(message)):
        _cooldown = _global_cooldown.get_bucket(message)
        retry_after = _cooldown.update_rate_limit()
        if retry_after:
            # Spam detected
            return await message.delete()
        # No spam detected
    await bot.process_commands(message)


@bot.command(name="reload", aliases=["-r"], hidden=True)
@commands.guild_only()
@commands.has_guild_permissions(manage_roles=True)
async def reload_cogs(ctx):
    """ Reloads cogs while bot is still online """
    updated_cogs = ""
    length = len(COGS)
    print_progress_bar(0, length, bar_prefix="\nInitializing:", suffix="Complete", length=50)
    for i, cog in enumerate(COGS):
        time.sleep(0.3)
        print_progress_bar(i + 1, length, bar_prefix=f"Loading:{' ' * (20 - len(cog))} {cog}",
                           suffix="Complete", length=50)
        await bot.reload_extension(cog)
        updated_cogs += f"{cog}\n"
    print(f"\n{yellow}Initializing Bot, Please wait...{end_colour}\n")
    print(f"{green}Cogs loaded... Bot is now ready and waiting for prefix \"{PREFIX}\"{end_colour}")
    await ctx.send(f"`Cogs reloaded by:` <@{ctx.author.id}>")


@bot.command(name="cooldown")
@staff_only
async def channel_command_cooldown(ctx, channel: discord.TextChannel = None, _time: TimeConverter = 0):
    channel = channel if channel is not None else ctx.channel
    cooldowns[channel.id] = _time
    # TODO: make and use an inverse of string_to_seconds() here to make it look nicer
    await ctx.send(f"Set command cooldown for {channel.mention} to {_time:,} seconds")


@bot.command()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: Greedy[Object], spec: Optional[Literal["~", "*"]] = None) -> None:
    """
    I don't have a clue how this works
    Umbra's sync command, found with `?tag umbras sync command` in dpy discord

    Works like:
    -sync -> global sync
    -sync ~ -> sync current guild
    -sync * -> copies all global app commands to current guild and syncs
    -sync id_1 id_2 -> syncs guilds with id 1 and 2
    """
    if not guilds:
        if spec == "~":
            fmt = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            fmt = await ctx.bot.tree.sync(guild=ctx.guild)
        else:
            fmt = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(fmt)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    fmt = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            fmt += 1

    await ctx.send(f"Synced the tree to {fmt}/{len(guilds)} guilds.")


async def restrict_command_usage(ctx):
    if not ctx.guild or (hasattr(ctx, "is_help_command") and ctx.is_help_command is True):
        return True
    user = await get_user(ctx.bot, ctx.author)
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
    channel_allowed = ctx.channel.id in [Channel.BOT_COMMANDS, Channel.BOT_TEST_CHANNEL] or \
                      ctx.channel.category.id in [constants.Category.TICKETS]
    command_bypass = ctx.command.name in ["claimroles", "purchase", "report", "sbinfo"]
    cog_bypass = ctx.command.cog.qualified_name in ["Useless Commands"] if ctx.command.cog else False
    return staff_bypass or (not_blacklist and not_on_cooldown and (
           level_bypass or channel_allowed or command_bypass or role_bypass or cog_bypass))

bot.add_check(restrict_command_usage)

bot.run(TOKEN)
