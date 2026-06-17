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
