from main.models import Notice

# kode import
from .funk import client, last_notice_data, send_notice, is_chat_accessible, chat_ids, last_sent_times

# add import
from asgiref.sync import sync_to_async
from asyncio import sleep
import asyncio
from datetime import datetime



async def dynamic_notice_send_task():
    async with client:
        await client.start()
        print("Client started...")

        while True:
            notices = await sync_to_async(list)(Notice.objects.all())
            for notice in notices:
                if notice.id not in last_notice_data or last_notice_data[notice.id]["descriptions"] != notice.descriptions:
                    last_notice_data[notice.id] = {
                        "descriptions": notice.descriptions,
                        "interval": notice.interval
                    }
            
            if notices:
                notice = notices[0]
                current_time = datetime.now()
                interval_seconds = notice.interval * 60  # Convert minutes to seconds
                
                # Calculate check interval: check 10 times per interval, but at least every 30 seconds
                # This ensures we check frequently enough while not wasting resources
                check_interval = min(interval_seconds / 10, 30)
                
                for chat_id in chat_ids:
                    time_since_last_sent = None
                    if last_sent_times[chat_id] is not None:
                        time_since_last_sent = (current_time - last_sent_times[chat_id]).total_seconds()
                    
                    # Send if never sent before, or if interval has passed
                    should_send = time_since_last_sent is None or time_since_last_sent >= interval_seconds
                    
                    if should_send:
                        if await is_chat_accessible(chat_id):
                            await send_notice(notice, chat_id)
                            last_sent_times[chat_id] = current_time
                            # Small delay between messages to different chats to avoid API rate limits
                            # The interval check ensures we don't send to the same chat too frequently
                            await asyncio.sleep(0.3)
                        else:
                            print(f"Cannot send to {chat_id}")
                    else:
                        # Small delay between checking different chats
                        await asyncio.sleep(0.05)
            
            # Sleep adaptively based on the check interval
            if notices:
                interval_seconds = notices[0].interval * 60
                sleep_time = min(interval_seconds / 10, 30)
            else:
                sleep_time = 30  # Default check every 30 seconds if no notices
            
            await sleep(sleep_time)

