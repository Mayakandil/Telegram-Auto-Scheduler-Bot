# 🚀 Telegram Scheduler Bot #
- Bot to schedule Telegram messages based on data stored in a Google Sheet.
-  This project sends messages at scheduled times and auto-deletes them after one hour.
   
    # 📌 Overview
- This bot reads rows from a Google Sheet and schedules messages to be sent to specific chat IDs at specific times.
- After sending a message, the bot automatically deletes it after 1 hour.
    
    # Key Features:
📅 Load message queue from Google Sheets
⏱️ Schedule messages at exact times
🗑️ Auto-delete messages 1 hour after sending
🔄 Periodic sheet refresh
⚠️ Skips duplicates and already-sent rows
  
   # 🛠️ Technologies Used
- Python 3
- apscheduler
- gspread
- Google Sheets API
- Telegram Bot API
- python-telegram-bot
- AsyncIO
  
   # 📁 Project Structure

project/
│
├── scheduler.py          # Main bot logic
├── requirements.txt      # Dependencies
├── .env.example          # Example environment variables
└── README.md

⚠️ Note:
Do NOT upload credentials.json or .env to GitHub.
Store them locally only.

   # 🔐 Environment Variables
- Create a .env file in your project root (DO NOT upload it).
- You can use the example file included:
    .env.example
    TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
    GOOGLE_SHEET_ID=your-google-sheet-id-here
    WORKSHEET_NAME=Sheet1
    TIMEZONE=Africa/Cairo
    REFRESH_HOURS=24
* * Make your own .env file: 

    # 🔧 Setting Up Google Sheets
- Go to Google Cloud Console
- Create a project
- Enable:
      - Google Sheets API
      - Google Drive API
- Create Service Account
- Generate JSON Key → save it as credentials.json (local only)
- Share your Google Sheet with the service account email:
       your-service-account@yourproject.iam.gserviceaccount.com

# ▶️ Running the Bot
- Install dependencies:
      pip install -r requirements.txt
- Make sure you have:
      .env
      credentials.json
placed in the same directory as your script.
- Run the scheduler:
      python scheduler.py
The bot will load messages from the Google Sheet and start scheduling them.

# 📄 Google Sheet Format
Your sheet must contain:
Column	Meaning
A	    Any (ignored)
B	    Chat ID
C	    Message
D	    Send DateTime
E	    Status (sent / active / off / done / etc.)
Example row: 
A	B	        C	     D	                E
1	12345678	Hello!	02/12/2025 16:30	active

# 🔒 Security Notes
Never upload:
  credentials.json
  .env
  Real tokens or sheet IDs
If you ever exposed a token, regenerate it from BotFather.
Regenerate Google Service Account keys if leaked.

# 🤝 Contributions
Feel free to fork, open issues, or submit pull requests.

# 📬 Contact
If you have questions or need help integrating your own scheduling logic—happy to assist!
