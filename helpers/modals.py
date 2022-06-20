import discord


class TicketQuestionsModal(discord.ui.Modal):
    def __init__(self, _type: str, question_dict: dict):
        super().__init__(title=f"Open Ticket - {question_dict[_type]['name']}")
        self.interaction = None

        self._type = _type
        self.question_dict = question_dict
        self.questions = question_dict[_type]["questions"]
        self.responses = []

        self.question1 = discord.ui.TextInput(label="Q1", placeholder=self.questions[0],
                                              style=discord.TextStyle.paragraph)
        self.add_item(self.question1)

        if len(self.questions) >= 2:
            self.question2 = discord.ui.TextInput(label="Q2", placeholder=self.questions[1],
                                                  style=discord.TextStyle.paragraph)
            self.add_item(self.question2)

            if len(self.questions) >= 3:
                self.question3 = discord.ui.TextInput(label="Q3", placeholder=self.questions[2],
                                                      style=discord.TextStyle.paragraph)
                self.add_item(self.question3)

                if len(self.questions) >= 4:
                    self.question4 = discord.ui.TextInput(label="Q4", placeholder=self.questions[3],
                                                          style=discord.TextStyle.paragraph)
                    self.add_item(self.question4)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.TextInput):
                self.responses.append(child.value)
        self.interaction = interaction
        self.stop()


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
