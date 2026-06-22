import motor.motor_asyncio
from config import DB_URI, DB_NAME
from datetime import datetime

class SidDataBase:

    def __init__(self, DB_URI, DB_NAME):
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
        self.database = self.dbclient[DB_NAME]
        
        self.user_data = self.database['users']
        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.banned_user_data = self.database['banned_user']
        self.autho_user_data = self.database['autho_user']
        
        self.auto_delete_data = self.database['auto_delete']
        self.hide_caption_data = self.database['hide_caption']
        self.protect_content_data = self.database['protect_content']
        self.channel_button_data = self.database['channel_button']
        
        self.del_timer_data = self.database['del_timer']
        self.channel_button_link_data = self.database['channelButton_link']

        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.store_reqLink_data = self.database['store_reqLink']
        self.group_data = self.database['groups']
        self.settings = self.database['settings']
        self.channels_col = self.database['saved_channels']
        self.indexed_channels_data = self.database['indexed_channels']
        self.user_states = self.database['user_states']  # ✅ ADDED

    # CHANNEL BUTTON SETTINGS
    async def set_channel_button_link(self, button_name: str, button_link: str):
        await self.channel_button_link_data.delete_many({})
        await self.channel_button_link_data.insert_one({'button_name': button_name, 'button_link': button_link})
    
    async def get_channel_button_link(self):
        data = await self.channel_button_link_data.find_one({})
        if data:
            return data.get('button_name'), data.get('button_link')
        return 'Join Channel', 'https://t.me/btth480p'
    
    # DELETE TIMER SETTINGS
    async def set_del_timer(self, value: int):        
        existing = await self.del_timer_data.find_one({})
        if existing:
            await self.del_timer_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.del_timer_data.insert_one({'value': value})
    
    async def get_del_timer(self):
        data = await self.del_timer_data.find_one({})
        if data:
            return data.get('value', 600)
        return 600
    
    # SET BOOLEAN VALUES
    async def set_auto_delete(self, value: bool):
        existing = await self.auto_delete_data.find_one({})
        if existing:
            await self.auto_delete_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.auto_delete_data.insert_one({'value': value})
    
    async def set_hide_caption(self, value: bool):
        existing = await self.hide_caption_data.find_one({})
        if existing:
            await self.hide_caption_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.hide_caption_data.insert_one({'value': value})
    
    async def set_protect_content(self, value: bool):
        existing = await self.protect_content_data.find_one({})
        if existing:
            await self.protect_content_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.protect_content_data.insert_one({'value': value})
    
    async def set_channel_button(self, value: bool):
        existing = await self.channel_button_data.find_one({})
        if existing:
            await self.channel_button_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.channel_button_data.insert_one({'value': value})
    
    async def set_request_forcesub(self, value: bool):
        existing = await self.rqst_fsub_data.find_one({})
        if existing:
            await self.rqst_fsub_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.rqst_fsub_data.insert_one({'value': value})

    # GET BOOLEAN VALUES
    async def get_auto_delete(self):
        data = await self.auto_delete_data.find_one({})
        if data:
            return data.get('value', False)
        return False
    
    async def get_hide_caption(self):
        data = await self.hide_caption_data.find_one({})
        if data:
            return data.get('value', False)
        return False
    
    async def get_protect_content(self):
        data = await self.protect_content_data.find_one({})
        if data:
            return data.get('value', False)
        return False
    
    async def get_channel_button(self):
        data = await self.channel_button_data.find_one({})
        if data:
            return data.get('value', False)
        return False
    
    async def get_request_forcesub(self):
        data = await self.rqst_fsub_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    # USER MANAGEMENT
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)
    
    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id})
        return
    
    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        user_ids = []
        for doc in user_docs:
            user_ids.append(doc['_id'])
        return user_ids
    
    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})
        return
    
    # CHANNEL MANAGEMENT
    async def channel_exist(self, channel_id: int):
        found = await self.channel_data.find_one({'_id': channel_id})
        return bool(found)
        
    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.channel_data.insert_one({'_id': channel_id})
            return
    
    async def del_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.channel_data.delete_one({'_id': channel_id})
            return
    
    async def get_all_channels(self):
        channel_docs = await self.channel_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids
    
    # ADMIN MANAGEMENT
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)
        
    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})
            return
    
    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})
            return
    
    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids
    
    # BAN USER MANAGEMENT
    async def ban_user_exist(self, user_id: int):
        found = await self.banned_user_data.find_one({'_id': user_id})
        return bool(found)
        
    async def add_ban_user(self, user_id: int):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id})
            return
    
    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})
            return
    
    async def get_ban_users(self):
        users_docs = await self.banned_user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids
    
    # REQUEST FORCE-SUB MANAGEMENT
    async def add_reqChannel(self, channel_id: int):
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$setOnInsert': {'user_ids': []}},
            upsert=True
        )

    async def reqSent_user(self, channel_id: int, user_id: int):
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$addToSet': {'user_ids': user_id}}, 
            upsert=True
        )

    async def del_reqSent_user(self, channel_id: int, user_id: int):
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$pull': {'user_ids': user_id}}
        )
        
    async def clear_reqSent_user(self, channel_id: int):
        if await self.reqChannel_exist(channel_id):
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': channel_id}, 
                {'$set': {'user_ids': []}}
            )

    async def reqSent_user_exist(self, channel_id: int, user_id: int):
        found = await self.rqst_fsub_Channel_data.find_one(
            {'_id': channel_id, 'user_ids': user_id}
        )
        return bool(found)

    async def del_reqChannel(self, channel_id: int):
        await self.rqst_fsub_Channel_data.delete_one({'_id': channel_id})

    async def reqChannel_exist(self, channel_id: int):
        found = await self.rqst_fsub_Channel_data.find_one({'_id': channel_id})
        return bool(found)

    async def get_reqSent_user(self, channel_id: int):
        data = await self.rqst_fsub_Channel_data.find_one({'_id': channel_id})
        if data:
            return data.get('user_ids', [])
        return []

    async def get_reqChannel(self):
        channel_docs = await self.rqst_fsub_Channel_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    async def get_reqLink_channels(self):
        channel_docs = await self.store_reqLink_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    async def get_stored_reqLink(self, channel_id: int):
        data = await self.store_reqLink_data.find_one({'_id': channel_id})
        if data:
            return data.get('link')
        return None

    async def store_reqLink(self, channel_id: int, link: str):
        await self.store_reqLink_data.update_one(
            {'_id': channel_id}, 
            {'$set': {'link': link}}, 
            upsert=True
        )

    async def del_stored_reqLink(self, channel_id: int):
        await self.store_reqLink_data.delete_one({'_id': channel_id})

    # GROUP SYSTEM
    async def approve_group(self, chat_id: int):
        await self.group_data.update_one(
            {"_id": chat_id},
            {"$set": {"approved": True}},
            upsert=True
        )

    async def disapprove_group(self, chat_id: int):
        await self.group_data.update_one(
            {"_id": chat_id},
            {"$set": {"approved": False}},
            upsert=True
        )

    async def is_group_approved(self, chat_id: int):
        data = await self.group_data.find_one({"_id": chat_id})
        if not data:
            await self.group_data.insert_one({
                "_id": chat_id,
                "approved": False,
                "search_mode": "auto"
            })
            return False
        return data.get("approved", False)

    # SEARCH MODE
    async def set_search_mode(self, chat_id: int, mode: str):
        await self.group_data.update_one(
            {"_id": chat_id},
            {"$set": {"search_mode": mode}},
            upsert=True
        )

    async def get_search_mode(self, chat_id: int):
        data = await self.group_data.find_one({"_id": chat_id})
        if not data:
            await self.group_data.insert_one({
                "_id": chat_id,
                "approved": False,
                "search_mode": "auto"
            })
            return "auto"
        return data.get("search_mode", "auto")

    # CHANNEL SYSTEM
    async def update_channel(self, channel_id: int, data: dict):
        if "expire" in data:
            data["expire_seconds"] = data.pop("expire")
        await self.indexed_channels_data.update_one(
            {"_id": channel_id},
            {"$set": data},
            upsert=True
        )

    async def get_channel(self, channel_id: int):
        return await self.indexed_channels_data.find_one({"_id": channel_id})

    async def get_indexed_channels(self):
        return await self.indexed_channels_data.find(
            {"is_indexed": True}
        ).to_list(length=None)

    async def search_channel(self, keyword: str):
        regex = {"$regex": keyword, "$options": "i"}
        return await self.indexed_channels_data.find({
            "is_indexed": True,
            "$or": [
                {"title": regex},
                {"username": regex}
            ]
        }).to_list(length=None)

    # INDEXING SYSTEM
    async def add_or_update_channel(self, channel_id: int, title: str, username: str = None, join_mode: str = "direct", expire_seconds: int = 600, added_by: int = None):
        data = {
            "title": title,
            "username": username,
            "join_mode": join_mode,
            "expire_seconds": expire_seconds,
            "is_indexed": True,
            "updated_at": datetime.now()
        }
        if added_by:
            data["added_by"] = added_by
        await self.indexed_channels_data.update_one(
            {"_id": channel_id},
            {"$set": data},
            upsert=True
        )

    # FILE SHARE SAVE SYSTEM
    async def add_save_channel(self, channel_id: int):
        await self.channels_col.update_one(
            {"_id": channel_id},
            {"$set": {"_id": channel_id}},
            upsert=True
        )

    async def remove_save_channel(self, channel_id: int):
        await self.channels_col.delete_one({"_id": channel_id})

    async def get_all_save_channels(self):
        data = await self.channels_col.find().to_list(length=None)
        return [x["_id"] for x in data]
        
    async def del_indexed_channel(self, channel_id: int):
        await self.indexed_channels_data.delete_one({"_id": channel_id})

    async def update_channel_join_mode(self, channel_id, mode: str):
        await self.indexed_channels_data.update_one(
            {"_id": int(channel_id)},
            {"$set": {"join_mode": mode}}
        )

    async def search_channels(self, keyword: str):
        regex = {"$regex": keyword, "$options": "i"}
        return await self.indexed_channels_data.find({
            "is_indexed": True,
            "$or": [{"title": regex}, {"username": regex}]
        }).to_list(length=None)

    # ✅ USER STATE SYSTEM (Bot restart ke baad bhi kaam karega)
    async def set_user_state(self, user_id: int, state: str):
        await self.user_states.update_one(
            {"_id": user_id},
            {"$set": {"state": state}},
            upsert=True
        )

    async def get_user_state(self, user_id: int):
        doc = await self.user_states.find_one({"_id": user_id})
        return doc.get("state") if doc else None

    async def clear_user_state(self, user_id: int):
        await self.user_states.delete_one({"_id": user_id})


kingdb = SidDataBase(DB_URI, DB_NAME)

"""
database.py  –  MongoDB queries for the stats panel.

Assumes your users collection has documents like:
{
    "_id": ...,
    "user_id": 123456789,
    "date": datetime(2024, 6, 1, 10, 30)   ← the join date field
}

Usage in stats.py:
    from database import get_user_count, get_graph_data
"""

import calendar
from datetime import datetime, timedelta, timezone

# ── Import your existing DB connection ──────────────────────────
# Change this to match however you connect to MongoDB in your bot.
# Examples:
#   from database import db          (if you have a db.py)
#   from kingdb import db
#   from config import db
from database import database       # ← change this line to your actual import

users_col = database.users             # ← change "users" to your collection name


# ───────────────────────────────────────────────────────────────
# Internal helper
# ───────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _count_since(dt: datetime) -> int:
    """Count users whose `date` field is >= dt."""
    return await users_col.count_documents({"date": {"$gte": dt}})


async def _count_between(start: datetime, end: datetime) -> int:
    return await users_col.count_documents({
        "date": {"$gte": start, "$lt": end}
    })


# ───────────────────────────────────────────────────────────────
# Public: counts
# ───────────────────────────────────────────────────────────────

async def get_user_count(period: str) -> int:
    """
    period → "today" | "weekly" | "monthly" | "mau" | "yearly" | "all"
    Returns integer count.
    """
    now = _now_utc()

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return await _count_since(start)

    if period == "weekly":
        start = now - timedelta(days=7)
        return await _count_since(start)

    if period == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return await _count_since(start)

    if period == "mau":
        # Monthly Active Users = joined in last 30 days
        start = now - timedelta(days=30)
        return await _count_since(start)

    if period == "yearly":
        start = now.replace(month=1, day=1, hour=0, minute=0,
                            second=0, microsecond=0)
        return await _count_since(start)

    if period == "all":
        return await users_col.count_documents({})

    return 0


# ───────────────────────────────────────────────────────────────
# Public: graph data
# ───────────────────────────────────────────────────────────────

async def get_graph_data(period: str) -> tuple[list, list, str, str]:
    """
    Returns (x_labels, y_values, x_axis_title, chart_title).
    All counts come from MongoDB – no mock data.
    """
    now = _now_utc()

    # ── Today: hourly (00:00 → current hour) ──────────────────
    if period == "today":
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hours  = [f"{h:02d}:00" for h in range(24)]
        values = []
        for h in range(24):
            h_start = today_start + timedelta(hours=h)
            h_end   = h_start + timedelta(hours=1)
            count   = await _count_between(h_start, h_end)
            values.append(count)
        return hours, values, "Hour (UTC)", "Hourly User Joins – Today"

    # ── Week: last 7 days ──────────────────────────────────────
    if period == "week":
        labels = []
        values = []
        for i in range(6, -1, -1):          # 6 days ago → today
            day_start = (now - timedelta(days=i)).replace(
                hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            count   = await _count_between(day_start, day_end)
            labels.append(day_start.strftime("%a %d"))
            values.append(count)
        return labels, values, "Day", "Daily User Joins – Last 7 Days"

    # ── Month: every day of current month ─────────────────────
    if period == "month":
        month_start = now.replace(day=1, hour=0, minute=0,
                                  second=0, microsecond=0)
        num_days = calendar.monthrange(now.year, now.month)[1]
        labels = []
        values = []
        for d in range(1, num_days + 1):
            day_start = month_start.replace(day=d)
            day_end   = day_start + timedelta(days=1)
            count     = await _count_between(day_start, day_end)
            labels.append(str(d))
            values.append(count)
        title = f"Daily Joins – {now.strftime('%B %Y')}"
        return labels, values, "Date", title

    # ── Year: month-wise for current year ─────────────────────
    if period == "year":
        month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        labels = []
        values = []
        for m in range(1, 13):
            m_start = datetime(now.year, m, 1)
            if m < 12:
                m_end = datetime(now.year, m + 1, 1)
            else:
                m_end = datetime(now.year + 1, 1, 1)
            count = await _count_between(m_start, m_end)
            labels.append(month_names[m - 1])
            values.append(count)
        return labels, values, "Month", f"Monthly Joins – {now.year}"

    return [], [], "", ""
        
