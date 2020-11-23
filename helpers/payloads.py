from helpers import utils
import time
import datetime

def insert_message(payload, message):
    payload["message"] = f"{message.guild.id}-{message.channel.id}-{message.id}"
    return payload

def warn_payload(*, offender_id, mod_id, reason):
    return {
        "id": utils.nanoId(),
        "offender_id": offender_id,
        "mod_id": mod_id,
        "type": "warn",
        "reason": reason,
        "timestamp": round(time.time()),
        "expired": False
    }

def mute_payload(*, offender_id, mod_id, reason, duration):
    return {
        "id": utils.nanoId(),
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

def ban_payload(*, offender_id, mod_id, reason, duration):
    return {
        "id": utils.nanoId(),
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
def kick_payload(*,offender_id, mod_id,reason):
    return {
        "id": utils.nanoId(),
        "offender_id": offender_id,
        "mod_id": mod_id,
        "type": "kick",
        "reason": reason,
        "timestamp": round(time.time()),
        "expired": False
    }
