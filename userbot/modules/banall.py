# Port By @VckyouuBitch
# From GeezProject <https://github.com/vckyou/Geez-UserBot>
# Perkontolan Dengan Hapus Credits

from asyncio import sleep

from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights

from userbot.events import register


@register(outgoing=True, pattern="^\\.banall(?: |$)(.*)")
async def testing(event):
    nikal = await event.get_chat()
    chutiya = await event.client.get_me()
    admin = nikal.admin_rights
    creator = nikal.creator
    if not admin and not creator:
        await event.edit("Anda Tidak Mempunyai Hak")
        return
    await event.edit("Tidak Melakukan Apa-apa")

    # Thank for Dark_Cobra

    everyone = await event.client.get_participants(event.chat_id)
    for user in everyone:
        if user.id == chutiya.id:
            pass
        try:
            await event.client(
                EditBannedRequest(
                    event.chat_id,
                    int(user.id),
                    ChatBannedRights(until_date=None, view_messages=True),
                )
            )
        except Exception as e:
            await event.edit(str(e))
        await sleep(0.5)
    await event.edit("Tidak Ada yang Terjadi di sini🙃🙂")
