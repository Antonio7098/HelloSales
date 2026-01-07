#!/usr/bin/env python3
"""Minimal test to verify voice handler is reachable."""
import os

os.environ["CLERK_DEV_BYPASS_ENABLED"] = "true"
os.environ["ENVIRONMENT"] = "development"
os.environ["LLM_PROVIDER"] = "stub"
os.environ["STT_PROVIDER"] = "stub"
os.environ["STUB_LLM_FORCE_STREAM_TEXT"] = "Hello, how can I help you?"
os.environ["STUB_LLM_STREAM_MODE"] = "normal"
os.environ["STUB_STT_FORCE_TRANSCRIPT"] = "Hello, I want to practice my presentation skills"
os.environ["STUB_STT_FORCE_DURATION_MS"] = "1500"

from fastapi.testclient import TestClient

from app.ai.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
from app.config import get_settings
from app.main import app

get_settings.cache_clear()
get_stt_provider.cache_clear()
get_llm_provider.cache_clear()
get_tts_provider.cache_clear()

client = TestClient(app)

print("Connecting to websocket...")
with client.websocket_connect("/ws") as websocket:
    print("Connected!")

    # Auth
    print("Authenticating...")
    websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
    auth_resp = websocket.receive_json()
    print(f"Auth response: {auth_resp['type']}")

    # Drain auth messages
    websocket.receive_json()

    # Set pipeline mode
    print("Setting pipeline mode...")
    websocket.send_json({"type": "settings.setPipelineMode", "payload": {"mode": "fast"}})

    # Drain until we get pipelineModeSet
    for _ in range(10):
        msg = websocket.receive_json()
        print(f"Received: {msg['type']}")
        if msg.get("type") == "settings.pipelineModeSet":
            break

    # Start voice recording
    print("\nSending voice.start...")
    websocket.send_json({
        "type": "voice.start",
        "payload": {
            "sessionId": None,
            "format": "webm",
        },
    })

    # Wait for recording status
    print("Waiting for recording status...")
    for _ in range(10):
        msg = websocket.receive_json()
        print(f"Received: {msg['type']}")
        if msg.get("type") == "status.update" and msg.get("payload", {}).get("status") == "recording":
            print("Recording started!")
            break

    # Send audio chunk
    print("\nSending voice.chunk...")
    websocket.send_json({
        "type": "voice.chunk",
        "payload": {
            "data": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQF",
        },
    })

    # End recording
    print("\nSending voice.end...")
    websocket.send_json({
        "type": "voice.end",
        "payload": {
            "messageId": "test-message-id",
        },
    })

    # Wait for voice.complete
    print("Waiting for voice.complete (max 30 seconds)...")
    for i in range(100):
        try:
            msg = websocket.receive_json()
            msg_type = msg.get("type")
            print(f"[{i}] Received: {msg_type}")
            if msg_type == "voice.complete":
                print("\n✓ SUCCESS! Received voice.complete")
                print(f"Payload keys: {list(msg.get('payload', {}).keys())}")
                break
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            break
    else:
        print("\n✗ FAILED: Did not receive voice.complete within timeout")

print("\nTest complete. Check /tmp/debug_voice_handler.log for backend logs.")
