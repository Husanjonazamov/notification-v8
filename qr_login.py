#!/usr/bin/env python3
"""
QR Code Login Script for Telethon
This script generates a QR code for Telegram authentication using Telethon.
Scan the QR code with your Telegram app to authenticate and get session details.
"""

import asyncio
import sys
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import qrcode

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.env import API_ID, API_HASH


async def generate_and_display_qr(client, session_name):
    """
    Generate and display QR code for login
    Returns the QRLogin object
    """
    print("Generating QR code...")
    qr_login_result = await client.qr_login()
    
    # Get the URL from the QR login result
    qr_url = qr_login_result.url if hasattr(qr_login_result, 'url') else str(qr_login_result)
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to file
    qr_filename = f"{session_name}_qr_code.png"
    img.save(qr_filename)
    print(f"\n✓ QR code saved to: {qr_filename}")
    print(f"\nPlease scan this QR code with your Telegram app:")
    print(f"  1. Open Telegram on your phone")
    print(f"  2. Go to Settings > Devices > Link Desktop Device")
    print(f"     (or Settings > Privacy and Security > Active Sessions)")
    print(f"  3. Tap 'Link Desktop Device' and scan the QR code")
    print(f"\n⚠ Note: QR codes expire after a few minutes. If expired, a new one will be generated.")
    print(f"QR Code URL: {qr_url}\n")
    
    print("QR Code (ASCII):")
    print("-" * 50)
    qr.print_ascii(invert=True)
    print("-" * 50)
    print(f"\nOr open the image file: {qr_filename}")
    print("-" * 50)
    
    return qr_login_result, qr_filename


async def qr_login(session_name='qr_session'):
    """
    Authenticate using QR code login with retry support
    """
    print(f"Creating Telethon client with session: {session_name}")
    client = TelegramClient(session_name, API_ID, API_HASH)
    
    try:
        await client.connect()
        
        # Check if already authorized
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"\n✓ Already authorized as: {me.first_name}")
            if me.username:
                print(f"  Username: @{me.username}")
            print(f"Session file: {session_name}.session")
            print(f"\nSession details:")
            print(f"  - Phone: {me.phone}")
            print(f"  - User ID: {me.id}")
            if me.username:
                print(f"  - Username: @{me.username}")
            print(f"  - First Name: {me.first_name}")
            if me.last_name:
                print(f"  - Last Name: {me.last_name}")
            
            await client.disconnect()
            return True
        
        print("\nNot authorized. Starting QR code login...")
        
        max_retries = 5
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            if attempt > 1:
                print(f"\n{'='*60}")
                print(f"Attempt {attempt} of {max_retries}")
                print(f"{'='*60}\n")
            
            # Generate QR code
            qr_login_result, qr_filename = await generate_and_display_qr(client, session_name)
            print(f"\n⏳ Waiting for you to scan the QR code... (Attempt {attempt}/{max_retries})")
            print("   - QR codes expire after ~60 seconds")
            print("   - If expired, a new QR code will be generated automatically")
            print("   - Press Ctrl+C to cancel\n")
            
            # Wait for authentication
            try:
                # Wait for the QR code to be scanned
                # The wait() method waits for authentication or until the QR code expires (~60 seconds)
                # If timeout occurs, we'll catch it and generate a new QR code
                await qr_login_result.wait()
                print("\n✓ Authentication successful!")
                
                # Get user info
                me = await client.get_me()
                print(f"\n" + "=" * 60)
                print("SESSION DETAILS:")
                print("=" * 60)
                print(f"  Phone: {me.phone}")
                print(f"  User ID: {me.id}")
                if me.username:
                    print(f"  Username: @{me.username}")
                print(f"  First Name: {me.first_name}")
                if me.last_name:
                    print(f"  Last Name: {me.last_name}")
                print(f"\n✓ Session file saved: {session_name}.session")
                print(f"✓ You can now use this session file with Telethon!")
                print("=" * 60)
                
                await client.disconnect()
                return True
                
            except (asyncio.TimeoutError, TimeoutError) as e:
                print(f"\n⚠ QR code expired (timeout after ~60 seconds).")
                print(f"   Generating a new QR code...")
                # Continue to next iteration to generate new QR code
                await asyncio.sleep(1)
                continue
                
            except asyncio.CancelledError:
                print(f"\n⚠ QR code wait was cancelled. Generating a new QR code...")
                # Continue to next iteration to generate new QR code
                await asyncio.sleep(1)
                continue
                
            except SessionPasswordNeededError:
                print("\n⚠ Two-factor authentication is enabled.")
                password = input("Please enter your 2FA password: ")
                await client.sign_in(password=password)
                print("✓ Authentication successful with 2FA!")
                
                me = await client.get_me()
                print(f"\n" + "=" * 60)
                print("SESSION DETAILS:")
                print("=" * 60)
                print(f"  Phone: {me.phone}")
                print(f"  User ID: {me.id}")
                if me.username:
                    print(f"  Username: @{me.username}")
                print(f"  First Name: {me.first_name}")
                if me.last_name:
                    print(f"  Last Name: {me.last_name}")
                print(f"\n✓ Session file saved: {session_name}.session")
                print("=" * 60)
                
                await client.disconnect()
                return True
                
            except Exception as e:
                error_msg = str(e).lower()
                error_type = type(e).__name__
                
                # Check if it's a timeout-related error
                if 'timeout' in error_msg or 'expired' in error_msg or 'TimeoutError' in error_type:
                    print(f"\n⚠ QR code expired or timed out. Generating a new one...")
                    await asyncio.sleep(1)
                    continue
                else:
                    print(f"\n✗ Error during authentication: {e}")
                    print(f"   Error type: {error_type}")
                    raise
        
        # If we exhausted all retries
        print(f"\n✗ Failed to authenticate after {max_retries} attempts.")
        print("   Please try running the script again.")
        await client.disconnect()
        return False
        
    except Exception as e:
        print(f"\n✗ Error during authentication: {e}")
        import traceback
        traceback.print_exc()
        await client.disconnect()
        raise


async def main():
    """
    Main function
    """
    print("=" * 60)
    print("Telethon QR Code Login")
    print("=" * 60)
    
    # Get session name from command line or use default
    session_name = sys.argv[1] if len(sys.argv) > 1 else 'qr_session'
    
    try:
        await qr_login(session_name)
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
