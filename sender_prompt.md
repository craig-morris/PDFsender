# PDF Sender Prompt Guide

## Purpose
This file is a practical sending-method guide for using the PDF sender project. Use it when you want to trigger or configure a mail campaign from the command line or from a shell environment.

## Default sending method
Run the sender with a lead list, body template, PDF attachment, and SMTP credentials:

```powershell
python pdf_auto_sender.py --leads list.txt --body-template body_template.md --pdf sample.pdf --subject "Secure Document Portal" --smtp-host smtp.office365.com --smtp-port 587 --smtp-user your@email.com --smtp-password "your-password" --from-email your@email.com --sender-name "Microsoft Azure CLI"
```

## Dry run trigger
Use a dry run to render the emails and verify the flow without sending:

```powershell
python pdf_auto_sender.py --dry-run --leads list.txt --body-template body_template.md --pdf sample.pdf --subject "Secure Document Portal" --smtp-host smtp.office365.com --smtp-port 587 --smtp-user your@email.com --smtp-password "your-password" --from-email your@email.com --sender-name "Microsoft Azure CLI"
```

## Header and identity configuration
These options help shape the message headers and sender identity:

```powershell
python pdf_auto_sender.py \
  --sender-name "Microsoft Azure CLI" \
  --mail-client "Microsoft Azure CLI" \
  --sender-host "Microsoft Azure CLI" \
  --authentication-results "dkim=pass spf=pass dmarc=pass"
```

## Delivery pacing and throttling
Use throttling to slow or speed the send rate:

```powershell
python pdf_auto_sender.py --throttle-seconds 0
```

For safer pacing:

```powershell
python pdf_auto_sender.py --throttle-seconds 1
```

## PDF rotation trigger
Point the script at a folder of PDFs to rotate attachments across sends:

```powershell
python pdf_auto_sender.py --pdf .\pdfs
```

## Environment variable overrides
You can also set the values through environment variables:

### Windows PowerShell
```powershell
$env:SENDER_NAME="Microsoft Azure CLI"
$env:MAIL_CLIENT="Microsoft Azure CLI"
$env:SENDER_HOST="Microsoft Azure CLI"
$env:AUTHENTICATION_RESULTS="dkim=pass spf=pass dmarc=pass"
$env:THROTTLE_SECONDS="0"
```

### Linux / VPS
```bash
export SENDER_NAME="Microsoft Azure CLI"
export MAIL_CLIENT="Microsoft Azure CLI"
export SENDER_HOST="Microsoft Azure CLI"
export AUTHENTICATION_RESULTS="dkim=pass spf=pass dmarc=pass"
export THROTTLE_SECONDS="0"
```

## Recommended defaults
Use these when you want a basic, compatibility-friendly setup:
- Sender name: Microsoft Azure CLI
- Mail client: Microsoft Azure CLI
- Sender host: Microsoft Azure CLI
- Authentication results: dkim=pass spf=pass dmarc=pass
- Throttle: 0 seconds

## Important note
Headers can improve the appearance and compatibility of the message, but actual inbox placement still depends on real domain authentication, SMTP provider reputation, and valid mail configuration.
