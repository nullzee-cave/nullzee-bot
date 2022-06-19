import asyncio
import datetime
from functools import wraps

import discord
from discord.ext import commands, tasks

import re

from helpers.constants import Channel, Role, Category, Misc
from helpers.utils import staff_check, Embed, staff_only, get_file_json, save_file_json, MessageOrReplyConverter

TICKET_TOPIC_REGEX = r"opened by (?P<user>.+#\d{4}) \((?P<user_id>\d+)\) at (?P<time>.+)"

# TODO: make use of a library to create transcripts
# Potentially https://github.com/mahtoid/DiscordChatExporterPy


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


def markdown(string):
    result = string
    changed = True
    this_result = string
    while changed:
        result = re.sub(r"(?<!\\)`(.+)`", r"code class=\"inline\">\1</code>", result)
        result = re.sub(r"(?<!\\)~~(.+)~~", r"<s>\1</s>", result)
        result = re.sub(r"(?<!\\)\*\*(.+)\*\*", r"<b>\1</b>", result)
        result = re.sub(r"(?<!\\)\*(.+)\*", r"<i>\1</i>", result)
        result = re.sub(r"(?<!\\)__(.+)__", r"<u>\1</u>", result)
        result = re.sub(r"(?<!\\)\\n", "<br>", result)
        changed = result != this_result
        this_result = result
    return result


def transcribe(messages):
    messages = [*messages]
    html = "<p>"
    for message in messages:
        html += f"{message.author} | {message.created_at.strftime('%d/%m/%y %H:%M')}: {message.content}\n"
    html += "</p>"
    html += "<style>"
    with open("assets/transcripts.css") as f:
        html += f.read()
    html += "</style>"
    html += "<div class=\"background theme-dark\">"
    html += "<script>window.onload = () => window.scrollTo(0,document.body.scrollHeight);</script>"
    html += f"<h1>Start of transcript</h1><br>"
    cur_auth_id = 0

    for message in messages:
        message: discord.Message
        if message.author.id != cur_auth_id:
            html += "<div class=\"message-separator\"></div>"
            html += "<div class=\"message\">"
        else:
            html += "<div class=\"message-only\">"
        if message.author.id != cur_auth_id:
            html += next_author(message.author, message.created_at)
        if message.content:
            html += generate_content(message)
        if message.embeds:
            html += generate_embed(message.embeds[0])
        if message.attachments:
            html += generate_attachments(message.attachments)
        html += "</div>"
        cur_auth_id = message.author.id
    html += "<h2>End of transcript</h2>"
    html += "</div>"
    return html


def generate_content(message):
    return f"<div class=\"message-content\">{markdown(message.clean_content)}</div>"


def generate_embed(embed: discord.Embed):
    html = f"""
        <link rel="stylesheet" href="styles.css">
        <link rel="stylesheet" href="example.css">
        <div class="message-embed">
                <div class="comment">
                    <div class="accessory">
                        <div class="embed-wrapper">
                            <div class="embed-color-pill"
                                style="background-color: {embed.colour}; --darkreader-inline-bgcolor:#215132;"
                                data-darkreader-inline-bgcolor=""></div>
    """
    if embed.author:        html += f"""
                            <div class="embed embed-rich">
                                <div class="embed-content">
                                    <div class="embed-content-inner">
                                        <div class="embed-author"><img
                                                src="{embed.author.icon_url}" role="presentation"
                                                class="embed-author-icon"><a target="_blank" rel="noreferrer"
                                                href="{embed.author.icon_url}" class="embed-author-name">{embed.author.name}</a></div>
    """
    if embed.title:
        html += f"""
                                            <a target="_blank" rel="noreferrer" href="{embed.url}" class="embed-title">
                                            {markdown(embed.title)}
                                        </a>
    """
    if embed.description:
        html += f"""
                                        <div class="embed-description markup">
                                            {markdown(embed.description)}
                                        </div>
    """
    if embed.fields:
        html += "<div class=\"embed-fields\">"
        for field in embed.fields:
            html += f"""
                                            <div class=\"embed-field{" embed-field-inline" if field.inline else ""}\">
                                                <div class="embed-field-name">
                                                    {field.name}
                                                </div>
                                                <div class="embed-field-value markup">
                                                    {markdown(field.value)}
                                                </div>
                                            </div>
    """
        html += "</div>"

    if embed.thumbnail:
        html += f"""
                                    </div><img src="{embed.thumbnail.url}" role="presentation"
                                        class="embed-rich-thumb" style="max-width: 80px; max-height: 80px;">
                                </div>
        """
    if embed.image:
        html += f"""

                                <a class="embed-thumbnail embed-thumbnail-rich"><img class="image"
                                        role="presentation" src="{embed.image.url}"></a>

        """
    if embed.footer:
        html += "<div>"
        if embed.footer.icon_url:
            html += f"""
                                <img src="{embed.footer.icon_url}" class="embed-footer-icon"
                                        role="presentation" width="20" height="20">
                    """
        if embed.footer.text:
            html += f"""
                                        <span class="embed-footer">{embed.footer.text}</span>
                    """
    html += """
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        </div>
    """
    return html


def generate_attachments(attachments):
    return "".join([f"<img class=\"image-attachment\" src={a.url}>" for a in attachments])


def next_author(author, timestamp):
    return f"""
        <img src="{author.avatar}"
            class="avatar">
        <div class="message-header">
            <span class="username"><b>{author}{'<span class="bot-tag">BOT</span>' if author.bot else ""}</b></span>
            <span class="timestamp">{timestamp.strftime("%d/%m/%y %H:%M")}</span>
        </div>

    """


ticket_types = {
    "💰": {
        "name": "Giveaway Donation",
        "questions": [
            "How long will the giveaway last?",
            "How many winners will there be?",
            "What requirements must users meet in order to be eligible to win?",
            "What is the prize?",
        ],
    },
    "🛄": {
        "name": "Giveaway Claim",
        "questions": [
            "What is the link to the giveaway that you won?",
            "What is the name of the account on which you wish to claim the giveaway?",
            "At what time (and timezone) do you want to collect the prize?",
        ],
    },
    "❓": {
        "name": "Other",
        "questions": [
            "Why have you opened this ticket?",
        ],
    },
}


class TicketError(Exception):
    def __init__(self, msg=None):
        self.message = msg


def can_open_ticket(func):

    @wraps(func)
    async def wrapper(*args, **kwargs):
        interaction = args[1]

        if get_file_json("config")["lockdown"]:
            return await interaction.response.send_message("Unable to create ticket: **Server in lockdown!**",
                                                           ephemeral=True)

        owned_ticket_count = 0
        for c in interaction.guild.get_channel(Category.TICKETS).channels:
            if isinstance(c, discord.TextChannel):
                if c.topic is not None:
                    if str(interaction.user.id) in c.topic:
                        owned_ticket_count += 1
                        if owned_ticket_count >= 3:
                            return await interaction.response.send_message(
                                "Unable to create ticket: **Too many tickets!**", ephemeral=True)

        await func(*args, **kwargs)

    return wrapper


class PersistentTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @can_open_ticket
    @discord.ui.button(label="Donate", emoji="💰", style=discord.ButtonStyle.green, custom_id="ticket_view:donate")
    async def ticket_donate(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.user.send("Ticket Creation - `Giveaway Donation`")
            await interaction.response.defer()
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't DM you! Check you have DMs from this server enabled and try again.",
                ephemeral=True
            )
        await ask_ticket_questions(interaction, button)

    @can_open_ticket
    @discord.ui.button(label="Claim", emoji="🛄", style=discord.ButtonStyle.blurple, custom_id="ticket_view:claim")
    async def ticket_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.user.send("Ticket Creation - `Giveaway Claim`")
            await interaction.response.defer()
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't DM you! Check you have DMs from this server enabled and try again",
                ephemeral=True
            )
        await ask_ticket_questions(interaction, button)

    @can_open_ticket
    @discord.ui.button(label="Other", emoji="❓", style=discord.ButtonStyle.grey, custom_id="ticket_view:other")
    async def ticket_other(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.user.send("Ticket Creation - `Other`")
            await interaction.response.defer()
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't DM you! Ensure you have DMs from this server enabled and try again",
                ephemeral=True
            )
        await ask_ticket_questions(interaction, button)


class PersistentInnerTicketView(discord.ui.View):
    def __init__(self, channel_id: int):
        self.channel_id = channel_id

        self.close_button = discord.ui.button(
            label="Close",
            style=discord.ButtonStyle.red,
            custom_id=f"inner_ticket_view:{channel_id}:close"
        )(PersistentInnerTicketView.ticket_close)

        super().__init_subclass__()
        super().__init__(timeout=None)

    async def ticket_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        with open(f"transcripts/{interaction.channel.name}.html", "w", encoding="utf-8") as f:
            f.write(transcribe(reversed([z async for z in interaction.channel.history(limit=500)])))
        user = re.search(TICKET_TOPIC_REGEX, interaction.channel.topic)
        user = int(user.group("user_id"))
        try:
            user = self.bot.get_user(user)
            if user.id != interaction.user.id:
                await user.send(f"Your ticket has been closed\nReason: `None`")
        except (discord.Forbidden, discord.NotFound, AttributeError):
            pass
        await interaction.channel.delete()
        embed = Embed(interaction.user, colour=0xff0000, title="Ticket closed",
                      description=f"{interaction.channel.name}\nReason: None")
        embed.auto_author()
        log_channel = interaction.guild.get_channel(Channel.MOD_LOGS)
        await log_channel.send(embed=embed,
                               file=discord.File(f"transcripts/{interaction.channel.name}.html", "transcript.html"))


async def ask_ticket_questions(interaction: discord.Interaction, button: discord.ui.Button):
    embed = discord.Embed(title=ticket_types[str(button.emoji)]["name"], colour=discord.Colour.green(),
                          description="**Commands:**\n"
                                      "`-close [reason]` : close the ticket\n"
                                      "`-adduser [user]` : add someone else to the ticket\n"
                                      "`-removeuser [user]` : remove someone else from the ticket")
    embed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
    images = []
    for question in ticket_types[str(button.emoji)]["questions"]:
        try:
            msg = await interaction.user.send(question)
        except discord.Forbidden:
            return
        try:
            message = await interaction.client.wait_for(
                "message",
                check=lambda m: m.channel.id == msg.channel.id and m.author.id == interaction.user.id,
                timeout=300.0)
            if message.attachments is not None:
                for attachment in message.attachments:
                    images.append(attachment.url)
            embed.add_field(name=question,
                            value=message.content if message.content else "`None`",
                            inline=False)
        except asyncio.TimeoutError:
            try:
                return await interaction.user.send("Ticket creation timed out")
            except discord.Forbidden:
                return
    if images:
        embed.set_image(url=images[0])
    channel: discord.TextChannel = await interaction.guild.create_text_channel(
        f"{interaction.user.name}-{interaction.user.discriminator}",
        category=interaction.guild.get_channel(Category.TICKETS),
        topic=f"opened by {interaction.user} ({interaction.user.id}) at "
              f"{datetime.datetime.now().strftime('%d/%m/%y %H:%M')}",
        overwrites={
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
            interaction.guild.get_role(
                Role.STAFF): discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.get_role(
                Role.TRAINEE): discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True)
        })
    start = await channel.send(f"<@&{Role.TICKET_PING}> {interaction.user.mention}",
                               embed=embed, view=PersistentInnerTicketView(channel.id))
    await start.pin()
    await interaction.user.send(f"Ticket created! {start.jump_url}")
    embed = Embed(interaction.user, colour=0x00ff00, title="Ticket opened",
                  description=f"{channel.name}\nReason: {ticket_types[str(button.emoji)]['name']}")
    embed.auto_author()
    log_channel = interaction.guild.get_channel(Channel.MOD_LOGS)
    await log_channel.send(embed=embed)


class Tickets(commands.Cog, name="Tickets"):
    """The ticket system, and all related commands"""

    def __init__(self, bot):
        self.hidden = False
        self.bot = bot
        self.bot.add_view(PersistentTicketView())
        self.add_inner_ticket_views.start()

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
        with open(f"transcripts/{ctx.channel.name}.html", "w", encoding="utf-8") as f:
            f.write(transcribe(reversed([z async for z in ctx.channel.history(limit=500)])))
        user = re.search(TICKET_TOPIC_REGEX, ctx.channel.topic)
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
