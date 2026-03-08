# SplitBill — Smart Bill Splitter

Upload a photo of any restaurant bill and AI automatically reads every line item so you can split it perfectly with friends.

---

## Features

- **Photo upload** — drag & drop or tap to upload any bill photo (JPG, PNG, HEIC)
- **AI-powered** — Google Gemini reads the bill and extracts every item, subtotal, tax, and tip automatically
- **People management** — add everyone splitting the bill with coloured avatars
- **Per-item assignment** — tap names to assign each item to specific people
- **Smart splitting** — split tax & tip equally or proportionally by item totals
- **Settlement view** — see exactly who pays whom and how much
- **Copy summary** — one tap to copy the full breakdown for sharing in WhatsApp/iMessage

---

## Running Locally

### 1. Get a Gemini API key (free)
Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create a key → copy it.

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
**Mac / Linux:**
```bash
export GEMINI_API_KEY="your-gemini-key-here"
```
**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=your-gemini-key-here
```

### 4. Run the app
```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser. That's it!

---

## Deploy to Railway (get a shareable link!)

Railway gives you a public URL like `https://splitbill-production.up.railway.app` that you can share with anyone.

### Step 1 — Push to GitHub
1. Create a new repository at [github.com/new](https://github.com/new)
2. Upload all files: `app.py`, `requirements.txt`, `Procfile`

Or via terminal:
```bash
cd splitbill/
git init
git add .
git commit -m "Initial SplitBill app"
git remote add origin https://github.com/YOUR_USERNAME/splitbill.git
git push -u origin main
```

### Step 2 — Deploy on Railway
1. Go to [railway.app](https://railway.app) and sign up (free)
2. Click **New Project → Deploy from GitHub repo**
3. Select your `splitbill` repository
4. Railway auto-detects Python and deploys automatically

### Step 3 — Add your API key
1. In Railway, click your project → **Variables** tab
2. Add a variable:
   - Name: `GEMINI_API_KEY`
   - Value: `your-gemini-key-here`
3. Click **Deploy**

### Step 4 — Get your link
Go to **Settings → Domains** → click **Generate Domain**. Share that link with friends!

---

## Alternative: Deploy to Render (also free)

1. Go to [render.com](https://render.com) → New → **Web Service**
2. Connect your GitHub repo
3. Set:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add environment variable `GEMINI_API_KEY`
5. Click **Create Web Service**

---

## File structure

```
splitbill/
├── app.py            ← The entire app (Flask backend + React frontend)
├── requirements.txt  ← Python dependencies
└── Procfile          ← Tells Railway/Render how to start the app
```

---

## How it works

1. You upload a photo of a bill
2. The image is sent to Google Gemini's vision API
3. Gemini extracts every line item, price, tax, and tip as structured data
4. You assign items to people by tapping their names
5. The app calculates each person's exact share (including their portion of tax & tip)
6. The settlement view shows who pays whom to settle up

---

## Privacy

- Bill images are sent to Google's Gemini API for processing (subject to [Google's privacy policy](https://policies.google.com/privacy))
- No data is stored — everything stays in your browser session
- The app does not have a database
