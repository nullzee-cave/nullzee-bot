import time

from api_key import userColl
from helpers.events import Subscriber
from helpers.utils import get_user
from helpers.constants import Role, Channel

ACHIEVEMENT_BORDERS = {
    0.2: "bronze",
    0.5: "silver",
    0.8: "gold"
}

achievements = {
    "Hello, World!": {
        "listeners": {
            "message": lambda msg: not msg.author.bot
        },
        "description": "Send your first message in the server"
    },
    "Level Collector I": {
        "listeners": {
            "level_up": lambda _, level: level == 10
        },
        "description": "Reach level 10"
    },
    "Level Collector II": {
        "listeners": {
            "level_up": lambda _, level: level == 30
        },
        "description": "Reach level 30"
    },
    "Level Collector III": {
        "listeners": {
            "level_up": lambda _, level: level == 50
        },
        "description": "Reach level 50"
    },
    "Role collector I": {
        "listeners": {
            "update_roles": lambda _, roles: len(roles) > 10
        },
        "description": "Have 10 roles"
    },
    "Role collector II": {
        "listeners": {
            "update_roles": lambda _, roles: len(roles) > 25
        },
        "description": "Have 25 roles",
    },
    "Role collector III": {
        "listeners": {
            "update_roles": lambda _, roles: len(roles) > 50
        },
        "description": "Have 50 roles"
    },
    "Rich": {
        "listeners": {
            "update_roles": lambda ctx, roles: Role.BOOSTER in [z.id for z in roles]
            # "update_roles": lambda ctx, roles: print(Role)
        },
        "description": "Nitro boost the server"
    },
    "Prime Log": {
        "listeners": {
            "update_roles": lambda _, roles: Role.TWITCH_SUB in [z.id for z in roles]
        },
        "description": "Subscribe to Nullzee on twitch and link your account through discord!"
    },
    "Full of ideas": {
        "listeners": {
            "command": lambda _, name: name == "suggest"
        },
        "description": "Make your first suggestion"
    },
    "Talkative I": {
        "listeners": {
            "update_role": lambda _, roles: Role.VC_LORD in [z.id for z in roles]
        },
        "description": "Become a VC lord"
    },
    "Talkative II": {
        "listeners": {
            "update_role": lambda _, roles: Role.VC_GOD in [z.id for z in roles]
        },
        "description": "Become a VC god"
    },
    "Mean": {
        "listeners": {
            "points_spent": lambda _, name: name == "staffNickChange"
        },
        "description": "Purchase staffNickChange from -shop"
    },
    "Frugal I": {
        "listeners": {
            "point_earned": lambda _, points: points == 100
        },
        "description": "Save up 100 points"
    },
    "Frugal II": {
        "listeners": {
            "point_earned": lambda _, points: points == 200
        },
        "description": "Save up 200 points"
    },
    "Frugal III": {
        "listeners": {
            "point_earned": lambda _, points: points == 300
        },
        "description": "Save up 300 points"
    },
    "Necromancer": {
        "listeners": {
            "points_spent": lambda _, name: name == "deadChatPing"
        },
        "description": "Purchase deadChatPing from -shop"
    },
    "Up to date": {
        "listeners": {
            "update_roles": lambda _, roles: {Role.POLL_PING, Role.QOTD_PING, Role.EVENT_PING, Role.DEAD_CHAT_PING,
                                              Role.GIVEAWAY_PING, Role.ANNOUNCEMENT_PING} <= set([z.id for z in roles])
        },
        "description": "Have all ping roles"
    },
    "Agreeable": {
        "listeners": {
            "suggestion_stage_2": lambda _: True
        },
        "description": "Get 15 more upvotes than downvotes on one of your suggestions"
    },
    "Generous I": {
        "listeners": {
            "giveaway_create[donor]": lambda _, payload: payload["channel"] == Channel.MINI_GIVEAWAY
        },
        "description": "Donate for a mini-giveaway"
    },
    "Generous II": {
        "listeners": {
            "giveaway_create[donor]": lambda _, payload: payload["channel"] == Channel.GIVEAWAY
        },
        "description": "Donate for a large giveaway"
    },
    "Lucky!": {
        "listeners": {
            "giveaway_win": lambda ctx: ctx.channel.id == Channel.GIVEAWAY
        },
        "description": "Win a large giveaway"
    },
    "Funny": {
        "listeners": {
            "pinned_starred": lambda _: True
        },
        "description": "Have one of your messages pinned or starred"
    },
    "Establishing Connections": {
        "listeners": {},
        "description": "Send a message in twitch chat after linking your twitch to your discord"
    },
    "Bad boy": {
      "listeners": {
          "point_change": lambda _, points: points > 0
      },
      "description": "Have some points refunded"
    },
    "Colourful": {
        "listeners": {
            "points_spent": lambda _, name: name == "embedColour"
        },
        "description": "Change your embed colour",
    },

    "Great Job": {
        "listeners": {
            "message": lambda msg: msg.guild and msg.author.guild_permissions.manage_messages,
            "update_roles": lambda ctx, _: ctx.author.guild_permissions.manage_messages
        },
        "description": "Get any staff position",
        "hidden": True
    },
    "Twitch Main": {
        "listeners": {},
        "description": "",
        "hidden": True
    }

    # TODO:
    #   Establishing Connections (*)
    #   Twitch Main (*)
}


async def award_achievement(ctx, data, name):
    return
    if name in data["achievements"]:
        return
    string = ""
    if "cb" in achievements[name]:
        await achievements[name]["cb"](ctx)
    if "response" in achievements[name]:
        await ctx.send(achievements[name]["response"].format(ctx))
    if "db_rewards" in achievements[name]:
        await userColl.update_one({"_id": str(ctx.author.id)}, {"$inc": achievements[name]["db_rewards"]})
        string += f" and earned {','.join(f'{v} {k}' for k, v in achievements[name]['db_rewards'])}"
    await ctx.send(f"Congratulations {ctx.author.mention}, you just achieved `{name}`{string}!")
    await userColl.update_one({"_id": str(ctx.author.id)}, {"$set": {f"achievements.{name}": time.time()}})


def listeners_for(event):
    return [z for z in achievements if "listeners" in achievements[z] and event in achievements[z]["listeners"]]


@Subscriber().listen_all()
async def listen(event, ctx, *args, **kwargs):
    user_data = kwargs.get("user_data", await get_user(ctx.author))
    for achievement in listeners_for(event):
        if achievements[achievement]["listeners"][event](ctx, *args, **kwargs):
            await award_achievement(ctx, user_data, achievement)
