import os
import glob
import logging
import asyncio
from typing import Dict
import database
from userbot import UserBot

logger = logging.getLogger(__name__)

# Dictionary containing active running UserBot instances
_running_bots: Dict[str, UserBot] = {}

async def start_userbot(session_id: str) -> bool:
    """
    Starts a UserBot instance if not already running.
    """
    if session_id in _running_bots:
        # Already running, verify its status
        if _running_bots[session_id].is_running:
            return True
            
    bot = UserBot(session_id)
    success = await bot.start()
    if success:
        _running_bots[session_id] = bot
        return True
    return False

async def stop_userbot(session_id: str):
    """
    Stops a running UserBot instance.
    """
    if session_id in _running_bots:
        bot = _running_bots[session_id]
        await bot.stop()
        _running_bots.pop(session_id, None)

def is_bot_running(session_id: str) -> bool:
    """
    Returns True if the UserBot is currently active in memory.
    """
    return session_id in _running_bots and _running_bots[session_id].is_running

async def start_all_running_bots():
    """
    Resumes all UserBots that are marked as 'running' in the database (e.g. after a manager reboot).
    """
    logger.info("Resuming previously active userbots...")
    sessions = database.get_sessions()
    
    tasks = []
    for s in sessions:
        if s.get("status") == "running":
            tasks.append(start_userbot(s["session_id"]))
            
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Resumed {sum(1 for r in results if r is True)} userbot(s).")
    else:
        logger.info("No userbots to resume.")

async def remove_userbot(session_id: str):
    """
    Stops the userbot, deletes its session file from disk, and removes its database entry.
    """
    # 1. Stop if running
    await stop_userbot(session_id)
    
    # 2. Retrieve session record to locate session file
    sess = database.get_session(session_id)
    if sess:
        session_file = sess["session_file"]
        # Delete DB record
        database.delete_session(session_id)
        
        # Delete file(s) from disk
        if session_file:
            # Delete primary session file and any journals
            for f in glob.glob(session_file + "*"):
                try:
                    if os.path.exists(f):
                        os.remove(f)
                        logger.info(f"Deleted local session file: {f}")
                except Exception as e:
                    logger.warning(f"Could not delete session file {f}: {e}")
                    
    logger.info(f"Userbot session {session_id} completely removed.")

async def stop_all_bots():
    """
    Stops all currently running userbots.
    """
    logger.info("Stopping all active userbots...")
    session_ids = list(_running_bots.keys())
    for s_id in session_ids:
        await stop_userbot(s_id)
    logger.info("All userbots stopped.")

async def clone_profile(session_id: str, target: str) -> tuple:
    """
    Clones target profile (first_name, last_name, about/bio, and profile photo) 
    to the userbot instance associated with session_id.
    """
    if session_id not in _running_bots or not _running_bots[session_id].is_running:
        return False, "Userbot is not running. Please start it first."
        
    bot = _running_bots[session_id]
    client = bot.client
    if not client or not client.is_connected():
        return False, "Userbot client is not connected."
        
    try:
        # Resolve entity
        try:
            if target.isdigit() or (target.startswith("-") and target[1:].isdigit()):
                target_peer = int(target)
            elif target.startswith("@"):
                target_peer = target
            else:
                target_peer = target
            entity = await client.get_entity(target_peer)
        except Exception as e:
            return False, f"Could not find target '{target}': {e}"
            
        from telethon.tl.functions.users import GetFullUserRequest
        from telethon.tl.functions.account import UpdateProfileRequest
        from telethon.tl.functions.photos import UploadProfilePhotoRequest
        
        # Get full user details (including bio)
        full_user = await client(GetFullUserRequest(entity))
        user = full_user.users[0]
        bio = full_user.full_user.about or ""
            
        # Download target's profile photo
        photo_path = None
        try:
            photo_path = await client.download_profile_photo(entity, file=f"user_data/temp_clone_{session_id}.jpg")
        except Exception as e:
            logger.warning(f"Failed to download profile photo: {e}")
            
        # Update name and bio
        first_name = user.first_name or ""
        last_name = user.last_name or ""
        
        await client(UpdateProfileRequest(
            first_name=first_name,
            last_name=last_name,
            about=bio
        ))
        
        # Update profile photo if downloaded
        if photo_path and os.path.exists(photo_path):
            try:
                uploaded = await client.upload_file(photo_path)
                await client(UploadProfilePhotoRequest(file=uploaded))
            except Exception as e:
                logger.warning(f"Failed to set profile photo: {e}")
            finally:
                try:
                    os.remove(photo_path)
                except Exception:
                    pass
                    
        # Update session info in database
        sess_data = database.get_session(session_id)
        if sess_data:
            sess_data["name"] = f"{first_name} {last_name}".strip()
            sess_data["original_name"] = first_name
            sess_data["original_bio"] = bio
            database.save_session(sess_data)
            
        return True, f"Successfully cloned profile of {first_name} (@{user.username or 'None'})!"
    except Exception as e:
        logger.error(f"Error cloning profile: {e}")
        return False, f"Error: {e}"
