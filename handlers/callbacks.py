import logging
from telethon import events
import utils

logger = logging.getLogger(__name__)

def get_action_key(data: str) -> str:
    """
    Parses the callback data payload to identify the associated help hint translation key.
    """
    if data.startswith("menu_"):
        return data.replace("menu_", "", 1)
    if data.startswith("set_lang_"):
        return "change_lang"
    if data.startswith("admin_set_"):
        return data.replace("admin_set_", "set_", 1)
        
    # Standard prefix list
    prefixes = [
        "start_bot_", "stop_bot_", "set_broadcast_", "set_welcome_",
        "toggle_spam_", "toggle_welcome_", "toggle_vc_", "toggle_tag_",
        "set_tag_msg_", "change_name_", "set_interval_", "toggle_gpt_",
        "refresh_stats_", "delete_bot_", "buy_qty_", "approve_payment_",
        "reject_payment_", "admin_"
    ]
    
    for p in prefixes:
        if data.startswith(p):
            return p.rstrip("_")
            
    return data

def register_handlers(client):
    @client.on(events.CallbackQuery)
    async def global_callback_help_handler(event):
        """
        Intercepts all callback queries, identifies their actions, and displays help messages.
        """
        try:
            # Decode callback data
            data = event.data.decode("utf-8") if isinstance(event.data, bytes) else event.data
            if not data:
                return
                
            # Run Guard check (exception: 'verify_sub' must pass through)
            if data != "verify_sub":
                if await utils.guard(event, client):
                    raise events.StopPropagation
                    
            action = get_action_key(data)
            user_id = event.sender_id
            
            # Show the translation help text popup
            await utils.show_help(event, action, user_id)
        except events.StopPropagation:
            raise
        except Exception as e:
            logger.error(f"Error in global callback help handler: {e}")
            # Do not raise events.StopPropagation so other matching callback handlers can still fire.
