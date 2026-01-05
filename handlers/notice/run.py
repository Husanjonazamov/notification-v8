import asyncio
from handlers.notice.funk import client
from handlers.notice.handler import dynamic_notice_send_task

async def run_client_with_task():
    async with client:
        await client.start()

        await asyncio.gather(
            dynamic_notice_send_task(),
            client.run_until_disconnected()
        )