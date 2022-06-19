import discord


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
