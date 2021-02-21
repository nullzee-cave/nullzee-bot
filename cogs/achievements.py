from discord.ext import commands
import discord
from perks.achievements import achievements
from helpers.events import Emitter
from PIL import Image, ImageDraw, ImageFont
from math import ceil


class ShallowContext:
    def __init__(self):
        self.channel = None
        self.author = None
        self.guild = None

    @classmethod
    async def create(cls, member: discord.Member):
        self = cls()
        self.channel = (member.dm_channel or await member.create_dm())
        self.author = member
        self.guild = member.guild
        return self

    async def send(self, *args, **kwargs):
        return await self.channel.send(*args, **kwargs)

font_0 = ImageFont.truetype('Roboto-Medium.ttf', 20)
font_1 = ImageFont.truetype('Roboto-thin.ttf', 15)

names = []
descriptions = []
for achievement in achievements:
    names.append(achievement)
    descriptions.append(achievements[achievement]["description"])

def achievement_box(image, x: int, y: int, name: str, definition: str):
    draw = ImageDraw.Draw(image)
    draw.rectangle([(x, y), (x + 300, y + 100)], 'white', 'black')
    draw.text((x + 10, y + 10), name, 'black', font=font_0)
    draw.text((x + 10, y + 40), definition, 'black', font=font_1)

def addPage(image, page: int, repeat: int):
    xPos = 100
    yPos = 100
    loop = range(0, repeat)
    for i in loop:
        pageNum = ((page - 1) * 3) + i
        achievement_box(image, xPos, yPos, names[pageNum], descriptions[pageNum])
        yPos += 150

def achievement_page(page):
    lastPage = ceil(len(achievements) / 3)
    mod = len(achievements) % 3
    image = Image.new('RGBA', (500, 600), (0, 0, 0, 0))
    if page == lastPage:
        addPage(image, page, mod)
    else:
        addPage(image, page, 3)
    return image.save('image.png', format='PNG')

class Achievements(commands.Cog):

    def __init__(self, bot):
        self.hidden = True
        self.bot: commands.Bot = bot
        self.emitter = Emitter()

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.emitter.emit("message", await self.bot.get_context(message))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            await self.emitter.emit("update_roles", await ShallowContext.create(after), after.roles)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        await self.emitter.emit("command", ctx, ctx.command.name)

    @commands.command()
    async def achievement(self, ctx, page: int):
        achievement_page(page)
        await ctx.send(file=discord.File("image.png"))


def setup(bot):
    bot.add_cog(Achievements(bot))
