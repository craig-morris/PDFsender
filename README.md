# PDFsender 2.0

Lightweight Python SMTP sender for sending plain-text email bodies with PDF attachments.

## Features
- Supports SMTP ports 587 and 465
- SMTP rotation across multiple hosts
- Plain-text body rendering from a markdown template
- Subject and sender name support
- Variable replacement for lead fields
- Auto-creates output files for sent, delivered, failed, logs, and campaign log
- Supports configuration from a .env-style file for Windows and VPS use

## Files
- pdf_auto_sender.py: Main script
- list.txt: Sample leads list
- body_template.md: Default email body template
- sample.pdf: Sample PDF attachment
- sender_prompt.md: Sending-method guide
- .env.example: Example configuration file

## Requirements
- Python 3.8+
- No third-party packages are required for the base script

## Quick setup guide

### Option 1: Windows (local machine or VS Code)
1. Install Python 3.10+ from https://www.python.org/downloads/windows/ or with:
   ```powershell
   winget install --id Python.Python.3.12 -e
   ```
2. During installation, enable "Add Python to PATH".
3. Reopen VS Code after installation.
4. Open the project folder in VS Code.
5. Press Ctrl+Shift+P and run "Python: Select Interpreter".
6. Choose the installed Python version.
7. Open a terminal in the project folder and run:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
8. Test without sending:
   ```powershell
   python pdf_auto_sender.py --dry-run --leads list.txt --body-template body_template.md --pdf sample.pdf --subject "Secure Document Portal" --smtp-host smtp.example.com --smtp-port 587 --smtp-user user@example.com --smtp-password secret --from-email sender@example.com --sender-name "PDFsender"
   ```

### Option 2: VPS / Linux server (Ubuntu/Debian)
1. Connect to your VPS and install Python:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip
   ```
2. Go to the project folder:
   ```bash
   cd /path/to/PDFsender
   ```
3. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Create your config file:
   ```bash
   nano .env.myconfig
   ```
   Add the SMTP and sender settings you want to use, for example:
   ```env
   SMTP_HOST=smtp.office365.com
   SMTP_PORT=587
   SMTP_USER=your-email@example.com
   SMTP_PASSWORD=your-password
   FROM_EMAIL=your-email@example.com
   SENDER_NAME=Microsoft Azure CLI
   MAIL_CLIENT=Microsoft Azure CLI
   SENDER_HOST=Microsoft Azure CLI
   AUTHENTICATION_RESULTS=dkim=pass spf=pass dmarc=pass
   THROTTLE_SECONDS=0
   ```
6. Run a dry test:
   ```bash
   python pdf_auto_sender.py --config .env.myconfig --dry-run --leads list.txt --body-template body_template.md --pdf sample.pdf --subject "Secure Document Portal"
   ```
7. Send for real:
   ```bash
   python pdf_auto_sender.py --config .env.myconfig --leads list.txt --body-template body_template.md --pdf sample.pdf --subject "Secure Document Portal"
   ```
8. If you want the process to keep running in the background:
   ```bash
   nohup python pdf_auto_sender.py --config .env.myconfig --leads list.txt --body-template body_template.md --pdf sample.pdf --subject "Secure Document Portal" > sender.log 2>&1 &
   ```
9. If Python is not installed on the VPS yet, install it first:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip
   ```

## Configuration file setup
You can keep your SMTP credentials and sender metadata in a .env-style file instead of typing them every time.

### Create a config file
Create a file such as `.env.myconfig` or `.env` in the project folder:

```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
FROM_EMAIL=your-email@example.com
SENDER_NAME=Microsoft Azure CLI
MAIL_CLIENT=Microsoft Azure CLI
SENDER_HOST=Microsoft Azure CLI
AUTHENTICATION_RESULTS=dkim=pass spf=pass dmarc=pass
THROTTLE_SECONDS=0
```

### Run with the config file
#### Windows
```powershell
python pdf_auto_sender.py --config .env.myconfig --dry-run
```

#### VPS / Linux
```bash
python pdf_auto_sender.py --config .env.myconfig --dry-run
```

### Override order
The sender resolves settings in this order:
1. Command-line argument
2. Environment variable
3. Config file value
4. Built-in default

## Running for real
```bash
python pdf_auto_sender.py --leads list.txt --body-template body_template.md --pdf sample.pdf --subject "Secure Document Portal" --smtp-host smtp.example.com --smtp-port 587 --smtp-user user@example.com --smtp-password secret --from-email sender@example.com --sender-name "PDFsender"
```

## Notes
- If you are using VS Code on Windows and `python` is not recognized, restart the terminal or install Python again with PATH enabled.
- If PowerShell blocks activation, run:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```
