from api_key import userColl
from helpers.events import Subscriber
from helpers.utils import get_user
from helpers.constants import Role

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
    "Rich": {
        "listeners": {
            "update_roles": lambda ctx, roles: Role.BOOSTER in [z.id for z in roles]
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
        "description": "Purchase `staffNickChange` from `-shop`"
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
        "description": "Purchase `deadChatPing` from `-shop`"
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
    # TODO:
    #   Establishing Connections (*)
    #   Twitch Main (*)
    #   funny
    #   hilarious
    #   helpful
    #   leader
    #   creative
    #   Generous I
    #   Generous II
    #   Lucky!
}


async def award_achievement(ctx, data, name):
    if name in data["achievements"]:
        return
    if "cb" in achievements[name]:
        await achievements[name]["cb"](ctx)
    if "response" in achievements[name]:
        await ctx.send(achievements[name]["response"].format(ctx))
    else:
        await ctx.send(f"Congratulations {ctx.author.mention}, you just achieved `{name}`!")
    await userColl.update_one({"_id": str(ctx.author.id)}, {"$push": {"achievements": name}})


def listeners_for(event):
    return [z for z in achievements if "listeners" in achievements[z] and event in achievements[z]["listeners"]]


@Subscriber().listen_all()
async def listen(event, ctx, *args, **kwargs):
    user_data = kwargs.get("user_data", await get_user(ctx.author))
    for achievement in listeners_for(event):
        if achievements[achievement]["listeners"][event](ctx, *args, **kwargs):
            await award_achievement(ctx, user_data, achievement)
