import datetime

import discord
import re
import chat_exporter
import io

from cogs.tickets import TICKET_TOPIC_REGEX
from helpers.constants import Channel, Category, Role
from helpers.modals import TicketQuestionsModal
from helpers.ticket_utils import ticket_types, can_open_ticket
from helpers.utils import Embed


class PersistentTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @can_open_ticket
    @discord.ui.button(label="Donate", emoji="💰", style=discord.ButtonStyle.green, custom_id="ticket_view:donate")
    async def ticket_donate(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketQuestionsModal(str(button.emoji), ticket_types)
        await interaction.response.send_modal(modal)
        await modal.wait()
        await self.create_ticket(modal)

    @can_open_ticket
    @discord.ui.button(label="Claim", emoji="🛄", style=discord.ButtonStyle.blurple, custom_id="ticket_view:claim")
    async def ticket_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketQuestionsModal(str(button.emoji), ticket_types)
        await interaction.response.send_modal(modal)
        await modal.wait()
        await self.create_ticket(modal)

    @can_open_ticket
    @discord.ui.button(label="Other", emoji="❓", style=discord.ButtonStyle.grey, custom_id="ticket_view:other")
    async def ticket_other(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketQuestionsModal(str(button.emoji), ticket_types)
        await interaction.response.send_modal(modal)
        await modal.wait()
        await self.create_ticket(modal)

    async def create_ticket(self, modal: TicketQuestionsModal):
        embed = discord.Embed(title=modal.question_dict[str(modal._type)]["name"], colour=discord.Colour.green(),
                              description="**Commands:**\n"
                                          "`-close [reason]` : close the ticket\n"
                                          "`-adduser [user]` : add someone else to the ticket\n"
                                          "`-removeuser [user]` : remove someone else from the ticket")
        embed.set_author(name=modal.interaction.user, icon_url=modal.interaction.user.avatar)

        embed.add_field(name=modal.questions[0], value=modal.responses[0], inline=False)
        if len(modal.questions) >= 2:
            embed.add_field(name=modal.questions[1], value=modal.responses[1], inline=False)

            if len(modal.questions) >= 3:
                embed.add_field(name=modal.questions[2], value=modal.responses[2], inline=False)

                if len(modal.questions) >= 4:
                    embed.add_field(name=modal.questions[3], value=modal.responses[3], inline=False)

        channel: discord.TextChannel = await modal.interaction.guild.create_text_channel(
            f"{modal.interaction.user.name}-{modal.interaction.user.discriminator}",
            category=modal.interaction.guild.get_channel(Category.TICKETS),
            topic=f"opened by {modal.interaction.user} ({modal.interaction.user.id}) at "
                  f"{datetime.datetime.now().strftime('%d/%m/%y %H:%M')}",
            overwrites={
                modal.interaction.guild.default_role: discord.PermissionOverwrite(
                    read_messages=False),
                modal.interaction.guild.get_role(
                    Role.STAFF): discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True),
                modal.interaction.guild.get_role(
                    Role.TRAINEE): discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True),
                modal.interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True)
            })

        start = await channel.send(f"<@&> {modal.interaction.user.mention}",
                                   embed=embed, view=PersistentInnerTicketView(channel.id))
        await start.pin()
        await modal.interaction.response.send_message(f"Ticket created! {start.jump_url}", ephemeral=True)
        embed = Embed(modal.interaction.user, colour=0x00ff00, title="Ticket opened",
                      description=f"{channel.name}\nReason: {modal.question_dict[modal._type]['name']}")
        embed.auto_author()
        log_channel = modal.interaction.guild.get_channel(Channel.MOD_LOGS)
        await log_channel.send(embed=embed)


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
        messages = [*reversed([z async for z in interaction.channel.history()])]
        html = "<!--\n"
        for message in messages:
            html += f"{message.author} | {message.created_at.strftime('%d/%m/%y %H:%M')}: {message.content}\n"
        html += "\n-->\n\n"
        transcript = await chat_exporter.export(interaction.channel, military_time=True, bot=interaction.client)
        html += transcript
        with open(f"transcripts/{interaction.channel.name}.html",
                  "w", encoding="utf-8") as f:
            f.write(html)
        user = re.search(TICKET_TOPIC_REGEX, interaction.channel.topic)
        user = int(user.group("user_id"))
        try:
            user = interaction.client.get_user(user)
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