import json
import unittest
from unittest.mock import patch

from app.whatsapp import WhatsAppNotifier, format_daily_summary_message


class _FakeResponse:
    def __init__(self, status: int = 200, body: str = 'ok') -> None:
        self.status = status
        self._body = body.encode('utf-8')

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


class WhatsAppTests(unittest.TestCase):
    def test_message_contains_important_daily_fields(self) -> None:
        analytics = {
            'totalReservations': 12,
            'totalCovers': 30,
            'completedReservations': 8,
            'cancelledReservations': 2,
            'noShowReservations': 1,
            'waitlistWaiting': 3,
            'waitlistPromoted': 2,
        }
        message = format_daily_summary_message('resto-main', '2026-05-12', analytics)
        self.assertIn('Total reservations: 12', message)
        self.assertIn('Total covers: 30', message)
        self.assertIn('Waitlist waiting: 3', message)

    @patch('urllib.request.urlopen')
    def test_send_daily_summary_posts_payload(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(200, 'queued')
        notifier = WhatsAppNotifier('https://example.com/webhook', recipient='+971500000000')
        analytics = {'totalReservations': 1, 'totalCovers': 2}

        result = notifier.send_daily_summary('resto-main', '2026-05-12', analytics)

        self.assertTrue(result['ok'])
        self.assertEqual(result['statusCode'], 200)

        request = mock_urlopen.call_args[0][0]
        payload = json.loads(request.data.decode('utf-8'))
        self.assertEqual(payload['channel'], 'whatsapp')
        self.assertEqual(payload['to'], '+971500000000')
        self.assertEqual(payload['restaurantId'], 'resto-main')


if __name__ == '__main__':
    unittest.main()
