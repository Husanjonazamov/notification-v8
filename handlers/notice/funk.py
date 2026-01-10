from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from utils import env
from services.services import getNotice
from asgiref.sync import sync_to_async
from main.models import Notice
from datetime import datetime
import asyncio
import re


client = TelegramClient('qr_session', env.API_ID, env.API_HASH)

last_notice_data = {}

    
chat_ids = [
    -1001950144985, -1001661240991, -1001696066827, -1001368447491,
    -1001623332436, -1001934813270, -1001698342886, -1001969097223,
    -1002308491767, -1001900254910, -1002232778089, -1001830606441,
    -1002161701360, -1002530161567, -1002068631562, -1002678070583,
    -1002247652778, -1002347020143, -1002143883661, -1002172394330,
    -1001799869165, -1002385271069, -1002469632510, -1001698975338,
    -1002083400408, -1002089458891, -1002230508278, -1001889067613,
    -1002341287738, -1002225373901, -1002206635995, -1002169615850,
    -1002202717276, -1002232013574, -1002406606261, -1002387686287,
    -1002211977483, -1002067577089, -1001927709760, -1002318451740,
    -1001561634319, -1002237859063, -1001869944953, -1001768202236,
    -1002219596565, -1001932433103, -1002298605058, -1002114024623,
    -1002483533745, -1001276254263, -1002178966866, -1002215121340,
    -1002355702294, -1002297602082, -1002228677318, -1002291327774,
    -1002285384904, -1002225184030, -1002385819649, -1002220553035,
    -1001570432014, -1002379133637, -1002474360096, -1001790205450,
    -1002372123702, -1002001875045, -1002143591933, -1002376541471,
    -1002357488084, -1002299313513, -1002360266775, -1002301648032,
    -1002220623140, -1001503290336, -1001689353727, -1002091350845,
    -1002459403501, -1002248065061, -1001945152898,
    -1001801467376, -1002141143999, -1002159005012, -1002164491449,
    -1002357301670, -1002176213545, -1002345459660, -1001661001936,
    -1002085064659, -1002192007005, -1002247208452, -1002433091888,
    -1001995597670, -1002375234737, -1001502734345, -1002133733161,
    -1002367286161
]



message_counters = {chat_id: 0 for chat_id in chat_ids}
last_sents = {chat_id: False for chat_id in chat_ids}

last_sent_times = {chat_id: None for chat_id in chat_ids}

async def is_chat_accessible(chat_id):
    try:
        await client.get_entity(chat_id)
        return True
    except Exception as e:
        print(f"Chat {chat_id} is not accessible: {e}")
        with open("error_log.txt", "a") as log_file:
            log_file.write(f"Chat {chat_id} is not accessible. Error: {e}\n")
        return False



async def send_notice(notice, chat_id):
    """
    Send a notice to a chat with proper error handling and rate limit compliance.
    """
    formatted_description = f"{notice.descriptions}"
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            await client.send_message(chat_id, formatted_description, parse_mode='Markdown')
            return  # Successfully sent
        except FloodWaitError as e:
            # Telegram is asking us to wait - we must respect this
            wait_time = e.seconds
            print(f"Flood wait error for chat {chat_id}: need to wait {wait_time} seconds")
            await asyncio.sleep(wait_time)
            # Retry after waiting (don't increment retry_count as this is expected behavior)
            continue
        except Exception as e:
            retry_count += 1
            error_msg = str(e)
            print(f"Error sending message to {chat_id} (attempt {retry_count}/{max_retries}): {error_msg}")
            
            # Log the error
            try:
                with open("error_log.txt", "a") as log_file:
                    log_file.write(f"{datetime.now().isoformat()} - Chat ID: {chat_id} - Error: {error_msg}\n")
            except Exception as log_error:
                print(f"Failed to write to error log: {log_error}")
            
            # If it's a retryable error and we haven't exceeded max retries, wait and retry
            if retry_count < max_retries and "wait" in error_msg.lower():
                # Extract wait time from error message if possible, otherwise wait 5 seconds
                wait_time = 5
                if "wait of" in error_msg and "seconds" in error_msg:
                    try:
                        # Try to extract the number
                        match = re.search(r'wait of (\d+) seconds', error_msg)
                        if match:
                            wait_time = int(match.group(1))
                    except:
                        pass
                await asyncio.sleep(wait_time)
            else:
                # Give up after max retries or non-retryable error
                break

