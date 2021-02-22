from achievements.achievements import achievements

from PIL import Image, ImageDraw, ImageFont
from math import ceil

font_0 = ImageFont.truetype('Roboto-Medium.ttf', 20)
font_1 = ImageFont.truetype('Roboto-thin.ttf', 15)


def achievement_box(image, x: int, y: int, name: str, definition: str):
    draw = ImageDraw.Draw(image)
    draw.rectangle([(x, y), (x + 300, y + 100)], 'white', 'black')
    draw.text((x + 10, y + 10), name, 'black', font=font_0)
    draw.text((x + 10, y + 40), definition, 'black', font=font_1)


def add_page(image, page: int, repeat: int):
    x_pos = 100
    y_pos = 100
    loop = range(0, repeat)
    for i in loop:
        page_num = ((page - 1) * 3) + i
        name = list(achievements.keys())[page_num]
        achievement_box(image, x_pos, y_pos, name, achievements[name]["description"])
        y_pos += 150


def achievement_page(page, filename="image.png"):
    last_page = ceil(len(achievements) / 3)
    mod = len(achievements) % 3
    image = Image.new('RGBA', (500, 600), (0, 0, 0, 0))
    if page == last_page:
        add_page(image, page, mod)
    else:
        add_page(image, page, 3)
    return image.save(filename, format='PNG')
