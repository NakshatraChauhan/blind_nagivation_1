from __future__ import annotations

from typing import Tuple

from core.voice_engine import VoiceEngine

try:
    from jnius import autoclass
except Exception:  # pragma: no cover
    autoclass = None

Coordinate = Tuple[float, float]


class EmergencyHandler:
    """Handles long-press emergency flow and SMS dispatch with GPS coordinates."""

    def __init__(self, voice_engine: VoiceEngine):
        self.voice_engine = voice_engine

    def activate(self, location: Coordinate, contact_number: str) -> bool:
        lat, lon = location
        message = f"Emergency alert from BlindNav AI. Location: https://maps.google.com/?q={lat:.6f},{lon:.6f}"
        sent = self._send_sms(contact_number, message)

        if sent:
            self.voice_engine.speak_alert("Emergency message sent with your GPS coordinates.", emergency=True)
        else:
            self.voice_engine.speak_alert("Emergency mode activated, but SMS could not be sent.", emergency=True)
        return sent

    @staticmethod
    def _send_sms(phone: str, message: str) -> bool:
        if autoclass is None:
            return False
        try:
            SmsManager = autoclass("android.telephony.SmsManager")
            sms_manager = SmsManager.getDefault()
            sms_manager.sendTextMessage(phone, None, message, None, None)
            return True
        except Exception:
            return False
