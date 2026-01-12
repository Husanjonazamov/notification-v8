from main.models import Notice

# kode import
from .funk import client, last_notice_data, send_notice, is_chat_accessible, chat_ids, last_sent_times

# add import
from asgiref.sync import sync_to_async
from asyncio import sleep
import asyncio
from datetime import datetime



async def dynamic_notice_send_task():
    """
    Task to send notices dynamically. Client connection is managed in bot.py.
    Just checks if client is connected before sending, skips inaccessible chats silently.
    """
    while True:
        try:
            # Wait for client to be connected and authorized
            if not client.is_connected() or not await client.is_user_authorized():
                await asyncio.sleep(5)  # Wait a bit and check again
                continue
            
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
                    try:
                        # Check if client is still connected before processing
                        if not client.is_connected():
                            break  # Exit chat loop, will retry at next iteration
                        
                        time_since_last_sent = None
                        if last_sent_times[chat_id] is not None:
                            time_since_last_sent = (current_time - last_sent_times[chat_id]).total_seconds()
                        
                        # Send if never sent before, or if interval has passed
                        should_send = time_since_last_sent is None or time_since_last_sent >= interval_seconds
                        
                        if should_send:
                            # Check if chat is accessible, if not just skip silently
                            if await is_chat_accessible(chat_id):
                                # Try to send notice, if fails just continue to next chat
                                success, reason = await send_notice(notice, chat_id)
                                if success:
                                    last_sent_times[chat_id] = current_time
                                    # Small delay between messages to different chats to avoid API rate limits
                                    await asyncio.sleep(0.3)
                                else:
                                    # Log only once per failure occurrence
                                    print(f"Skipped chat {chat_id} reason={reason}")
                            # If chat is not accessible or client disconnected, just skip silently and continue
                        else:
                            # Small delay between checking different chats
                            await asyncio.sleep(0.05)
                    except Exception as e:
                        # If any error occurs for this chat, just skip and continue to next
                        # Don't let one chat's error stop the entire process
                        # Only log non-disconnection errors
                        error_msg = str(e).lower()
                        if 'disconnected' not in error_msg:
                            print(f"Error processing chat {chat_id}: {e}")
                        continue
            
            # Sleep adaptively based on the check interval
            if notices:
                interval_seconds = notices[0].interval * 60
                sleep_time = min(interval_seconds / 10, 30)
            else:
                sleep_time = 30  # Default check every 30 seconds if no notices
            
            await sleep(sleep_time)
            
        except Exception as e:
            # Catch any unexpected errors and continue
            print(f"Error in notice sending loop: {e}")
            await asyncio.sleep(5)  # Wait a bit before retrying
            continue

