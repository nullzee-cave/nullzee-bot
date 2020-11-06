from helpers import utils
import time

def warn_payload(*, offender_id, mod_id, reason):
    return {
        "id": utils.nanoId(),
        "offender_id": offender_id,
        "mod_id": mod_id,
        "type": "warn",
        "reason": reason,
        "timestamp": round(time.time())
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
        "ends": round(time.time()) + duration,
        "active": True,
        "permanent": True if not duration else False
    }