import hjson


class Emote:
    def get(self, key: str):
        if self.custom is not None and key in self.custom:
            return self.custom.get(key)

        if key in self.default:
            return self.default.get(key)

        return None

    def __init__(self):
        self.default = hjson.load(open("config/emotes.default.hjson", "r"))
        try:
            self.custom = hjson.load(open("config/emotes.hjson", "r"))
        except FileNotFoundError:
            self.custom = None

        # fmt: off
        self.happy =     self.get('happy')
        self.love =      self.get('love')
        self.sad =       self.get('sad')
        self.angry =     self.get('angry')
        self.ree =       self.get('ree')
        self.scared =    self.get('scared')
        self.wtf =       self.get('wtf')
        self.ok =        self.get('ok')

        self.panic =     self.get('panic')
        self.facepalm =  self.get('facepalm')
        self.wave =      self.get('wave')
        self.hug_left =  self.get('hug_left')
        self.hug_right = self.get('hug_right')
        self.objection = self.get('objection')
        self.tagrage =   self.get('tagrage')

        self.yes =       self.get('yes')
        self.no =        self.get('no')
        self.welcome =   self.get('welcome')
        # fmt: on


emote = Emote()
