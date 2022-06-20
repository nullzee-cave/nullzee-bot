from functools import wraps

import discord

from helpers.constants import Category
from helpers.utils import get_file_json

TICKET_TOPIC_REGEX = r"opened by (?P<user>.+#\d{4}) \((?P<user_id>\d+)\) at (?P<time>.+)"


ticket_types = {
    "💰": {
        "name": "Giveaway Donation",
        "questions": [
            "How long will the giveaway last?",
            "How many winners will there be?",
            "What requirements must users meet in order to be eligible to win?",
            "What is the prize?"
        ],
    },
    "🛄": {
        "name": "Giveaway Claim",
        "questions": [
            "What is the link to the giveaway that you won?",
            "What is the name of the account on which you wish to claim the giveaway?",
            "At what time (and timezone) do you want to collect the prize?"
        ],
    },
    "❓": {
        "name": "Other",
        "questions": [
            "Why have you opened this ticket?"
        ],
    },
}


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
