from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.errors.rpcerrorlist import ChatWriteForbiddenError, ChannelPrivateError, UserBannedInChannelError
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
    """
    Check if chat is accessible. Returns False if chat is not accessible or client is disconnected.
    """
    try:
        # Check if client is connected
        if not client.is_connected():
            return False
        
        # Try to get entity to check accessibility
        await client.get_entity(chat_id)
        return True
    except (ChannelPrivateError, ChatWriteForbiddenError, UserBannedInChannelError, ValueError) as e:
        # These are expected errors for inaccessible chats - just skip silently
        return False
    except Exception as e:
        error_msg = str(e).lower()
        # If client is disconnected, just skip
        if 'disconnected' in error_msg or 'not connected' in error_msg:
            return False
        # For other errors, log but still return False to skip
        print(f"Chat {chat_id} is not accessible: {e}")
        try:
            with open("error_log.txt", "a") as log_file:
                log_file.write(f"{datetime.now().isoformat()} - Chat {chat_id} is not accessible. Error: {e}\n")
        except:
            pass
        return False



async def send_notice(notice, chat_id):
    """
    Send a notice to a chat with proper error handling and rate limit compliance.
    Returns True if sent successfully, False otherwise.
    """
    # Check if client is connected before attempting to send
    if not client.is_connected():
        return False
    
    formatted_description = f"{notice.descriptions}"
    max_retries = 2
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            await client.send_message(chat_id, formatted_description, parse_mode='Markdown')
            return True  # Successfully sent
        except FloodWaitError as e:
            # Telegram is asking us to wait - we must respect this
            wait_time = e.seconds
            print(f"Flood wait error for chat {chat_id}: need to wait {wait_time} seconds")
            await asyncio.sleep(wait_time)
            # Retry after waiting (don't increment retry_count as this is expected behavior)
            continue
        except (ChannelPrivateError, ChatWriteForbiddenError, UserBannedInChannelError, ValueError) as e:
            # These are expected errors - chat is not accessible, just skip
            return False
        except Exception as e:
            error_msg = str(e).lower()
            
            # If client is disconnected, just skip this chat
            if 'disconnected' in error_msg or 'not connected' in error_msg:
                return False
            
            # For other errors, try retrying once
            retry_count += 1
            if retry_count < max_retries:
                # Wait a bit before retry
                await asyncio.sleep(1)
                continue
            else:
                # Failed after retries - just skip this chat
                try:
                    with open("error_log.txt", "a") as log_file:
                        log_file.write(f"{datetime.now().isoformat()} - Chat ID: {chat_id} - Error: {e}\n")
                except:
                    pass
                return False
    
    return False  # Failed to send after all retries

