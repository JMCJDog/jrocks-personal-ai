# Setup Instructions: Gemini Feedback Loop

To enable the Gemini App (Android) to control your local codebase, we need to authorize access to your Google Drive.

## Step 1: Enable Google Drive API
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project (or select an existing one).
3.  Search for **"Google Drive API"** and enable it.

## Step 2: Create Credentials
1.  Go to **APIs & Services > Credentials**.
2.  Click **Create Credentials > OAuth client ID**.
3.  Select **Application type**: "Desktop app".
4.  Name it "Vibe Coding".
5.  Click **Create**.
6.  **Download the JSON file** and rename it to `credentials.json`.

## Step 3: Place the File
Move `credentials.json` to this folder:
`c:\Users\jared\Vibe Coding (root)\Projects\jrocks-personal-ai\`

## Step 4: Create the Feedback Doc
1.  Go to Google Docs.
2.  Create a new blank document named: **`Vibe Coding Feedback`**
3.  (Optional) Type "Status: Connected" in it.

## Step 5: Authorization (One-time)
Run the script to authorize:
```powershell
python run_feedback_loop.py
```
It will open a browser window. Log in with `jared.cohen55@gmail.com` and grant access.

## Step 6: Usage
1.  Leave `run_feedback_loop.py` running on your PC.
2.  On your Android phone, ask Gemini: "Open my Vibe Coding Feedback doc".
3.  Dictate a command: "Add a new python script to say hello."
4.  Watch your PC execute it!
