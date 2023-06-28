import chat_exporter
import discord
from discord import app_commands
from discord.ext import commands, tasks

import re

from helpers.constants import Channel, Role, Category, Misc
from helpers.ticket_utils import TICKET_TOPIC_REGEX, ALTERNATE_TICKET_TOPIC_REGEX
from helpers.utils import staff_check, Embed, MessageOrReplyConverter, role_ids, list_one
from helpers.views import PersistentTicketView, PersistentInnerTicketView


def restrict_ticket_command_usage(ctx: commands.Context, raise_on_false=True):
    if ctx.channel.category.id != Category.TICKETS:
        if raise_on_false:
            raise commands.MissingPermissions(["manage_ticket"])
        else:
            return False
    if staff_check(ctx):
        return True
    match = re.search(TICKET_TOPIC_REGEX, ctx.channel.topic)
    if not match:
        if raise_on_false:
            raise commands.MissingPermissions(["manage_ticket"])
        else:
            return False
    if str(ctx.author.id) == str(match.group("user_id")):
        return True
    if raise_on_false:
        raise commands.MissingPermissions(["manage_ticket"])
    else:
        return False


def ticket_restriction_for_app_commands(interaction: discord.Interaction, raise_on_false=False):
    if interaction.channel.category.id != Category.TICKETS:
        if raise_on_false:
            raise commands.MissingPermissions(["manage_ticket"])
        else:
            return False
    roles = role_ids(interaction.user.roles)
    if list_one(roles, Role.STAFF, Role.ADMIN):
        return True
    match = re.search(TICKET_TOPIC_REGEX, interaction.channel.topic)
    if not match:
        if raise_on_false:
            raise commands.MissingPermissions(["manage_ticket"])
        else:
            return False
    if str(interaction.user.id) == str(match.group("user_id")):
        return True
    if raise_on_false:
        raise commands.MissingPermissions(["manage_ticket"])
    else:
        return False


ticket_restriction_check = app_commands.check(ticket_restriction_for_app_commands)


class TicketError(Exception):
    def __init__(self, msg=None):
        self.message = msg


class Tickets(commands.Cog, name="Tickets"):
    """The ticket system, and all related commands"""

    def __init__(self, bot):
        self.hidden = False
        self.bot = bot
        self.bot.add_view(PersistentTicketView())
        self.add_inner_ticket_views.start()

        self.remove_user_context_menu = discord.app_commands.ContextMenu(
            name="Remove User",
            callback=self.remove_user_context_menu_callback,
        )
        self.bot.tree.add_command(self.remove_user_context_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.remove_user_context_menu.name, type=self.remove_user_context_menu.type)

    @tasks.loop(seconds=1)
    async def add_inner_ticket_views(self):
        await self.bot.wait_until_ready()
        for channel in self.bot.get_guild(Misc.GUILD).get_channel(Category.TICKETS).channels:
            if isinstance(channel, discord.TextChannel) and channel.id != Channel.OPEN_TICKET:
                view_message = (await channel.pins())[-1]
                if view_message.components:
                    self.bot.add_view(PersistentInnerTicketView(channel.id))
        self.bot.initialisation_vars["ticket_inner_views"] = True
        self.add_inner_ticket_views.stop()

    @commands.command(name="createticketview", hidden=True)
    @commands.has_role(Role.ADMIN)
    async def create_ticket_view(self, ctx, channel: discord.TextChannel = None):
        embed = discord.Embed(
            title="Open a Ticket",
            description="The bot will DM you some questions for you to answer before creating the ticket. "
                        "If you wish to cancel ticket creation, simply ignore the messages and it will time out. "
                        "Please answer all DM questions as fully as possible. If donating for a giveaway, "
                        f"please check <#{Channel.GIVEAWAY_INFO}> to make sure it is allowed.",
            colour=discord.Colour.blurple()
        )
        embed.add_field(name="Ticket Types", value="💰 - Donate for a giveaway\n"
                                                   "🛄 - Claim a giveaway prize\n"
                                                   "❓ - Anything else")
        channel = ctx.channel if channel is None else channel
        await channel.send(embed=embed, view=PersistentTicketView())

    @commands.command(name="adduser")
    async def add_user(self, ctx: commands.Context, *, member: discord.Member):
        """Add a user to a ticket"""
        restrict_ticket_command_usage(ctx)
        await ctx.channel.set_permissions(member, read_messages=True)
        await ctx.send(f"{ctx.author.mention} added {member.mention} to this ticket")

    @commands.command(name="removeuser")
    async def remove_user(self, ctx: commands.Context, *, member: discord.Member):
        """Remove a user from a ticket"""
        restrict_ticket_command_usage(ctx)
        string = f"{ctx.author.mention} removed {member.mention} from this ticket"
        member_ctx = ctx
        # noinspection PyPropertyAccess
        member_ctx.author = member
        if restrict_ticket_command_usage(member_ctx, raise_on_false=False):
            raise commands.MissingPermissions(["manage_tickets"])
        await ctx.channel.set_permissions(member, read_messages=False)
        await ctx.send(string)

    @app_commands.guild_only
    @app_commands.default_permissions(manage_messages=True)
    @ticket_restriction_check
    async def remove_user_context_menu_callback(self, interaction: discord.Interaction, member: discord.Member):
        """Remove a user from a ticket via a context menu"""
        if list_one(role_ids(member.roles), Role.STAFF, Role.ADMIN):
            raise app_commands.errors.MissingPermissions(["manage_tickets"])
        match = re.search(TICKET_TOPIC_REGEX, interaction.channel.topic)
        if str(member.id) == str(match.group("user_id")):
            raise app_commands.errors.MissingPermissions(["manage_tickets"])
        await interaction.channel.set_permissions(member, read_messages=False)
        await interaction.response.send_message(f"{interaction.user.mention} removed {member.mention} from this ticket")

    @commands.command()
    async def pin(self, ctx: commands.Context, message: str = "none"):
        """Pin a message in a ticket"""
        restrict_ticket_command_usage(ctx)
        message: discord.Message = await MessageOrReplyConverter().convert(ctx, message)
        await message.pin(reason=f"pinned by {ctx.author}")

    @commands.command()
    async def unpin(self, ctx: commands.Context, message: str = "none"):
        """Unpin a message in a ticket"""
        restrict_ticket_command_usage(ctx)
        message: discord.Message = await MessageOrReplyConverter().convert(ctx, message)
        if message.id == (await ctx.pins())[-1].id:
            return await ctx.send("You cannot unpin that message")
        await message.unpin(reason=f"unpinned by {ctx.author}")
        await ctx.send("Unpinned!")

    @commands.command()
    async def close(self, ctx, *, reason: str = None):
        """Close a ticket"""
        restrict_ticket_command_usage(ctx)
        messages = [*reversed([z async for z in ctx.channel.history()])]
        html = "<!--\n"
        for message in messages:
            html += f"{message.author} | {message.created_at.strftime('%d/%m/%y %H:%M')}: {message.content}\n"
        html += "\n-->\n\n"
        transcript = await chat_exporter.export(ctx.channel, military_time=True, bot=ctx.bot)
        html += transcript
        with open(f"transcripts/{ctx.channel.name}.html",
                  "w", encoding="utf-8") as f:
            f.write(html)
        user = re.search(TICKET_TOPIC_REGEX, ctx.channel.topic)
        if user is None:
            user = re.search(ALTERNATE_TICKET_TOPIC_REGEX, ctx.channel.topic)
        user = int(user.group("user_id"))
        try:
            user = self.bot.get_user(user)
            if user.id != ctx.author.id:
                await user.send(f"Your ticket has been closed\nReason: `{reason}`")
        except (discord.Forbidden, discord.NotFound, AttributeError):
            pass
        await ctx.channel.delete()
        embed = Embed(ctx.author, colour=0xff0000, title="Ticket closed",
                      description=f"{ctx.channel.name}\nReason: {reason}")
        embed.auto_author()
        log_channel = ctx.guild.get_channel(Channel.MOD_LOGS)
        await log_channel.send(embed=embed,
                               file=discord.File(f"transcripts/{ctx.channel.name}.html", "transcript.html"))


async def setup(bot):
    await bot.add_cog(Tickets(bot))
