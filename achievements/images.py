from achievements.achievements import achievements, ACHIEVEMENT_BORDERS
from helpers.utils import deep_update_dict

from collections import OrderedDict
import discord
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from math import ceil
import aiohttp
import datetime
import io
import os
import json
import time

font_0 = ImageFont.truetype('Roboto-Medium.ttf', 20)
font_1 = ImageFont.truetype('Roboto-thin.ttf', 15)


def mask_circle_transparent(pil_img, blur_radius, offset=0):
    offset = blur_radius * 2 + offset
    mask = Image.new("L", pil_img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((offset, offset, pil_img.size[0] - offset, pil_img.size[1] - offset), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))

    result = pil_img.copy()
    result.putalpha(mask)
    return result


def achievement_box(image, x: int, y: int, name: str, definition: str):
    draw = ImageDraw.Draw(image)
    draw.rectangle([(x, y), (x + 300, y + 100)], 'white', 'black')
    draw.text((x + 10, y + 10), name, 'black', font=font_0)
    draw.text((x + 10, y + 40), definition, 'black', font=font_1)


def add_page(image, page: int, repeat: int, total_pages):
    x_pos = 100
    y_pos = 100
    loop = range(0, repeat)
    for i in loop:
        page_num = ((page - 1) * 3) + i
        name = [k for k in achievements if "hidden" not in achievements[k]][page_num]
        ImageDraw.Draw(image).text((x_pos, 540), f"page {page} of {total_pages}", 'black', font=font_1)
        achievement_box(image, x_pos, y_pos, name, achievements[name]["description"])
        y_pos += 150


def achievement_page(page, filename="image.png"):
    visible_achievements = {k:v for k, v in achievements.items() if "hidden" not in v}
    last_page = ceil(len(visible_achievements) / 3)
    mod = len(visible_achievements) % 3
    # image = Image.new('RGBA', (500, 600), (0, 0, 0, 0))
    image = Image.open("assets/achievement_backgrounds/default_background.png")
    if page == last_page:
        add_page(image, page, mod, last_page)
    else:
        add_page(image, page, 3, last_page)
    return image.save(filename, format='PNG')


def timeline_card(image, draw, achievement, timestamp, x, y):
    draw.rectangle([(x, y), (x + 400, y + 75)], 'white', 'black')
    draw.text((x + 10, y + 10), achievement, 'green', font=font_0)
    draw.text((x + 10, y + 45),
              f"achieved at {datetime.datetime.fromtimestamp(timestamp).strftime('%d/%m/%y %H:%M')}",
              'black', font=font_1)
    return image


async def achievement_timeline(user: discord.User, payload, page=1):

    # constants
    achieved = OrderedDict([(z, payload["achievements"][z])
                            for z in sorted(list(payload["achievements"].keys()),
                                            key=lambda x: payload["achievements"][x])])
    last_page = ceil(len(payload["achievements"]) / 4)
    mod = len(payload["achievements"]) % 4
    slice_start, slice_end = (-mod or -4, None) if page == last_page else (4 * (page-1), 4 * (page-1) + 4)
    achieved_page = {k: v for k, v in list(achieved.items())[slice_start:slice_end]}
    user_page_path = f"image_cache/user_achievements/{user.id}"

    percentage_achieved = len(payload["achievements"]) / len(achievements)
    border = None
    for i, kv in enumerate(ACHIEVEMENT_BORDERS.items()):
        milestone, border_type = kv
        if percentage_achieved >= milestone:
            border = border_type

    if page < 1 or page > last_page:
        raise ValueError

    # serve from cache
    json_cache = {}
    if f"{user.id}.json" in os.listdir("image_cache/user_achievements"):
        with open(f"{user_page_path}.json") as f:
            json_cache = json.load(f)
        if str(page) in json_cache["achievements"]\
                and json_cache["achievements"][str(page)] == list(achieved_page.keys())\
                and json_cache["uname"] == str(user)\
                and json_cache["avatar"] == str(user.avatar_url)\
                and json_cache["border_type"] == border\
                and json_cache["background_image"] == payload["background"]:
            return

    # generation
    image = Image.open(f"assets/achievement_backgrounds/{payload['background']}")
    async with aiohttp.ClientSession() as session:
        async with session.get(str(user.avatar_url).replace('gif', 'png')) as resp:
            avatar = Image.open(io.BytesIO(await resp.content.read()))
    x, y = 50, 100
    if border:
        border_image = Image.open(f"assets/achievement_borders/{border}.png").convert("RGBA")
        image.paste(border_image, (0, 0), border_image)
    draw = ImageDraw.Draw(image)
    draw.rectangle([(x, y - 50), (x + 400, y + 10)])
    avatar = mask_circle_transparent(avatar, 4)
    avatar = avatar.resize((50, 50))
    image.paste(avatar, (60, 55), mask=avatar)
    draw.text((x + 80, 70), str(user), 'black', font=font_0)
    draw.text((x, 540), f"page {page} of {last_page}", 'black', font=font_1)

    for i, achievement in enumerate(achieved_page, 1):
        image = timeline_card(image, draw, achievement, achieved_page[achievement], x, y * i + 50)

    # save to cache
    json_cache = deep_update_dict(json_cache, {
            "image_files": [f"{user_page_path}_{page}.png"],
            "uname": str(user),
            "avatar": str(user.avatar_url),
            "border_type": border,
            "background_image": payload["background"],
            "achievements": {
              str(page): list(achieved_page.keys())
            },
            "last_called": time.time()
    })
    with open(f"{user_page_path}.json", "w") as f:
        json.dump(json_cache, f)
    return image.save(f"{user_page_path}_{page}.png", format="PNG")
