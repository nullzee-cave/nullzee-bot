import asyncio
import datetime

import discord
from discord.ext import commands

import re

from helpers.constants import Channel, Role
from helpers.utils import staff_check, Embed, staff_only, getFileJson, saveFileJson, MessageOrReplyConverter

TICKET_TOPIC_REGEX = r"opened by (?P<user>.+#\d{4}) \((?P<user_id>\d+)\) at (?P<time>.+)"


def restrict_ticket_command_usage(ctx: commands.Context, raise_on_false=True):
    if ctx.channel.category.id != Channel.TICKETS:
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
    if str(ctx.author.id) == str(match.group('user_id')):
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
        result = re.sub(r"(?<!\\)`(.+)`", r'<code class="inline">\1</code>', result)
        result = re.sub(r"(?<!\\)~~(.+)~~", r"<s>\1</s>", result)
        result = re.sub(r"(?<!\\)\*\*(.+)\*\*", r"<b>\1</b>", result)
        result = re.sub(r"(?<!\\)\*(.+)\*", r"<i>\1</i>", result)
        result = re.sub(r"(?<!\\)__(.+)__", r"<u>\1</u>", result)
        result = re.sub(r"(?<!\\)\\n", '<br>', result)
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
    with open('assets/transcripts.css') as f:
        html += f.read()
    html += "</style>"
    html += '<div class="background theme-dark">'
    html += '<script>window.onload = () => window.scrollTo(0,document.body.scrollHeight);</script>'
    html += f'<h1>Start of transcript</h1><br>'
    cur_auth_id = 0

    for message in messages:
        message: discord.Message
        if message.author.id != cur_auth_id:
            html += '<div class="message-separator"></div>'
            html += '<div class="message">'
        else:
            html += '<div class="message-only">'
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
    html += '<h2>End of transcript</h2>'
    html += "</div>"
    return html


def generate_content(message):
    return f'<div class="message-content">{markdown(message.clean_content)}</div>'


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
        html += '<div class="embed-fields">'
        for field in embed.fields:
            html += f"""
                                            <div class="embed-field{' embed-field-inline' if field.inline else ''}">
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
    return ''.join([f'<img class="image-attachment" src={a.url}>' for a in attachments])


def next_author(author, timestamp):
    return f"""
        <img src="{author.avatar_url}"
            class="avatar">
        <div class="message-header">
            <span class="username"><b>{author}{'<span class="bot-tag">BOT</span>' if author.bot else ''}</b></span>
            <span class="timestamp">{timestamp.strftime('%d/%m/%y %H:%M')}</span>
        </div>

    """


ticket_types = {
    "💰": {
        "name": "giveaway donation",
        "questions": [
            "How long will the giveaway last?",
            "How many winners will there be?",
            "What requirements must users meet in order to be eligible to win?",
            "What is the prize?",
        ],
    },
    "🛄": {
        "name": "giveaway claim",
        "questions": [
            "What is the link to the giveaway that you won?",
            "What is the name of the account on which you wish to claim the giveaway?",
            "At what time (and timezone) do you want to collect the prize?",
        ],
    },
    "❓": {
        "name": "other",
        "questions": [
            "Why have you opened this ticket?",
        ],
    },
}


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.hidden = False
        self.bot = bot
        self.message_ids = []
        self.load_message_ids()

    def load_message_ids(self):
        self.message_ids = getFileJson("config")["ticket_messages"]

    @commands.command()
    @staff_only
    async def addTicketMessage(self, ctx, message: discord.Message):
        config = getFileJson("config")
        config["ticket_messages"].append(message.id)
        saveFileJson(config, "config")
        self.load_message_ids()
        await ctx.send("Successfully added message")

    @commands.command()
    @staff_only
    async def removeTicketMessage(self, ctx, message: discord.Message):
        config = getFileJson("config")
        config["ticket_messages"].remove(message.id)
        saveFileJson(config, "config")
        self.load_message_ids()
        await ctx.send("Successfully removed message")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.message_id not in self.message_ids:
            return
        if str(payload.emoji) in ticket_types:
            guild: discord.Guild = self.bot.get_guild(payload.guild_id)
            msg: discord.Message = await guild.get_channel(payload.channel_id).fetch_message(payload.message_id)
            await msg.remove_reaction(payload.emoji, payload.member)
            embed = discord.Embed(title=ticket_types[str(payload.emoji)]["name"], colour=discord.Colour.green(),
                                  description="**Commands:**\n"
                                              "`-close [reason]` : close the ticket\n"
                                              "`-adduser [user]` : add someone else to the ticket\n"
                                              "`-removeuser [user]` : remove someone else from the ticket")
            embed.set_author(name=payload.member, icon_url=payload.member.avatar_url)
            for question in ticket_types[str(payload.emoji)]["questions"]:
                msg = await payload.member.send(question)
                try:
                    embed.add_field(name=question,
                                    value=(await self.bot.wait_for('message',
                                                                   check=lambda m: m.channel.id == msg.channel.id
                                                                                   and m.author.id == payload.member.id,
                                                                   timeout=300.0)).content,
                                    inline=False)
                except asyncio.TimeoutError:
                    return await payload.member.send("Ticket creation timed out")
            channel: discord.TextChannel = await guild.create_text_channel(
                f"{payload.member.name}-{payload.member.discriminator}",
                category=guild.get_channel(Channel.TICKETS),
                topic=f"opened by {payload.member} ({payload.member.id}) at {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}",
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        read_messages=False),
                    guild.get_role(
                        Role.STAFF): discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True),
                    payload.member: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True)
                })
            start = await channel.send(f"<@&{Role.TICKET_PING}>", embed=embed)
            await start.pin()
            await payload.member.send(f"Ticket created! {start.jump_url}")
            await guild.get_channel(Channel.MOD_LOGS).send(
                embed=Embed(
                    payload.member,
                    colour=0x00ff00,
                    title="Ticket opened",
                    description=f"{channel.name}\nReason: {ticket_types[str(payload.emoji)]['name']}"
                ).auto_author()
            )

    @commands.command()
    async def adduser(self, ctx: commands.Context, *, member: discord.Member):
        restrict_ticket_command_usage(ctx)
        await ctx.channel.set_permissions(member, read_messages=True)
        await ctx.send(f"{ctx.author.mention} added {member.mention} to this ticket")

    @commands.command()
    async def pin(self, ctx: commands.Context, message: str = "none"):
        restrict_ticket_command_usage(ctx)
        message: discord.Message = await MessageOrReplyConverter().convert(ctx, message)
        await message.pin(reason=f"pinned by {ctx.author}")

    @commands.command()
    async def unpin(self, ctx: commands.Context, message: str = "none"):
        restrict_ticket_command_usage(ctx)
        message: discord.Message = await MessageOrReplyConverter().convert(ctx, message)
        await message.unpin(reason=f"unpinned by {ctx.author}")
        await ctx.send("Unpinned!")

    @commands.command()
    async def removeuser(self, ctx: commands.Context, *, member: discord.Member):
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
    async def close(self, ctx, *, reason: str = None):
        restrict_ticket_command_usage(ctx)
        with open(f"transcripts/{ctx.channel.name}.html", 'w', encoding="utf-8") as f:
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
        await ctx.guild.get_channel(Channel.MOD_LOGS).send(
            embed=Embed(
                ctx.author,
                colour=0xff0000,
                title="Ticket closed",
                description=f"{ctx.channel.name}\nReason: {reason}"
            ).auto_author(),
            file=discord.File(f"transcripts/{ctx.channel.name}.html", "transcript.html")
        )
        # await mod_logs.send(file=discord.File(f"transcripts/{ctx.author}.html", "transcript.html"))


def setup(bot):
    bot.add_cog(Tickets(bot))
