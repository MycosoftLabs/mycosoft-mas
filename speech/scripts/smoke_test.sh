#!/bin/bash
# Smoke test for speech gateway

set -e

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8002}"
TEST_AUDIO="${TEST_AUDIO:-test_audio.webm}"

echo "🧪 MYCA Speech Gateway Smoke Test"
echo "=================================="
echo ""

# Check if gateway is running
echo "1. Checking gateway health..."
HEALTH_RESPONSE=$(curl -s "${GATEWAY_URL}/health")
if echo "$HEALTH_RESPONSE" | grep -q "ok"; then
    echo "✅ Gateway is healthy"
    echo "   Response: $HEALTH_RESPONSE"
else
    echo "❌ Gateway health check failed"
    echo "   Response: $HEALTH_RESPONSE"
    exit 1
fi
echo ""

# Check available voices
echo "2. Checking available voices..."
VOICES_RESPONSE=$(curl -s "${GATEWAY_URL}/voices")
if echo "$VOICES_RESPONSE" | grep -q "voices"; then
    echo "✅ Voices endpoint working"
    echo "   Response: $VOICES_RESPONSE"
else
    echo "❌ Voices endpoint failed"
    exit 1
fi
echo ""

# Test speech turn (if test audio exists)
if [ -f "$TEST_AUDIO" ]; then
    echo "3. Testing speech turn with audio file..."
    RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/speech/turn" \
        -F "audio=@${TEST_AUDIO}" \
        -F "provider=openai" \
        -F "voice=alloy" \
        -F "store_audio=false" \
        -F "wake_word_enabled=false")
    
    if echo "$RESPONSE" | grep -q "request_id"; then
        echo "✅ Speech turn successful"
        echo "   Response: $RESPONSE"
        
        # Extract request_id
        REQUEST_ID=$(echo "$RESPONSE" | grep -o '"request_id":"[^"]*' | cut -d'"' -f4)
        echo "   Request ID: $REQUEST_ID"
        
        # Check for transcript
        if echo "$RESPONSE" | grep -q "transcript"; then
            echo "✅ Transcript received"
        else
            echo "⚠️  No transcript in response"
        fi
        
        # Check for TTS audio
        if echo "$RESPONSE" | grep -q "tts_audio_base64"; then
            echo "✅ TTS audio received"
        else
            echo "⚠️  No TTS audio in response"
        fi
    else
        echo "❌ Speech turn failed"
        echo "   Response: $RESPONSE"
        exit 1
    fi
else
    echo "⚠️  Test audio file not found: $TEST_AUDIO"
    echo "   Skipping speech turn test"
    echo "   Create a test audio file or record one to test full pipeline"
fi
echo ""

echo "✅ Smoke test completed successfully!"
echo ""
echo "Next steps:"
echo "1. Start the UI: cd speech/ui && npm install && npm run dev"
echo "2. Open http://localhost:3000"
echo "3. Test push-to-talk functionality"
