import discord
from discord.ext import commands
import difflib

from helpers.constants import Channel
from helpers.utils import Embed


class Logging(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.hidden: bool = True
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        content = message.content if message.content else ""
        truncated_content = content[:1960]
        files = []
        embed = Embed(message.author, colour=discord.Colour.dark_orange(),
                      ).auto_author().set_footer(
            text=f"Message ID: {message.id}, Channel ID: {message.channel.id}, Author ID: {message.author.id}")
        embed.description = f"**Message deleted in {message.channel.mention} by {message.author.mention}:**\n" \
                            f"{content}{'...' if truncated_content != content else ''}"
        if message.attachments:
            for attachment in message.attachments:
                if attachment.width is not None:
                    embed.set_image(url=message.attachments[0].url)
                else:
                    files.append(await attachment.to_file())

        kwargs = {"embed": embed}
        if len(files) != 0:
            kwargs["files"] = files

        channel: discord.TextChannel = message.guild.get_channel(Channel.MESSAGE_LOGS)
        await channel.send(**kwargs)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content == after.content or not after.guild or after.author.bot:
            return

        if len(before.content) + len(after.content) > 1500:
            diff = [*difflib.ndiff(before.content, after.content)]
            output = "**Changes:**\n"
            last_change = ""
            for char in diff:
                char: str
                change = char[0]
                if change in ("+", "-"):
                    if change != last_change:
                        output += '`'
                        output += char[::2]
                        last_change = change
                    else:
                        output += char[-1]
                else:
                    if last_change:
                        last_change = ""
                        output += '`'
                    output += char[-1]
        else:
            output = f"**Before:**\n{before.content}\n**After:**\n{after.content}"

        embed = Embed(after.author, colour=discord.Colour.orange(),
                      description=f"**Message edited in {after.channel.mention} by {after.author.mention}:**\n{output}"
                      ).set_footer(
            text=f"Message ID: {after.id}, Channel ID: {after.channel.id}, Author ID: {after.author.id}"
        ).auto_author().timestamp_now()

        await before.guild.get_channel(Channel.MESSAGE_LOGS).send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Logging(bot))
