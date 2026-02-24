from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime


class WhatsAppNotifier:
    def __init__(self, webhook_url: str | None, recipient: str | None = None, timeout_seconds: int = 10) -> None:
        self.webhook_url = (webhook_url or "").strip()
        self.recipient = (recipient or "").strip() or None
        self.timeout_seconds = timeout_seconds

    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def send_daily_summary(self, restaurant_id: str, date: str, analytics: dict) -> dict:
        if not self.enabled():
            raise ValueError("WhatsApp webhook is not configured")

        message = format_daily_summary_message(restaurant_id, date, analytics)
        payload = {
            "channel": "whatsapp",
            "to": self.recipient,
            "message": message,
            "restaurantId": restaurant_id,
            "date": date,
            "analytics": analytics,
        }

        request = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
                return {
                    "ok": 200 <= response.status < 300,
                    "statusCode": int(response.status),
                    "response": response_body,
                    "message": message,
                }
        except urllib.error.HTTPError as exc:
            return {
                "ok": False,
                "statusCode": int(exc.code),
                "response": exc.read().decode("utf-8", errors="replace"),
                "message": message,
            }


def format_daily_summary_message(restaurant_id: str, date: str, analytics: dict) -> str:
    total = analytics.get("totalReservations", 0)
    covers = analytics.get("totalCovers", 0)
    completed = analytics.get("completedReservations", 0)
    cancelled = analytics.get("cancelledReservations", 0)
    no_show = analytics.get("noShowReservations", 0)
    waiting = analytics.get("waitlistWaiting", 0)
    promoted = analytics.get("waitlistPromoted", 0)

    return (
        f"🍽️ Daily Reservation Summary\n"
        f"Restaurant: {restaurant_id}\n"
        f"Date: {date}\n"
        f"Updated (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Total reservations: {total}\n"
        f"Total covers: {covers}\n"
        f"Completed: {completed}\n"
        f"Cancelled: {cancelled}\n"
        f"No-show: {no_show}\n"
        f"Waitlist waiting: {waiting}\n"
        f"Waitlist promoted: {promoted}"
    )
