class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


EVENTS = [
    "message",
    "update_roles",
    "point_earned",
    "points_spent",
    "points_changed",
    "experience_earned",
    "level_up", "command",
    "suggestion_stage_2",
    "giveaway_start[donor]",
    "giveaway_win",
    "pinned_starred",
    "hypixel_link",
    "vc_minute_gain",
    "bad_suggestion",
    "waste",
]


class Emitter(metaclass=Singleton):

    @classmethod
    async def emit(cls, event, *args, **kwargs):
        await Subscriber().emit(event, *args, **kwargs)


class Subscriber(metaclass=Singleton):

    def __init__(self):
        self.__listeners = {}
        self.__global_listeners = []

    async def emit(self, event, *args, **kwargs):
        for coro in self.__global_listeners:
            await coro(event, *args, **kwargs)
        if event in self.__listeners:
            for coro in self.__listeners[event]:
                await coro(*args, **kwargs)

    def add_listener(self, event, coro):
        if event in self.__listeners:
            self.__listeners[event].append(coro)
        else:
            self.__listeners[event] = [coro]

    def listen_all(self):
        def decorator(func):
            self.__global_listeners.append(func)

            def wrapper(*args, **kwargs):
                pass

            return wrapper

        return decorator

    def listen(self, event):
        def decorator(func):
            self.add_listener(event, func)

            def wrapper(*args, **kwargs):
                pass

            return wrapper

        return decorator
