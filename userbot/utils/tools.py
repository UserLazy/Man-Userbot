# Copyright (C) 2020 Adek Maulana
#
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import re
import hashlib
import asyncio
import shlex
import os
import requests
from os.path import basename
import os.path
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from html_telegraph_poster import TelegraphPoster
from typing import Optional, Union
from userbot import bot, LOGS
from PIL import Image
from typing import Tuple, Optional

from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator, DocumentAttributeFilename
from userbot import SUDO_USERS


async def md5(fname: str) -> str:
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def humanbytes(size: Union[int, float]) -> str:
    if size is None or isinstance(size, str):
        return ""

    power = 2**10
    raised_to_pow = 0
    dict_power_n = {0: "", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"


def time_formatter(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + " day(s), ") if days else "")
        + ((str(hours) + " hour(s), ") if hours else "")
        + ((str(minutes) + " minute(s), ") if minutes else "")
        + ((str(seconds) + " second(s), ") if seconds else "")
    )
    return tmp[:-2]


def human_to_bytes(size: str) -> int:
    units = {
        "M": 2 ** 20,
        "MB": 2 ** 20,
        "G": 2 ** 30,
        "GB": 2 ** 30,
        "T": 2 ** 40,
        "TB": 2 ** 40,
    }

    size = size.upper()
    if not re.match(r" ", size):
        size = re.sub(r"([KMGT])", r" \1", size)
    number, unit = [string.strip() for string in size.split()]
    return int(float(number) * units[unit])


async def is_admin(chat_id, user_id):
    req_jo = await bot(GetParticipantRequest(
        channel=chat_id,
        user_id=user_id
    ))
    chat_participant = req_jo.participant
    if isinstance(
            chat_participant,
            ChannelParticipantCreator) or isinstance(
            chat_participant,
            ChannelParticipantAdmin):
        return True
    return False


async def runcmd(cmd: str) -> tuple[str, str, int, int]:
    """ run command in terminal """
    args = shlex.split(cmd)
    process = await asyncio.create_subprocess_exec(*args,
                                                   stdout=asyncio.subprocess.PIPE,
                                                   stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    return (stdout.decode('utf-8', 'replace').strip(),
            stderr.decode('utf-8', 'replace').strip(),
            process.returncode,
            process.pid)


async def take_screen_shot(video_file: str, duration: int, path: str = '') -> Optional[str]:
    """ take a screenshot """
    LOGS.info(
        '[[[Extracting a frame from %s ||| Video duration => %s]]]',
        video_file,
        duration)
    ttl = duration // 2
    thumb_image_path = path or os.path.join(
        "./temp/", f"{basename(video_file)}.jpg")
    command = f"ffmpeg -ss {ttl} -i '{video_file}' -vframes 1 '{thumb_image_path}'"
    err = (await runcmd(command))[1]
    if err:
        LOGS.error(err)
    return thumb_image_path if os.path.exists(thumb_image_path) else None


async def check_media(reply_message):
    if reply_message and reply_message.media:
        if reply_message.photo:
            data = reply_message.photo
        elif reply_message.document:
            if (
                DocumentAttributeFilename(file_name="AnimatedSticker.tgs")
                in reply_message.media.document.attributes
            ):
                return False
            if (
                reply_message.gif
                or reply_message.video
                or reply_message.audio
                or reply_message.voice
            ):
                return False
            data = reply_message.media.document
        else:
            return False
    else:
        return False

    if not data or data is None:
        return False
    else:
        return data


async def run_cmd(cmd: list) -> tuple[bytes, bytes]:
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate()
    t_resp = out.strip()
    e_resp = err.strip()
    return t_resp, e_resp


def post_to_telegraph(title, html_format_content):
    post_client = TelegraphPoster(use_api=True)
    auth_name = "Man-Userbot"
    auth_url = "https://github.com/mrismanaziz/Man-Userbot"
    post_client.create_api_token(auth_name)
    post_page = post_client.post(
        title=title,
        author=auth_name,
        author_url=auth_url,
        text=html_format_content,
    )
    return post_page["url"]


async def edit_delete(event, text, time=None, parse_mode=None, link_preview=None):
    parse_mode = parse_mode or "md"
    link_preview = link_preview or False
    time = time or 5
    if event.sender_id in SUDO_USERS:
        reply_to = await event.get_reply_message()
        newevent = (
            await reply_to.reply(text, link_preview=link_preview, parse_mode=parse_mode)
            if reply_to
            else await event.reply(
                text, link_preview=link_preview, parse_mode=parse_mode
            )
        )
    else:
        newevent = await event.edit(
            text, link_preview=link_preview, parse_mode=parse_mode
        )
    await asyncio.sleep(time)
    return await newevent.delete()


async def media_to_pic(event, reply):
    mediatype = media_type(reply)
    if mediatype not in ["Photo", "Round Video", "Gif", "Sticker", "Video"]:
        await edit_delete(
            event,
            "`In the replied message. I cant extract any image to procced further reply to proper media`",
        )
        return None
    media = await reply.download_media(file="./temp")
    event = await edit_or_reply(event, f"`Transfiguration Time! Converting....`")
    file = os.path.join("./temp/", "meme.png")
    if mediatype == "Sticker":
        if media.endswith(".tgs"):
            await runcmd(
                f"lottie_convert.py --frame 0 -if lottie -of png '{media}' '{file}'"
            )
        elif media.endswith(".webp"):
            im = Image.open(media)
            im.save(file)
    elif mediatype in ["Round Video", "Video", "Gif"]:
        extractMetadata(createParser(media))
        await runcmd(f"rm -rf '{file}'")
        await take_screen_shot(media, 0, file)
        if not os.path.exists(file):
            await edit_delete(
                event, f"`Sorry. I can't extract a image from this {mediatype}`"
            )
            return None
    else:
        im = Image.open(media)
        im.save(file)
    await runcmd(f"rm -rf '{media}'")
    return [event, file, mediatype]
