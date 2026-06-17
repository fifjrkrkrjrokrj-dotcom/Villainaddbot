import json
import os
import logging
import time
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
import config

logger = logging.getLogger(__name__)

# Global database variables
_mongo_client: Optional[MongoClient] = None
_db = None
_use_mongodb = False

# Local JSON file paths
JSON_FILES = {
    "users": "db_users.json",
    "sessions": "db_sessions.json",
    "payments": "db_payments.json",
    "settings": "db_settings.json",
    "force_channels": "db_force_channels.json",
    "coupons": "db_coupons.json",
    "coupon_usage": "db_coupon_usage.json"
}

def db_init():
    """
    Initializes the database connection.
    Attempts to connect to MongoDB, falling back to local JSON files if connection fails or isn't set.
    """
    global _mongo_client, _db, _use_mongodb
    if config.MONGODB_URI:
        try:
            logger.info("Connecting to MongoDB...")
            _mongo_client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=3000)
            # Force connection check
            _mongo_client.server_info()
            _db = _mongo_client.get_database()
            _use_mongodb = True
            logger.info("Successfully connected to MongoDB.")
            return
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}. Falling back to local JSON files.")
    else:
        logger.info("MongoDB URI not provided. Falling back to local JSON files.")
    
    _use_mongodb = False
    # Initialize JSON files if they do not exist
    for table, path in JSON_FILES.items():
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                if table == "settings":
                    # settings starts with a list containing default config
                    default_sett = dict(config.DEFAULT_GLOBAL_SETTINGS)
                    default_sett["id"] = "global"
                    json.dump([default_sett], f, indent=4)
                else:
                    json.dump([], f, indent=4)

# Helper functions for local JSON manipulation
def _read_json(table: str) -> List[Dict[str, Any]]:
    path = JSON_FILES[table]
    try:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading JSON file {path}: {e}")
        return []

def _write_json(table: str, data: List[Dict[str, Any]]):
    path = JSON_FILES[table]
    try:
        serialized = json.dumps(data, indent=4)
        with open(path, "w", encoding="utf-8") as f:
            f.write(serialized)
    except Exception as e:
        logger.error(f"Error writing JSON file {path}: {e}")

# ==================== User CRUD Operations ====================
def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    if _use_mongodb:
        return _db.users.find_one({"user_id": user_id})
    else:
        users = _read_json("users")
        for u in users:
            if u["user_id"] == user_id:
                return u
        return None

def save_user(user_data: Dict[str, Any]):
    if _use_mongodb:
        _db.users.replace_one({"user_id": user_data["user_id"]}, user_data, upsert=True)
    else:
        users = _read_json("users")
        updated = False
        for i, u in enumerate(users):
            if u["user_id"] == user_data["user_id"]:
                users[i] = user_data
                updated = True
                break
        if not updated:
            users.append(user_data)
        _write_json("users", users)

# ==================== Session CRUD Operations ====================
def get_sessions(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if _use_mongodb:
        query = {"user_id": user_id} if user_id is not None else {}
        return list(_db.sessions.find(query))
    else:
        sessions = _read_json("sessions")
        if user_id is not None:
            return [s for s in sessions if s["user_id"] == user_id]
        return sessions

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    if _use_mongodb:
        return _db.sessions.find_one({"session_id": session_id})
    else:
        sessions = _read_json("sessions")
        for s in sessions:
            if s["session_id"] == session_id:
                return s
        return None

def save_session(session_data: Dict[str, Any]):
    if _use_mongodb:
        _db.sessions.replace_one({"session_id": session_data["session_id"]}, session_data, upsert=True)
    else:
        sessions = _read_json("sessions")
        updated = False
        for i, s in enumerate(sessions):
            if s["session_id"] == session_data["session_id"]:
                sessions[i] = session_data
                updated = True
                break
        if not updated:
            sessions.append(session_data)
        _write_json("sessions", sessions)

def delete_session(session_id: str):
    if _use_mongodb:
        _db.sessions.delete_one({"session_id": session_id})
    else:
        sessions = _read_json("sessions")
        sessions = [s for s in sessions if s["session_id"] != session_id]
        _write_json("sessions", sessions)

# ==================== Payment CRUD Operations ====================
def get_payment_requests(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if _use_mongodb:
        query = {"user_id": user_id} if user_id is not None else {}
        return list(_db.payments.find(query))
    else:
        payments = _read_json("payments")
        if user_id is not None:
            return [p for p in payments if p["user_id"] == user_id]
        return payments

def get_payment_request(payment_id: str) -> Optional[Dict[str, Any]]:
    if _use_mongodb:
        return _db.payments.find_one({"payment_id": payment_id})
    else:
        payments = _read_json("payments")
        for p in payments:
            if p["payment_id"] == payment_id:
                return p
        return None

def save_payment_request(payment_data: Dict[str, Any]):
    if _use_mongodb:
        _db.payments.replace_one({"payment_id": payment_data["payment_id"]}, payment_data, upsert=True)
    else:
        payments = _read_json("payments")
        updated = False
        for i, p in enumerate(payments):
            if p["payment_id"] == payment_data["payment_id"]:
                payments[i] = payment_data
                updated = True
                break
        if not updated:
            payments.append(payment_data)
        _write_json("payments", payments)

# ==================== Settings CRUD Operations ====================
def get_global_settings() -> Dict[str, Any]:
    if _use_mongodb:
        settings = _db.settings.find_one({"id": "global"})
        if not settings:
            settings = dict(config.DEFAULT_GLOBAL_SETTINGS)
            settings["id"] = "global"
            _db.settings.insert_one(settings)
        return settings
    else:
        settings_list = _read_json("settings")
        if not settings_list:
            settings = dict(config.DEFAULT_GLOBAL_SETTINGS)
            settings["id"] = "global"
            _write_json("settings", [settings])
            return settings
        return settings_list[0]

def save_global_settings(settings_data: Dict[str, Any]):
    if _use_mongodb:
        _db.settings.replace_one({"id": "global"}, settings_data, upsert=True)
    else:
        # Since local settings is a single item list, replace list contents
        settings_data["id"] = "global"
        _write_json("settings", [settings_data])

# ==================== Force Channels CRUD ====================
def get_force_channels() -> List[Dict[str, Any]]:
    if _use_mongodb:
        return list(_db.force_channels.find({}))
    else:
        return _read_json("force_channels")

def add_force_channel(channel_id: str, invite_link: str, channel_name: str):
    data = {
        "channel_id": channel_id,
        "channel_link": invite_link,
        "channel_name": channel_name
    }
    if _use_mongodb:
        _db.force_channels.replace_one({"channel_id": channel_id}, data, upsert=True)
    else:
        channels = _read_json("force_channels")
        updated = False
        for i, ch in enumerate(channels):
            if ch["channel_id"] == channel_id:
                channels[i] = data
                updated = True
                break
        if not updated:
            channels.append(data)
        _write_json("force_channels", channels)

def delete_force_channel(channel_id: str):
    if _use_mongodb:
        _db.force_channels.delete_one({"channel_id": channel_id})
    else:
        channels = _read_json("force_channels")
        channels = [ch for ch in channels if ch["channel_id"] != channel_id]
        _write_json("force_channels", channels)

# ==================== Coupons CRUD ====================
def get_coupons() -> List[Dict[str, Any]]:
    if _use_mongodb:
        return list(_db.coupons.find({}))
    else:
        return _read_json("coupons")

def get_coupon(code: str) -> Optional[Dict[str, Any]]:
    if _use_mongodb:
        return _db.coupons.find_one({"code": code})
    else:
        coupons = _read_json("coupons")
        for c in coupons:
            if c["code"] == code:
                return c
        return None

def save_coupon(coupon_data: Dict[str, Any]):
    if _use_mongodb:
        _db.coupons.replace_one({"code": coupon_data["code"]}, coupon_data, upsert=True)
    else:
        coupons = _read_json("coupons")
        updated = False
        for i, c in enumerate(coupons):
            if c["code"] == coupon_data["code"]:
                coupons[i] = coupon_data
                updated = True
                break
        if not updated:
            coupons.append(coupon_data)
        _write_json("coupons", coupons)

def delete_coupon(code: str):
    if _use_mongodb:
        _db.coupons.delete_one({"code": code})
    else:
        coupons = _read_json("coupons")
        coupons = [c for c in coupons if c["code"] != code]
        _write_json("coupons", coupons)

# ==================== Coupon Usage CRUD ====================
def has_used_coupon(code: str, user_id: int) -> bool:
    if _use_mongodb:
        return _db.coupon_usage.find_one({"code": code, "user_id": user_id}) is not None
    else:
        usage = _read_json("coupon_usage")
        for u in usage:
            if u["code"] == code and u["user_id"] == user_id:
                return True
        return False

def save_coupon_usage(code: str, user_id: int):
    data = {
        "code": code,
        "user_id": user_id,
        "timestamp": time.time()
    }
    if _use_mongodb:
        _db.coupon_usage.insert_one(data)
    else:
        usage = _read_json("coupon_usage")
        usage.append(data)
        _write_json("coupon_usage", usage)
