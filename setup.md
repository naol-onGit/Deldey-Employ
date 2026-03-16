# Deldey Employment Agency Bot — Setup Guide

---

## 1. Google Sheets Credentials

### Step 1 — Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **New Project** → name it `deldey-bot` → Create.

### Step 2 — Enable APIs

Inside your project, go to **APIs & Services → Library** and enable:

- **Google Sheets API**
- **Google Drive API**

### Step 3 — Create a Service Account

1. Go to **APIs & Services → Credentials → Create Credentials → Service Account**.
2. Name it `deldey-sheets-bot`, click **Done**.
3. Click the service account → **Keys tab → Add Key → Create new key → JSON**.
4. A `.json` file downloads — **keep it safe, never commit it to git**.

### Step 4 — Prepare the JSON for Vercel

The entire contents of that JSON file become the `GOOGLE_CREDENTIALS_JSON`
environment variable. Minify it first (remove whitespace) or copy it as-is —
Vercel handles multi-line env values if you paste it directly in the dashboard.

### Step 5 — Share the Google Sheet with the Service Account

1. Open your target Google Sheet.
2. Click **Share** and paste the service account email
   (looks like `deldey-sheets-bot@your-project.iam.gserviceaccount.com`).
3. Give it **Editor** access.
4. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit`

### Step 6 — Add a Header Row (recommended)

In row 1 of your sheet, add these columns in order:

| Full Name | Age | Profession | Education | Years of Experience | Primary Phone | Secondary Phone |

---

## 2. Telegram Bot Setup

1. Message [@BotFather](https://t.me/BotFather) on Telegram.
2. Send `/newbot` → follow prompts → copy the **Bot Token**.
3. Generate a random secret string for the webhook
   (e.g. run `python -c "import secrets; print(secrets.token_hex(32))"`)
   — this becomes `WEBHOOK_SECRET`.

---

## 3. Environment Variables

Set these in **Vercel → Project → Settings → Environment Variables**:

| Variable                  | Description                                    |
| ------------------------- | ---------------------------------------------- |
| `BOT_TOKEN`               | Telegram bot token from BotFather              |
| `WEBHOOK_SECRET`          | Random secret string you generated             |
| `GOOGLE_SHEET_ID`         | Spreadsheet ID from the Google Sheet URL       |
| `GOOGLE_CREDENTIALS_JSON` | Full contents of the service account JSON file |

For **local development**, create a `.env` file:

```
BOT_TOKEN=123456:ABC-your-token
WEBHOOK_SECRET=your_random_secret
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```

Add `.env` to `.gitignore` immediately.

---

## 4. Register the Webhook with Telegram

After deploying to Vercel, run this once (replace placeholders):

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://your-project.vercel.app/webhook" \
  -d "secret_token=<WEBHOOK_SECRET>"
```

Telegram will confirm with `{"ok":true,"result":true}`.

---

## 5. Local Development

```bash
pip install -r requirements.txt
pip install python-dotenv

# Start the server
uvicorn main:app --reload --port 8000
```

To test locally with a public URL, use [ngrok](https://ngrok.com/):

```bash
ngrok http 8000
# Then re-register the webhook with the ngrok HTTPS URL
```

---

## 6. File Structure

```
deldey-bot/
├── main.py           # FastAPI app + bot logic
├── requirements.txt  # Python dependencies
├── vercel.json       # Vercel deployment config
├── .env              # Local secrets (never commit!)
└── .gitignore
```

---

## 7. Conversation Flow

```
/start
  └─→ Full Name
        └─→ Age
              └─→ Profession
                    └─→ Education
                          └─→ Years of Experience
                                └─→ Primary Phone
                                      └─→ Secondary Phone
                                            └─→ ✅ Saved to Google Sheet
```

Any sticker, voice note, photo, or non-text message at any step triggers:

> "Please provide the requested information in text format."
