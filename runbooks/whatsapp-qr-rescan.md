# Runbook: WhatsApp Session Re-Scan (Client-Facing)

*Appliance module: inquiry auto-response (Phase A)*
*When to use: WhatsApp bot stopped responding, or you received the
"session dropped" alert.*

## The 1-page version

The WhatsApp connection works like WhatsApp Web on your phone. Once in a
while the session expires and someone must scan a QR code — same as
re-linking WhatsApp Web. It takes under 5 minutes.

## Steps

1. Open the link MJCX gave you: **http://wa.yourcompany.com:8080/manager**
   (evolution-api manager screen)
2. Find your instance (usually named after your company) → click **QR Code**
3. A QR appears (it refreshes every ~20 seconds — that's normal)
4. On the phone that owns the WhatsApp number:
   **WhatsApp → Settings → Linked Devices → Link a Device**
5. Point the camera at the QR on your computer screen
6. Wait for the green "connected" status in the manager screen
7. Send a test message to your own WhatsApp business number —
   the bot should reply within seconds

## If the QR won't scan

- QRs expire fast: if it fails, let it refresh and try again (up to 3×)
- Phone must have internet
- If WhatsApp shows "too many linked devices": remove an old one under
  Linked Devices, then scan again

## Still stuck?

Message MJCX support with:
- a screenshot of the manager screen
- what the phone shows when scanning

*Response target: same business day.*
