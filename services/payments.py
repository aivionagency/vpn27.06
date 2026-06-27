import hashlib
import hmac
from typing import Optional

from config import config


class PaymentsService:
    """Tribute payments: top-up link + webhook signature verification + parsing."""

    def get_topup_link(self, user_telegram_id: int) -> str:
        # Single Tribute donation link; the user picks the amount inside Tribute.
        # Attribution happens later by telegram_user_id from the webhook payload.
        return config.tribute_topup_url

    def verify_signature(self, raw_body: bytes, signature_header: Optional[str]) -> bool:
        """Verify the `trbt-signature` header: HMAC-SHA256(raw_body, api_key)."""
        if not signature_header or not config.tribute_api_key:
            return False
        expected = hmac.new(
            config.tribute_api_key.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        # constant-time comparison; tolerate a hex digest with different casing
        return hmac.compare_digest(expected, signature_header.strip().lower())

    @staticmethod
    def build_idempotency_key(telegram_user_id, amount_kopecks, created_at: str) -> str:
        raw = f"{telegram_user_id}:{amount_kopecks}:{created_at}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def parse_donation(self, envelope: dict) -> dict:
        """Extract the fields we need from a newDonation webhook envelope.

        Envelope: {name, created_at, sent_at, payload}
        payload: {amount(kopecks), currency, anonymously, telegram_user_id, ...}
        """
        payload = envelope.get("payload") or {}
        return {
            "event_name": envelope.get("name"),
            "created_at": envelope.get("created_at"),
            "amount_kopecks": payload.get("amount"),
            "currency": payload.get("currency"),
            "anonymously": payload.get("anonymously", False),
            "telegram_user_id": payload.get("telegram_user_id"),
            "telegram_username": payload.get("telegram_username"),
        }

    @staticmethod
    def is_donation_event(event_name: Optional[str]) -> bool:
        if not event_name:
            return False
        # accept both "newDonation" and "new_donation"
        return event_name.lower().replace("_", "") == "newdonation"
