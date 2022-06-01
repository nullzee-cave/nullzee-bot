from achievements.achievements import achievements, ACHIEVEMENT_BORDERS
from helpers.utils import deep_update_dict, json_meta, json_meta_converter

from collections import OrderedDict
import discord
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio
from math import ceil
import aiohttp
import datetime
import io
import os
import json
import time

font_medium = ImageFont.truetype("assets/fonts/Roboto-Medium.ttf", 20)
font_thin = ImageFont.truetype("assets/fonts/Roboto-Thin.ttf", 15)
font_bold = ImageFont.truetype("assets/fonts/Roboto-Bold.ttf", 15)
font_title = ImageFont.truetype("assets/fonts/Roboto-Bold.ttf", 80)

BackgroundMeta = json_meta("assets/achievement_backgrounds/bg_meta", {
    "aliases": [],
    "text_colour": "black",
    "box_background_colour": "white",
    "box_text_colour": "black",
    "box_border_colour": "black",
    "purchasable": False,
    "credit": "art by aei",
    "role_req": None,
    "role_req_strategy": "any",
    "claimable": False,
    "preview": True,
    "cost": 0,
})

BackgroundConverter = json_meta_converter(BackgroundMeta)

BoxBorderMeta = json_meta("assets/achievement_box_borders/box_border_meta", {
    "cost": 0,
    "purchasable": False,
    "aliases": [],
    "role_req": None,
    "role_req_strategy": "any",
    "preview": True
})
BoxBorderConverter = json_meta_converter(BoxBorderMeta)


def wrap_text(text: str, width, font: ImageFont.FreeTypeFont):
    length = font.getlength(text)
    if length <= width:
        return text
    cum_text = ""
    output = ""
    for word in text.split():
        if font.getlength(cum_text) + font.getlength(word) > width:
            output += "\n"
            cum_text = ""
        output += word + " "
        cum_text += word + " "
    return output


def should_regen(json_cache, *, page, user, border, background="default", achieved_page, embed_colour, box_border,
                 total_pages):
    if str(page) not in json_cache["pages"]:
        return True
    page_data = json_cache["pages"][str(page)]
    return not (page_data["achievements"] == list(achieved_page.keys())
                and page_data["total_pages"] == total_pages
                and page_data["embed_colour"] == embed_colour
                and page_data["uname"] == str(user)
                and page_data["avatar"] == str(user.avatar_url)
                and page_data["border_type"] == border
                and page_data["background_image"] == background
                and page_data["box_border"] == box_border)


def cache_for(user_id):
    try:
        with open(f"image_cache/user_achievements/{user_id}.json") as f:
            cache_data = json.load(f)
    except FileNotFoundError:
        cache_data = {
            "image_files": [],
            "pages": {},
            "last_called": 0,
            "regen_animated": True
        }
    return cache_data


def background_preview(name):
    w, h = font_title.getsize(" ".join(name.upper()))
    image = Image.open(f"assets/achievement_backgrounds/{name}.png").convert("RGBA")
    border = Image.open("assets/achievement_borders/default.png").convert("RGBA")
    image.paste(border, (0, 0), border)
    text = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(text)
    draw.text(((500 - w) / 2, (600 - h) / 2), " ".join(name.upper()), font=font_title, fill=(0, 0, 0, 95))
    save_path = f"image_cache/static_background_previews/{name}.png"
    combined = Image.alpha_composite(image, text)
    combined.save(save_path)
    return save_path


def box_border_preview(bb_name):
    bg = Image.open("assets/achievement_backgrounds/default.png").convert("RGBA")
    bb = Image.open(f"assets/achievement_box_borders/{bb_name}.png").convert("RGBA")
    bd = Image.open("assets/achievement_borders/default.png").convert("RGBA")
    bg.paste(bd, (0, 0), bd)
    draw = ImageDraw.Draw(bg)
    draw.rectangle([(50, 263), (449, 338)], BackgroundMeta.get().default.box_backround_colour)
    bg.paste(bb, (48, 261), bb)
    w, h = font_title.getsize(bb_name)
    draw.text(((500 - w) / 2, (600 - h) / 2), bb_name, BackgroundMeta.get().default.box_text_colour, font=font_title)
    save_path = f"image_cache/static_boxborder_previews/{bb_name}.png"
    bg.save(save_path)
    return save_path


def mask_circle_transparent(pil_img, blur_radius, offset=0):
    offset = blur_radius * 2 + offset
    mask = Image.new("L", pil_img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((offset, offset, pil_img.size[0] - offset, pil_img.size[1] - offset), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))

    result = pil_img.copy()
    result.putalpha(mask)
    return result


def achievement_page(page, filename="image.png"):
    visible_achievements = {k: v for k, v in achievements.items() if "hidden" not in v}
    last_page = ceil(len(visible_achievements) / 3)
    mod = len(visible_achievements) % 3
    image = Image.open("assets/achievement_backgrounds/default.png").convert("RGBA")
    border_image = Image.open(f"assets/achievement_borders/default.png").convert("RGBA")
    image.paste(border_image, (0, 0), border_image)
    per_page = mod if page == last_page else 3
    ##
    x_pos = 100
    y_pos = 100
    loop = range(0, per_page)
    draw = ImageDraw.Draw(image)
    draw.text((x_pos - 50, 555), f"page {page + 1} of {last_page}", BackgroundMeta.get().default.text_colour,
              font=font_bold)
    draw.text((490 - x_pos, 555), "art by aei", BackgroundMeta.get().default.text_colour, font=font_bold)
    for i in loop:
        page_num = ((page - 1) * 3) + i
        name = [k for k in achievements if "hidden" not in achievements[k]][page_num]
        draw.rectangle([(x_pos, y_pos), (x_pos + 300, y_pos + 100)], BackgroundMeta.get().default.box_background_colour,
                       BackgroundMeta.get().default.box_text_colour)
        draw.text((x_pos + 10, y_pos + 10), name, "black", font=font_medium)
        draw.text((x_pos + 10, y_pos + 40), wrap_text(achievements[name]["description"], 280, font_thin), "black",
                  font=font_thin)
        y_pos += 150
    image.save(filename, format="PNG")
    return filename


async def achievement_timeline(user: discord.User, payload, page=1):
    # constants
    achieved = OrderedDict([(z, payload["achievements"][z])
                            for z in sorted(list(payload["achievements"].keys()),
                                            key=lambda x: payload["achievements"][x])])
    last_page = ceil(len(payload["achievements"]) / 4)
    mod = len(payload["achievements"]) % 4
    slice_start, slice_end = (-mod or -4, None) if page == last_page else (4 * (page - 1), 4 * (page - 1) + 4)
    achieved_page = {k: v for k, v in list(achieved.items())[slice_start:slice_end]}
    user_page_path = f"image_cache/user_achievements/{user.id}"
    embed_colour = payload["embed_colour"]
    background = payload["background_image"]
    box_border_name = payload["box_border"] if "box_border" in payload else "default"

    percentage_achieved = sum([achievements[z]["value"] for z in payload["achievements"]]) / sum(
                              [achievements[z]["value"] for z in achievements])
    border = "default"
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
        if not should_regen(json_cache, page=page, user=user, border=border, background=background,
                            achieved_page=achieved_page, embed_colour=embed_colour, box_border=box_border_name,
                            total_pages=last_page):
            return
    # generation
    image = Image.open(f"assets/achievement_backgrounds/{payload['background_image']}.png").convert("RGBA")
    if background == "cubes":
        try:
            layer = Image.new("RGBA", image.size, payload["embed_colour"] if payload["embed_colour"].startswith(
                "#") else f"#{payload['embed_colour']}")
        except (ValueError, KeyError):
            layer = Image.new("RGBA", image.size, "#00FF00")
        image = Image.blend(image, layer, 0.5)
    async with aiohttp.ClientSession() as session:
        async with session.get(str(user.avatar_url).replace("gif", "png")) as resp:
            avatar_raw = Image.open(io.BytesIO(await resp.content.read())).convert("RGBA")
    x, y = 50, 100
    box_border = Image.open(
        f"assets/achievement_box_borders/{box_border_name}.png") \
        .convert("RGBA")
    border_image = Image.open(f"assets/achievement_borders/{border}.png").convert("RGBA")
    image.paste(border_image, (0, 0), border_image)
    draw = ImageDraw.Draw(image)
    # draw.rectangle([(x, y - 50), (x + 400, y + 10)], BackgroundMeta.get()[background].box_backround_colour)
    draw.rectangle([(x, y - 55), (x + 399, y + 20)], BackgroundMeta.get()[background].box_backround_colour)
    image.paste(box_border, (x - 4, y - 59), box_border)
    avatar = Image.new("RGBA", avatar_raw.size, "WHITE")
    avatar.paste(avatar_raw, (0, 0), avatar_raw)
    avatar = mask_circle_transparent(avatar, 4)
    avatar = avatar.resize((50, 50))
    image.paste(avatar, (60, 59), mask=avatar)
    draw.text((x + 80, 75), str(user), BackgroundMeta.get()[background].box_text_colour, font=font_medium)
    draw.text((x - 15, 555), f"page {page} of {last_page}", BackgroundMeta.get()[background].text_colour,
              font=font_bold)
    draw.text((450 - x, 555), BackgroundMeta.get()[background].credit, BackgroundMeta.get()[background].text_colour,
              font=font_bold)

    for i, achievement in enumerate(achieved_page, 1):
        y_pos = y * i + 50
        # image = timeline_card(image, draw, achievement, achieved_page[achievement], x, y * i + 50)
        draw.rectangle([(x, y_pos), (x + 399, y_pos + 75)], "white")  # , "black")
        image.paste(box_border, (x - 4, y_pos - 4), box_border)
        draw.text((x + 10, y_pos + 10), achievement, "green", font=font_medium)
        draw.text((x + 10, y_pos + 45),
                  f"achieved at {datetime.datetime.fromtimestamp(achieved_page[achievement]).strftime('%d/%m/%y %H:%M')}",
                  "black", font=font_thin)

    # save to cache
    json_cache = deep_update_dict(json_cache, {
        "image_files": [f"{user_page_path}_{page}.png"],
        "pages": {
            str(page): {
                "achievements": list(achieved_page.keys()),
                "total_pages": last_page,
                "uname": str(user),
                "avatar": str(user.avatar_url),
                "border_type": border,
                "background_image": payload["background_image"],
                "box_border": box_border_name,
                "embed_colour": embed_colour,
            }
        },
        "last_called": time.time()
    })
    with open(f"{user_page_path}.json", "w") as f:
        json.dump(json_cache, f)
    image.save(f"{user_page_path}_{page}.png", format="PNG")
    return True


async def achievement_timeline_animated(user: discord.User, payload):
    last_page = ceil(len(payload["achievements"]) / 4)
    image_dir = "image_cache/user_achievements"
    has_created = []
    user_page_path = f"image_cache/user_achievements/{user.id}"
    cache_data = cache_for(user.id)
    for page in range(1, last_page + 1):
        has_created.append(await achievement_timeline(user, payload, page))
    if True not in has_created and f"{user.id}_animated.gif" in os.listdir(image_dir) and \
            not cache_data["regen_animated"]:
        return
    pages = []
    for filename in sorted(
            filter(lambda fname: fname.endswith(".png") and fname.startswith(str(user.id)), os.listdir(image_dir)),
            key=lambda fname: int(fname.split("_")[1][:-4])):
        if filename.endswith(".png") and filename.startswith(str(user.id)):
            file_path = os.path.join(image_dir, filename)
            pages.append(imageio.imread(file_path))
    imageio.mimsave(f"image_cache/user_achievements/{user.id}_animated.gif", pages, fps=0.5)
    with open(f"{user_page_path}.json") as f:
        cache_data = json.load(f)
    cache_data["image_files"].append(f"{user_page_path}_animated.gif")
    cache_data["regen_animated"] = False
    with open(f"{user_page_path}.json", "w") as f:
        json.dump(cache_data, f)
