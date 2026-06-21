@echo off
python pdf_auto_sender.py --dry-run --leads list.txt --body-template body_template.md --pdf sample.pdf --subject "Secure Document Portal" --smtp-host %SMTP_HOST% --smtp-port %SMTP_PORT% --smtp-user %SMTP_USER% --smtp-password %SMTP_PASSWORD% --from-email %FROM_EMAIL% --sender-name "%SENDER_NAME%"
pause
