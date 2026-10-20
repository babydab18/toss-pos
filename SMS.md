# Optional order-ready SMS

SMS is disabled until a provider is configured. The POS, saved phone numbers,
and kitchen continue to work without it. No live messages have been sent in testing.

The cashier can enter an optional phone number. Select **Customer wants an
order-ready SMS** only when requested, using international format such as +91
followed by the phone number. Marking the order ready queues one notification.
The computer needs internet access to send it; local orders do not.

## Twilio adapter

No provider account has been selected or purchased. Twilio is an optional adapter,
not an activated service. Create the account and an approved sender/messaging
service before enabling it. Confirm costs and destination-country requirements.
For India, check Twilio's current sender/DLT requirements with the provider:
https://www.twilio.com/en-us/guidelines/in/sms

For the local Windows launcher, copy `.env.sms.example` to `.env.sms` in the
project root and edit it with Notepad. Never commit or share the filled file.
Set SMS_PROVIDER=twilio, account SID, auth token, and either a sender number or
Messaging Service SID. Restart the launcher. For Docker use the same variables
in `.env` (Compose forwards them); restart/recreate the API container.

Message text: `TOSS: Your order #123 is ready. Please collect it at the counter.`
The number changes per order. Use this exact message when arranging any required
provider template approval. Credentials stay on the server, never in browser code.
Provider API reference: https://www.twilio.com/docs/messaging/api/message-resource

## Status and limitations

Order tickets show queued, sending, accepted by provider, failed, not configured,
or unknown. **Accepted is not proof of delivery to the phone.** This local setup
has no public delivery webhook. Check the provider dashboard for final delivery.
Failed/unknown messages are not automatically retried, to avoid duplicate texts.
An interrupted send becomes unknown on server restart. Pending work resumes.
Staff should contact the customer directly if a message failed or remains unknown.

Admin **Still preparing** clears the ready timestamp and records the reversal in
history. Pending notifications are cancelled. Already sending/accepted SMS cannot
be recalled. Marking ready again does not send another accepted/unknown message.
Run a single API worker (the existing deployment default).

## Existing installation upgrade

Stop the launcher. Back up first (Setup creates a database backup), then run the
updated **Setup TOSS POS.cmd** to install dependencies, migrate, and rebuild.
It does not reset menu edits. To apply the new poster, open PowerShell in the
project folder and run:

```powershell
cd backend
& ..\.venv\Scripts\python.exe -m app.toss_menu --update-existing
```

Then reopen Run TOSS POS. The explicit menu update preserves past order snapshots.
