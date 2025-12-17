# Twilio Integration Guide

## Overview

MYCA MAS now supports **Twilio SMS and Voice** capabilities, allowing MYCA to send text messages, make phone calls, and deliver voice messages (text-to-speech) via Twilio's API.

## Prerequisites

1. **Twilio Account**: Sign up at https://www.twilio.com
2. **Twilio Phone Number**: Purchase a phone number from Twilio Console
3. **Account SID & Auth Token**: Found in Twilio Console → Account → API Credentials

## Configuration

### Step 1: Get Twilio Credentials

1. Log in to https://console.twilio.com
2. Navigate to **Account** → **API Credentials**
3. Copy:
   - **Account SID** (starts with `AC...`)
   - **Auth Token** (click "View" to reveal)
4. Navigate to **Phone Numbers** → **Manage** → **Buy a number**
5. Purchase a number (E.164 format, e.g., `+12025551234`)

### Step 2: Add to `.env.local`

```bash
# TWILIO (SMS/Phone Integration)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+12025551234
```

### Step 3: Restart MAS Orchestrator

```bash
docker-compose restart mas-orchestrator
```

## API Endpoints

### 1. Send SMS

**Endpoint**: `POST /twilio/sms/send`

**Request Body**:
```json
{
  "to": "+12025551234",
  "message": "Hello from MYCA! This is a test message."
}
```

**Response**:
```json
{
  "status": "success",
  "sid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "to": "+12025551234",
  "from": "+12025551234"
}
```

**Example (curl)**:
```bash
curl -X POST http://localhost:8001/twilio/sms/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+12025551234",
    "message": "Hello from MYCA!"
  }'
```

### 2. Send Voice Message (TTS Call)

**Endpoint**: `POST /twilio/voice/message`

**Request Body**:
```json
{
  "to": "+12025551234",
  "message": "Hello, this is MYCA speaking. I can deliver voice messages via Twilio.",
  "voice": "alice"
}
```

**Voice Options**:
- `alice` (default) - Female, clear, professional
- `man` - Male voice
- `woman` - Female voice

**Response**:
```json
{
  "status": "success",
  "sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "to": "+12025551234",
  "message": "Hello, this is MYCA speaking..."
}
```

**Example (curl)**:
```bash
curl -X POST http://localhost:8001/twilio/voice/message \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+12025551234",
    "message": "Hello from MYCA voice assistant!",
    "voice": "alice"
  }'
```

### 3. Make Outbound Call

**Endpoint**: `POST /twilio/voice/call`

**Request Body**:
```json
{
  "to": "+12025551234",
  "twiml_url": "https://your-server.com/twiml/voice.xml"
}
```

**Note**: You must host a TwiML XML file that defines what happens during the call. Example TwiML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Hello, this is MYCA calling.</Say>
    <Gather numDigits="1" action="/twilio/handle-input" method="POST">
        <Say voice="alice">Press 1 to speak with an agent, or press 2 to leave a message.</Say>
    </Gather>
</Response>
```

**Response**:
```json
{
  "status": "success",
  "sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "to": "+12025551234",
  "from": "+12025551234"
}
```

### 4. Get Message/Call Status

**Endpoint**: `GET /twilio/status/{message_sid}`

**Example**:
```bash
curl http://localhost:8001/twilio/status/SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Response**:
```json
{
  "sid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "status": "delivered",
  "to": "+12025551234",
  "from": "+12025551234",
  "body": "Hello from MYCA!",
  "date_sent": "2025-12-17T10:30:00Z"
}
```

### 5. Check Configuration

**Endpoint**: `GET /twilio/config`

**Example**:
```bash
curl http://localhost:8001/twilio/config
```

**Response**:
```json
{
  "configured": true,
  "has_account_sid": true,
  "has_auth_token": true,
  "has_phone_number": true
}
```

## n8n Integration

### Example Workflow: MYCA Voice Assistant → SMS Notification

1. **Webhook Trigger** (receives voice command)
2. **HTTP Request** → `POST http://mas-orchestrator:8000/voice/orchestrator/chat`
   - Body: `{"message": "{{ $json.body.command }}", "want_audio": false}`
3. **HTTP Request** → `POST http://mas-orchestrator:8000/twilio/sms/send`
   - Body:
     ```json
     {
       "to": "{{ $json.body.phone_number }}",
       "message": "{{ $json.response_text }}"
     }
     ```
4. **n8n Data Table** → Log interaction

### Example Workflow: Alert → Twilio Voice Call

1. **Cron Trigger** (every hour)
2. **HTTP Request** → Check system status
3. **IF Node** → If alert condition met
4. **HTTP Request** → `POST http://mas-orchestrator:8000/twilio/voice/message`
   - Body:
     ```json
     {
       "to": "+12025551234",
       "message": "Alert: System status check failed. Please investigate.",
       "voice": "alice"
     }
     ```

## Voice Integration with ElevenLabs

Combine Twilio voice calls with ElevenLabs premium TTS:

1. **Generate audio** via ElevenLabs proxy (`/voice/orchestrator/speech`)
2. **Host audio file** (e.g., S3, CDN, or local server)
3. **Create TwiML** that plays the audio:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
       <Play>https://your-server.com/audio/myca_response.mp3</Play>
   </Response>
   ```
4. **Call** `/twilio/voice/call` with the TwiML URL

## Error Handling

All endpoints return structured errors:

```json
{
  "detail": "Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER"
}
```

**Common Errors**:
- `503`: Twilio not configured (missing env vars)
- `400`: Missing required fields (`to`, `message`, etc.)
- `500`: Twilio API error (check logs for details)

## Security Best Practices

1. **Never commit** `.env.local` to git
2. **Rotate** Twilio Auth Token regularly
3. **Use environment variables** in production (not `.env.local`)
4. **Validate phone numbers** before sending (E.164 format)
5. **Rate limit** SMS/voice endpoints to prevent abuse
6. **Monitor usage** in Twilio Console to avoid unexpected charges

## Pricing

Twilio pricing (as of Dec 2024):
- **SMS**: ~$0.0075 per message (US)
- **Voice Calls**: ~$0.013 per minute (US)
- **Free Trial**: $15.50 credit for new accounts

**Tip**: Use Twilio for production alerts and critical notifications. For development/testing, use local TTS or mock endpoints.

## Testing

### Test SMS
```bash
curl -X POST http://localhost:8001/twilio/sms/send \
  -H "Content-Type: application/json" \
  -d '{"to": "+12025551234", "message": "Test from MYCA"}'
```

### Test Voice Message
```bash
curl -X POST http://localhost:8001/twilio/voice/message \
  -H "Content-Type: application/json" \
  -d '{"to": "+12025551234", "message": "Hello, this is MYCA.", "voice": "alice"}'
```

### Check Configuration
```bash
curl http://localhost:8001/twilio/config
```

## Troubleshooting

### "Twilio not configured"
- Verify `.env.local` has all three variables set
- Restart `mas-orchestrator` container
- Check logs: `docker logs mycosoft-mas-mas-orchestrator-1 --tail 50`

### "Invalid phone number"
- Ensure phone number is in E.164 format: `+[country code][number]`
- Example: `+12025551234` (US), `+442071234567` (UK)

### "Authentication failed"
- Verify Account SID and Auth Token are correct
- Check Twilio Console → Account → API Credentials
- Ensure no extra spaces in `.env.local`

### "Call failed"
- Verify TwiML URL is publicly accessible (not localhost)
- Check TwiML syntax is valid XML
- Review Twilio Console → Monitor → Logs → Calls

## References

- Twilio API Docs: https://www.twilio.com/docs/voice/api
- Twilio SMS API: https://www.twilio.com/docs/sms/api
- TwiML Reference: https://www.twilio.com/docs/voice/twiml
- E.164 Format: https://en.wikipedia.org/wiki/E.164
