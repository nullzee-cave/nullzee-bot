from helpers import utils
import time
import datetime


def insert_message(payload, message):
    payload["message"] = f"{message.guild.id}-{message.channel.id}-{message.id}"
    return payload


def warn_payload(*, offender_id, mod_id, reason):
    return {
        "id": utils.nano_id(),
        "offender_id": offender_id,
        "mod_id": mod_id,
        "type": "warn",
        "reason": reason,
        "timestamp": round(time.time()),
        "expired": False
    }


def mute_payload(*, offender_id, mod_id, reason, duration):
    return {
        "id": utils.nano_id(),
        "offender_id": offender_id,
        "mod_id": mod_id,
        "type": "mute",
        "reason": reason,
        "timestamp": round(time.time()),
        "duration": duration,
        "duration_string": "{:0>8}".format(str(datetime.timedelta(seconds=duration))) if duration else "",
        "ends": round(time.time()) + duration if duration else 0,
        "active": True,
        "permanent": True if not duration else False,
        "expired": False

    }


def ban_payload(*, offender_id, mod_id, reason, duration, _id = None):
    return {
        "id": _id if _id else utils.nano_id(),
        "offender_id": offender_id,
        "mod_id": mod_id,
        "type": "ban",
        "reason": reason,
        "timestamp": round(time.time()),
        "duration": duration,
        "duration_string": "{:0>8}".format(str(datetime.timedelta(seconds=duration))) if duration else 0,
        "ends": round(time.time()) + duration if duration else 0,
        "active": True,
        "permanent": True if not duration else False,
        "expired": False

    }


def mass_ban_payload(*, offenders, mod_id, reason, duration, _id):
    return {
        "id": _id if _id else utils.nano_id(),
        "offenders": offenders,
        "offenders_string": "\n".join([f'{z.mention} - {z.id}' for z in offenders]),
        "mod_id": mod_id,
        "type": "ban",
        "reason": reason,
        "timestamp": round(time.time()),
        "duration": duration,
        "duration_string": "{:0>8}".format(str(datetime.timedelta(seconds=duration))) if duration else 0,
        "ends": round(time.time()) + duration if duration else 0,
        "active": True,
        "permanent": True if not duration else False,
        "expired": False
    }


def kick_payload(*, offender_id, mod_id, reason):
    return {
        "id": utils.nano_id(),
        "offender_id": offender_id,
        "mod_id": mod_id,
        "type": "kick",
        "reason": reason,
        "timestamp": round(time.time()),
        "expired": False
    }


def giveaway_payload(ctx, msg, *, channel, giveaway_time, winner_count, role_req_strategy=1, roles=[], level=0,
                     booster=False, content, donor):
    return {
        "_id": str(msg.id),
        "active": True,
        "mod": ctx.author.id,
        "channel": channel.id,
        "ends": giveaway_time,
        "winner_count": winner_count,
        "requirements": {
            "role_type": role_req_strategy,
            "roles": roles,
            "level": level,
            "booster": booster,
        },
        "content": content,
        "donor": donor.id
    }
