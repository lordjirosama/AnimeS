from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from helper_func import encode, get_message_id, is_admin
from typing import Dict, Optional, List
import asyncio

# Per-user batch state management
batch_states: Dict[int, dict] = {}

class BatchState:
    """Manages the state of a batch process for a user"""
    def __init__(self, user_id: int, total_files: int):
        self.user_id = user_id
        self.total_files = total_files
        self.start_msg_id: Optional[int] = None
        self.collected_links: Dict[int, Dict[str, str]] = {}
        self.is_active = True
        self.progress_message_id: Optional[int] = None
        self.processing = False

    def cancel(self):
        """Cancel the batch process"""
        self.is_active = False
        self.processing = False

    def is_running(self) -> bool:
        """Check if batch is still active"""
        return self.is_active

    def add_links(self, msg_id: int, links: Dict[str, str]):
        """Store generated links for a message"""
        self.collected_links[msg_id] = links

    def get_all_links(self) -> Dict[int, Dict[str, str]]:
        """Get all collected links"""
        return self.collected_links


def get_batch_state(user_id: int) -> Optional[BatchState]:
    """Retrieve batch state for a user"""
    return batch_states.get(user_id)


def create_batch_state(user_id: int, total_files: int) -> BatchState:
    """Create a new batch state for a user"""
    state = BatchState(user_id, total_files)
    batch_states[user_id] = state
    return state


def clear_batch_state(user_id: int):
    """Clear batch state for a user"""
    if user_id in batch_states:
        del batch_states[user_id]


async def get_channel_message_id(client: Client, user_id: int) -> Optional[int]:
    """Ask user to provide a channel message link and extract message ID"""
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"
    
    while True:
        try:
            message = await client.ask(
                text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n"
                     f"<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote></b>",
                chat_id=user_id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=300,
                disable_web_page_preview=True
            )
            
            # Check if user cancelled
            state = get_batch_state(user_id)
            if not state or not state.is_running():
                return None
            
            msg_id = await get_message_id(client, message)
            
            if msg_id:
                return msg_id
            else:
                await message.reply(
                    f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>",
                    quote=True,
                    disable_web_page_preview=True
                )
                continue
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"Error in get_channel_message_id: {e}")
            return None


async def fetch_message_with_retry(client: Client, chat_id: int, msg_id: int, retries: int = 3) -> Optional[Message]:
    """Safely fetch a message with retry logic"""
    for attempt in range(retries):
        try:
            message = await client.get_messages(chat_id, msg_id)
            if message:
                return message
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(0.5)
                continue
            print(f"Failed to fetch message {msg_id}: {e}")
    return None


async def generate_quality_links_for_message(client: Client, chat_id: int, msg_id: int) -> Optional[Dict[str, str]]:
    """
    Generate quality links for a single message
    This function should integrate with your existing link generation logic
    """
    try:
        message = await fetch_message_with_retry(client, chat_id, msg_id)
        if not message:
            return None
        
        # Generate the encoded link using existing encode function
        base64_string = await encode(f"get-{msg_id * abs(chat_id)}")
        link = f"https://t.me/{client.username}?start={base64_string}"
        
        # Return links in the expected format
        # Note: Adjust these keys based on your actual quality extraction logic
        links = {
            '480p': link,
            '720p': link,
            '1080p': link,
            'hdrip': link
        }
        
        return links
    except Exception as e:
        print(f"Error generating links for message {msg_id}: {e}")
        return None


@Bot.on_message(filters.command('batch') & filters.private & is_admin)
async def batch_handler(client: Client, message: Message):
    """
    Enhanced batch command handler with parameter support
    Usage: /batch 5 (to process 5 consecutive messages)
    """
    user_id = message.from_user.id
    
    # Check if user already has active batch
    existing_state = get_batch_state(user_id)
    if existing_state and existing_state.is_running():
        await message.reply(
            "<b>❌ Eʀʀᴏʀ..\n<blockquote>Yᴏᴜ ᴀʟʀᴇᴀᴅʏ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ʙᴀᴛᴄʜ ᴘʀᴏᴄᴇss. Use /cancel to stop it.</blockquote></b>",
            disable_web_page_preview=True
        )
        return
    
    # Parse command arguments
    args = message.text.split()
    
    if len(args) > 1:
        # New parameterized batch mode: /batch {count}
        try:
            total_files = int(args[1])
            if total_files < 1:
                await message.reply("<b>❌ Eʀʀᴏʀ..\n<blockquote>Cᴏᴜɴᴛ ᴍᴜsᴛ ʙᴇ ᴀ ᴘᴏsɪᴛɪᴠᴇ ɪɴᴛᴇɢᴇʀ.</blockquote></b>")
                return
            
            # Create batch state
            state = create_batch_state(user_id, total_files)
            
            # Get starting message ID
            start_msg_id = await get_channel_message_id(client, user_id)
            if not start_msg_id or not state.is_running():
                await message.reply("<b>❌ Pʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ ᴏʀ ᴛɪᴍᴇᴅ ᴏᴜᴛ.</b>")
                clear_batch_state(user_id)
                return
            
            state.start_msg_id = start_msg_id
            state.processing = True
            
            # Fetch and process messages
            progress_msg = await message.reply(
                f"<b>⏳ Pʀᴏᴄᴇssɪɴɢ {total_files} ᴍᴇssᴀɢᴇs...\n\n"
                f"<code>0/{total_files}</code></b>"
            )
            state.progress_message_id = progress_msg.id
            
            successful_count = 0
            failed_count = 0
            
            for i in range(total_files):
                # Check if batch was cancelled
                if not state.is_running():
                    await progress_msg.edit_text(
                        "<b>❌ Bᴀᴛᴄʜ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>"
                    )
                    clear_batch_state(user_id)
                    return
                
                current_msg_id = start_msg_id + i
                
                # Generate links for this message
                links = await generate_quality_links_for_message(
                    client,
                    client.db_channel.id,
                    current_msg_id
                )
                
                if links:
                    state.add_links(current_msg_id, links)
                    successful_count += 1
                else:
                    failed_count += 1
                
                # Update progress
                progress_text = f"<b>⏳ Pʀᴏᴄᴇssɪɴɢ {total_files} ᴍᴇssᴀɢᴇs...\n\n"
                progress_text += f"<code>{successful_count + failed_count}/{total_files}</code>"
                if failed_count > 0:
                    progress_text += f" <b>({failed_count} ғᴀɪʟᴇᴅ)</b>"
                progress_text += "</b>"
                
                try:
                    await progress_msg.edit_text(progress_text)
                except:
                    pass
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            state.processing = False
            
            # Generate final output
            if successful_count > 0:
                # Compile all quality links
                all_480p = " && ".join([
                    f"[M{msg_id}]({links['480p']})" 
                    for msg_id, links in state.get_all_links().items()
                ])
                all_720p = " && ".join([
                    f"[M{msg_id}]({links['720p']})" 
                    for msg_id, links in state.get_all_links().items()
                ])
                all_1080p = " && ".join([
                    f"[M{msg_id}]({links['1080p']})" 
                    for msg_id, links in state.get_all_links().items()
                ])
                all_hdrip = " && ".join([
                    f"[M{msg_id}]({links['hdrip']})" 
                    for msg_id, links in state.get_all_links().items()
                ])
                
                final_text = (
                    "<b>🎬 Qᴜᴀʟɪᴛʏ Lɪɴᴋs Rᴇᴀᴅʏ!</b>\n\n"
                    "<code>"
                    f"𝟰𝟴𝟬𝗽 - {all_480p}\n"
                    f"𝟳𝟮𝟬𝗽 - {all_720p}\n"
                    f"𝟭𝟬𝟴𝟬𝗽 - {all_1080p}\n"
                    f"𝗛𝗗𝗿𝗶𝗽 - {all_hdrip}"
                    "</code>\n\n"
                    "<i>💡 Tap to copy all links</i>"
                )
                
                await progress_msg.edit_text(final_text)
            else:
                await progress_msg.edit_text(
                    "<b>❌ Nᴏ ᴍᴇssᴀɢᴇs ᴄᴏᴜʟᴅ ʙᴇ ᴘʀᴏᴄᴇssᴇᴅ.</b>"
                )
            
            clear_batch_state(user_id)
            
        except ValueError:
            await message.reply(
                "<b>❌ Eʀʀᴏʀ..\n<blockquote>Iɴᴠᴀʟɪᴅ ᴀʀɢᴜᴍᴇɴᴛ. Usage: /batch {count}\n"
                "Exᴀᴍᴘʟᴇ: /batch 5</blockquote></b>"
            )
    else:
        # Original batch mode: /batch (without parameters)
        await original_batch_handler(client, message)


async def original_batch_handler(client: Client, message: Message):
    """Original batch handler for backward compatibility"""
    user_id = message.from_user.id
    
    # Check if user already has active batch
    existing_state = get_batch_state(user_id)
    if existing_state and existing_state.is_running():
        await message.reply(
            "<b>❌ Eʀʀᴏʀ..\n<blockquote>Yᴏᴜ ᴀʟʀᴇᴀᴅʏ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ʙᴀᴛᴄʜ ᴘʀᴏᴄᴇss. Use /cancel to stop it.</blockquote></b>",
            disable_web_page_preview=True
        )
        return
    
    state = create_batch_state(user_id, 2)  # Original mode processes 2 messages
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"
    
    try:
        # Get first message
        while state.is_running():
            try:
                first_message = await client.ask(
                    text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Fɪʀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n"
                         f"<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote></b>",
                    chat_id=user_id,
                    filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                    timeout=300,
                    disable_web_page_preview=True
                )
            except asyncio.TimeoutError:
                clear_batch_state(user_id)
                return
            
            if not state.is_running():
                return
            
            f_msg_id = await get_message_id(client, first_message)
            if f_msg_id:
                state.start_msg_id = f_msg_id
                break
            else:
                await first_message.reply(
                    f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>",
                    quote=True,
                    disable_web_page_preview=True
                )
                continue
        
        # Get second message
        while state.is_running():
            try:
                second_message = await client.ask(
                    text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Lᴀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n"
                         f"<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote></b>",
                    chat_id=user_id,
                    filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                    timeout=300,
                    disable_web_page_preview=True
                )
            except asyncio.TimeoutError:
                clear_batch_state(user_id)
                return
            
            if not state.is_running():
                return
            
            s_msg_id = await get_message_id(client, second_message)
            if s_msg_id:
                break
            else:
                await second_message.reply(
                    f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>",
                    quote=True,
                    disable_web_page_preview=True
                )
                continue
        
        # Generate link
        string = f"get-{state.start_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
        base64_string = await encode(string)
        link = f"https://t.me/{client.username}?start={base64_string}"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]
        ])
        
        await second_message.reply_text(
            f"<b>Bᴇʟᴏᴡ ɪs ʏᴏᴜʀ ʟɪɴᴋ:</b>\n<blockquote>{link}</blockquote>",
            quote=True,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
    finally:
        clear_batch_state(user_id)


@Bot.on_message(filters.command('cancel') & filters.private)
async def cancel_batch(client: Client, message: Message):
    """Cancel active batch process"""
    user_id = message.from_user.id
    state = get_batch_state(user_id)
    
    if state and state.is_running():
        state.cancel()
        clear_batch_state(user_id)
        await message.reply(
            "<b>❌ Bᴀᴛᴄʜ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.</b>",
            disable_web_page_preview=True
        )
    else:
        await message.reply(
            "<b>❌ Eʀʀᴏʀ..\n<blockquote>Nᴏ ᴀᴄᴛɪᴠᴇ ʙᴀᴛᴄʜ ᴘʀᴏᴄᴇss ғᴏᴜɴᴅ.</blockquote></b>"
        )


@Bot.on_message(filters.command('genlink') & filters.private & is_admin)
async def link_generator(client: Client, message: Message):
    """Original genlink handler (unchanged)"""
    user_id = message.from_user.id
    
    # Check if user has active batch
    existing_state = get_batch_state(user_id)
    if existing_state and existing_state.is_running():
        await message.reply(
            "<b>❌ Eʀʀᴏʀ..\n<blockquote>Yᴏᴜ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ʙᴀᴛᴄʜ ᴘʀᴏᴄᴇss. Use /cancel to stop it.</blockquote></b>",
            disable_web_page_preview=True
        )
        return
    
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"
    
    while True:
        try:
            channel_message = await client.ask(
                text=f"<b><blockquote>Fᴏʀᴡᴀʀᴅ ᴛʜᴇ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel} (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n"
                     f"<blockquote>Oʀ Sᴇɴᴅ ᴛʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</blockquote></b>",
                chat_id=user_id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=300,
                disable_web_page_preview=True
            )
        except asyncio.TimeoutError:
            return
        
        msg_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        else:
            await channel_message.reply(
                f"<b>❌ Eʀʀᴏʀ..\n<blockquote>Tʜɪs Fᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ᴏʀ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ɪs ɴᴏᴛ ғʀᴏᴍ ᴍʏ {channel}</blockquote></b>",
                quote=True,
                disable_web_page_preview=True
            )
            continue
    
    base64_string = await encode(f"get-{msg_id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f'https://telegram.me/share/url?url={link}')]
    ])
    
    await channel_message.reply_text(
        f"<b>Bᴇʟᴏᴡ ɪs ʏᴏᴜʀ ʟɪɴᴋ:</b>\n<blockquote>{link}</blockquote>",
        quote=True,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
