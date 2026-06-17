import logging
from telethon import events
import database
import utils

logger = logging.getLogger(__name__)

async def render_status_dashboard(event, user_id: int):
    """
    Renders the Status Dashboard summarizing statistics for all bots owned by this user.
    """
    user = database.get_user(user_id)
    lang = user.get("language", "en") if user else "en"
    
    sessions = database.get_sessions(user_id)
    
    total_sessions = len(sessions)
    total_groups = sum(s.get("stats", {}).get("group_count", 0) for s in sessions)
    total_users = sum(s.get("stats", {}).get("user_count", 0) for s in sessions)
    total_broadcasts = sum(s.get("stats", {}).get("broadcast_count", 0) for s in sessions)
    total_welcomed = sum(len(s.get("stats", {}).get("welcomed_users", [])) for s in sessions)
    
    # Text formatting using HTML/Markdown style blockquotes and bold
    text = (
        f"📊 **System Status Dashboard**\n\n"
        f"📱 Total Connected Bots: **{total_sessions}**\n"
        f"👥 Managed Groups: **{total_groups}**\n"
        f"👤 Contacts/Users: **{total_users}**\n"
        f"✉️ Broadcast Runs Completed: **{total_broadcasts}**\n"
        f"👋 Welcomed New Users: **{total_welcomed}**\n"
    )
    
    buttons = [[utils.styled_button(utils.get_text("back_to_menu", lang), "menu_start", style="primary")]]
    
    global_settings = database.get_global_settings()
    ping_image = global_settings.get("ping_image")
    
    try:
        if ping_image:
            await event.respond(text, file=ping_image, buttons=buttons)
        else:
            await event.respond(text, buttons=buttons)
    except Exception as e:
        logger.error(f"Error rendering status screen: {e}")
        await event.respond(text, buttons=buttons)

def register_handlers(client):
    
    @client.on(events.NewMessage(pattern="/status"))
    async def status_command(event):
        if not event.is_private:
            return
        # Verify onboarding
        from handlers.start import check_onboarding
        onboarded = await check_onboarding(client, event)
        if onboarded:
            await render_status_dashboard(event, event.sender_id)

    @client.on(events.CallbackQuery(pattern="^menu_status$"))
    async def status_callback(event):
        await render_status_dashboard(event, event.sender_id)
