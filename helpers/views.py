import discord


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