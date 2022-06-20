import datetime

import discord

from helpers.constants import Category, Role


class TicketQuestionsModal(discord.ui.Modal):
    def __init__(self, _type: str, question_dict: dict):
        super().__init__(title=f"Open Ticket - {question_dict[_type]['name']}")

        self._type = _type
        self.question_dict = question_dict
        self.questions = question_dict[_type]["questions"]
        self.responses = []

        self.question1 = discord.ui.TextInput(label=self.questions[0])
        self.add_item(self.question1)

        if len(self.questions) >= 2:
            self.question2 = discord.ui.TextInput(label=self.questions[1])
            self.add_item(self.question2)

            if len(self.questions) >= 3:
                self.question3 = discord.ui.TextInput(label=self.questions[2])
                self.add_item(self.question3)

                if len(self.questions) >= 4:
                    self.question4 = discord.ui.TextInput(label=self.questions[3])
                    self.add_item(self.question4)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.TextInput):
                self.responses.append(child.value)

        embed = discord.Embed(title=self.question_dict[str(self._type)]["name"], colour=discord.Colour.green(),
                              description="**Commands:**\n"
                                          "`-close [reason]` : close the ticket\n"
                                          "`-adduser [user]` : add someone else to the ticket\n"
                                          "`-removeuser [user]` : remove someone else from the ticket")
        embed.set_author(name=interaction.user, icon_url=interaction.user.avatar)

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


class ShortTextInputModal(discord.ui.Modal):
    def __init__(self, title: str, label: str, placeholder: str):
        super().__init__(title=title)

        self.text = None
        self.text_input = discord.ui.TextInput(label=label, placeholder=placeholder, required=False)
        self.add_item(self.text_input)

        self.response = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.text = self.text_input.value
        self.response = interaction.response
        self.stop()
