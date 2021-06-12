

class Constant(type):
    _constants = {}

    def __new__(mcs, *args, **kwargs):
        self = super(Constant, mcs).__new__(mcs, *args, **kwargs)
        mcs._constants[self] = args[2]
        return self

    def __getitem__(self, item):
        return self._constants[self][item]



class Role(metaclass=Constant):
    BOOSTER     = 668724083718094869
    TWITCH_SUB  = 668736363297898506
    RETIRED     = 706285767898431500
    VC_LORD     = 682656964123295792
    VC_GOD      = 804095281036525638
    EVENT_PING  = 733698696159690838
    ANNOUNCEMENT_PING = 738691495317602344
    GIVEAWAY_PING = 735238184832860402
    POLL_PING   = 738691450417709077
    DEAD_CHAT_PING = 749178299518943343
    QOTD_PING   = 749178235845345380
    EVENT_HOSTER= 746469205427224588
    TRAINEE     = 675031583954173986
    STAFF       = 667953757954244628
    ADMIN       = 685027474522112000
    EVENT_WINNER= 734023673236947076
    TALENTED    = 703135588819271701
    MEGA_FAN    = 678152766891360298
    TRUSTED_MEMBER = 668722188764839946
    CARP_GANG   = 743940100018405497
    BANANA_GANG = 743940139901780010
    SB_SWEAT    = 668735481458065438
    GOOBY       = 810126462509645845
    MINI_GIVEAWAY_DONOR = 681900342409035837
    LARGE_GIVEAWAY_DONOR = 681900556788301843
    MINI_GIVEAWAY_WIN = 672141836567183413
    LARGE_GIVEAWAY_WIN = 691351294048337941
    TICKET_PING = 821791342614544414

    # categories:
    @classmethod
    def legacy(cls):
        return [
            cls.TRUSTED_MEMBER,
            cls.CARP_GANG,
            cls.BANANA_GANG,
            cls.SB_SWEAT,
            cls.GOOBY
        ]


class Channel(metaclass=Constant):
    GIVEAWAY        = 667960870697041942
    MINI_GIVEAWAY   = 735236900830576643
    QOTD_ANSWERS    = 749631176431370260
    SELF_PROMO      = 667960498448367668
    PETS            = 705106181559156888
    BOT_GAMES       = 685782425502220311
    NO_MIC          = 706920230089392260
    MOD_LOGS        = 667957285837864960
    MESSAGE_LOGS    = 849666627830415380
    TICKETS         = 821454390685597696
    MEMBER_COUNT_VC = 803967155246333991


class Skyblock(metaclass=Constant):
    SKILL_XP_REQUIREMENTS = [50, 175, 375, 675, 1175, 1925, 2925, 4425, 6425, 9925, 14925, 22425, 32425, 47425, 67425,
                             97425, 147425, 222425, 322425, 522425, 822425, 1222425, 1722425, 2322425, 3022425, 3822425,
                             4722425, 5722425, 6822425, 8022425, 9322425, 10722425, 12222425, 13822425, 15522425,
                             17322425, 19222425, 21222425, 23322425, 25522425, 27822425, 30222425, 32722425, 35322425,
                             38072425, 40972425, 44072425, 47472425, 51172425, 55172425, 59472425, 64072425, 68972425,
                             74172425, 79672425, 85472425, 91572425, 97972425, 104672425, 111672425]

    MAX_LEVEL_50_SKILLS = ["combat", "alchemy", "carpentry", "taming"]
