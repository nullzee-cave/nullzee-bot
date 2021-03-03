

class Constant(type):
    _constants = {}

    def __new__(mcs, *args, **kwargs):
        super(Constant, mcs).__new__(mcs, *args, **kwargs)
        mcs._constants[mcs] = args[2]
        return mcs._constants[mcs]

    def __class_getitem__(mcs, item):
        return mcs._constants[mcs]



class Role(metaclass=Constant):
    BOOSTER     = 668724083718094869
    TWITCH_SUB  = 668736363297898506
    VC_LORD     = 682656964123295792
    VC_GOD      = 804095281036525638
    EVENT_PING  = 733698696159690838
    ANNOUNCEMENT_PING = 738691495317602344
    GIVEAWAY_PING = 735238184832860402
    POLL_PING   = 738691450417709077
    DEAD_CHAT_PING = 749178299518943343
    QOTD_PING   = 749178235845345380
    TRAINEE     = 675031583954173986
    STAFF       = 667953757954244628
    ADMIN       = 685027474522112000

class Channel(metaclass=Constant):
    GIVEAWAY        = 667960870697041942
    MINI_GIVEAWAY   = 735236900830576643