import logging
import requests
import io
import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get('BOT_TOKEN')
REQUIRED_CHANNEL = os.environ.get('REQUIRED_CHANNEL', '@py_on')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False

async def generate_ai_response(prompt: str) -> str:
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return "عذراً، حدث خطأ أثناء معالجة طلبك."
            
    except Exception as e:
        return "عذراً، حدث خطأ أثناء معالجة طلبك."

async def generate_anime_image(prompt: str) -> bytes:
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        data = {
            "model": "dall-e-2",
            "prompt": f"anime style, {prompt}, high quality",
            "size": "512x512",
            "n": 1
        }
        
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            image_url = result['data'][0]['url']
            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                return img_response.content
        return None
            
    except Exception as e:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "🎨 أهلاً بك في بوت صور الأنمي!"
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    if not await check_subscription(user_id, context):
        await update.message.reply_text("⚠️ يرجى الاشتراك في القناة أولاً", parse_mode='Markdown')
        return
    
    processing_msg = await update.message.reply_text("🔄 جاري المعالجة...")
    
    try:
        image_keywords = ['صورة', 'رسم', 'أنمي']
        if any(keyword in user_message.lower() for keyword in image_keywords):
            image_data = await generate_anime_image(user_message)
            if image_data:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
                await update.message.reply_photo(
                    photo=io.BytesIO(image_data),
                    caption=f"🎨 تم الإنشاء بنجاح!\n{user_message}",
                    parse_mode='Markdown'
                )
            else:
                await context.bot.edit_message_text("❌ خطأ في التوليد", chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
        else:
            ai_response = await generate_ai_response(user_message)
            await context.bot.edit_message_text(f"🤖 {ai_response}", chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
            
    except Exception as e:
        await context.bot.edit_message_text("❌ خطأ غير متوقع", chat_id=update.effective_chat.id, message_id=processing_msg.message_id)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "📖 استخدم /start للبدء"
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)
    logger.info("Bot started!")
    app.run_polling()

if __name__ == '__main__':
    main()
