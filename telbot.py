import logging
import pytz
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
import gspread
from google.oauth2.service_account import Credentials
import telegram
import asyncio
import os

# ---------------- CONFIG ----------------
TOKEN = "you telegram token (from bot father)"  
SHEET_ID = "sheet id"
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "name")
TIMEZONE = "TimeZone "
REFRESH_HOURS = 24 
# ----------------------------------------

logging.basicConfig(
    level=logging.INFO,  
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class TelegramScheduler:
    def __init__(self):
        self.bot = telegram.Bot(token=TOKEN)
        self.timezone = pytz.timezone(TIMEZONE)
        self.scheduler = AsyncIOScheduler(jobstores={'default': MemoryJobStore()}, timezone=self.timezone)
        self.sheet = None

    async def initialize(self):
        """Initialize Google Sheets and start scheduler"""
        self.setup_sheets()
        self.scheduler.start()
        await self.load_and_schedule_messages()
        self.scheduler.add_job(self.reload_messages_periodically, 'interval', hours=REFRESH_HOURS)
        logger.info("✅ Scheduler initialized successfully")

    def setup_sheets(self):
        """Connect to Google Sheets"""
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        gc = gspread.authorize(creds)
        self.sheet = gc.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
        logger.info(f"📄 Connected to sheet: {SHEET_ID}, worksheet: {WORKSHEET_NAME}")

    async def send_and_delete(self, chat_id, message,row_indx= None ):
        """Send message and schedule delete after 1 hour"""
        try:
            msg = await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            logger.info(f"✅ Message sent to {chat_id}")


            if row_indx is not None:
                try:
                    self.sheet.update_cell(row_indx, 5,"sent")
                    logger.info(f"📝 Marked row {row_indx} as 'sent' in sheet")
                except Exception as e :
                    logger.warning(f"⚠️ Could not update status for row {row_indx}: {e}")




            # Schedule delete after 1 hour
            delete_time = datetime.now(self.timezone) + timedelta(hours=1)
            job_id = f"delete_{msg.message_id}_{chat_id}"
            self.scheduler.add_job(
                self.delete_message,
                'date',
                run_date=delete_time,
                args=[chat_id, msg.message_id],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"🕒 Delete scheduled for message {msg.message_id} at {delete_time}")

        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")

    async def delete_message(self, chat_id, message_id):
        """Delete a specific Telegram message"""
        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.info(f"🗑️ Message {message_id} deleted from chat {chat_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete message {message_id}: {e}")

    async def load_and_schedule_messages(self):
        """Load messages from sheet and schedule them (no duplicates)"""
        all_rows = self.sheet.get_all_values()

        # 🔍 DEBUG 
        logger.info(f"🔍 Total rows in sheet (including header): {len(all_rows)}")
        if all_rows:
            logger.info(f"🔍 Header row: {all_rows[0]}")

        current_time = datetime.now(self.timezone)
        logger.info(f"⏰ Current time (timezone {TIMEZONE}): {current_time}")
        scheduled = 0

        #start from the second row second coloumn 
        for idx, row in enumerate(all_rows[1:], start=2):
            logger.info(f"➡️ Row {idx} raw data: {row}")

            try:
                status =""
                if len(row)>=5:
                    status = str(row[4]).strip().lower()

                if status in ("sent",'done','inactive','off'):
                    logger.info(f"⏭️ Skipping row {idx}: status='{status}'")   
                    continue
                
                # make sure there are minimum of 4 coloums  
                if len(row) < 4:
                    logger.warning(f"⚠️ Skipping row {idx}: not enough columns (len={len(row)})")
                    continue

                chat_id_str = str(row[1]).strip()   # 👈 second column  (B)
                message = str(row[2]).strip()       # 👈 third column (C)
                send_time_str = str(row[3]).strip() # 👈 fourth column (D)

                logger.info(
                    f"Row {idx} parsed -> chat_id_str='{chat_id_str}', "
                    f"message='{message}', send_time_str='{send_time_str}'"
                )

                if not (chat_id_str and message and send_time_str):
                    logger.warning(f"⚠️ Skipping row {idx}: missing data")
                    continue

                try:
                    chat_id = int(chat_id_str)
                except ValueError:
                    logger.warning(f"⚠️ Skipping row {idx}: invalid chat_id '{chat_id_str}'")
                    continue

                send_time = self.parse_datetime(send_time_str)
                if not send_time:
                    logger.warning(f"⚠️ Skipping row {idx}: could not parse datetime '{send_time_str}'")
                    continue

                if send_time < current_time:
                    logger.info(f"⏭️ Skipping row {idx}: send_time {send_time} is in the past")
                    continue

              # unique job_id to avoid repeated scheduling  
                job_id = f"send_{idx}_{chat_id}_{int(send_time.timestamp())}"
                if self.scheduler.get_job(job_id):
                    logger.info(f"⏭️ Job {job_id} already scheduled, skipping duplicate")
                    continue

                # schedule messages 
                self.scheduler.add_job(
                    self.send_and_delete,
                    'date',
                    run_date=send_time,
                    args=[chat_id, message],
                    id=job_id,
                    replace_existing=True
                )
                scheduled += 1
                logger.info(f"📅 Scheduled message from row {idx} for {send_time}")

            except Exception as e:
                logger.error(f"❌ Row {idx} error: {e}")

        logger.info(f"🎯 Total scheduled messages: {scheduled}")

    def parse_datetime(self, date_str):
        """Parse flexible datetime formats"""
        formats = [
            "%d/%m/%Y %H:%M:%S",  # 02/12/2025 16:30:00
            "%d/%m/%Y %H:%M",     # 02/12/2025 16:30
            "%Y-%m-%d %H:%M:%S",  # 2025-12-02 16:30:00
            "%Y-%m-%d %H:%M",     # 2025-12-02 16:30
            "%m/%d/%Y %H:%M:%S",  # 12/02/2025 16:30:00
            "%m/%d/%Y %H:%M",     # 12/02/2025 16:30
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                localized_dt = self.timezone.localize(dt)
                logger.info(f"✅ Parsed datetime '{date_str}' using format '{fmt}' -> {localized_dt}")
                return localized_dt
            except ValueError:
                continue

        logger.warning(f"❌ Failed to parse datetime: '{date_str}' with all known formats")
        return None

    async def reload_messages_periodically(self):
        """Reload new rows every 3 hours"""
        logger.info("🔄 Refreshing sheet and scheduling new messages...")
        self.setup_sheets()
        await self.load_and_schedule_messages()

async def main():
    scheduler = TelegramScheduler()
    await scheduler.initialize()
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
