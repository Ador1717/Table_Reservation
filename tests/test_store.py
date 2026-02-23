import tempfile
import unittest
from pathlib import Path

from app.reservation_store import ReservationStore


class ReservationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tmpdir.name) / "test.db"
        self.store = ReservationStore(str(db_path))

    def tearDown(self) -> None:
        self.tmpdir.cleanup()



    def test_create_and_list_admin_users(self) -> None:
        self.store.create_admin_user('staff1', 'pw-1')
        users = self.store.list_admin_users()
        self.assertTrue(any(u['username'] == 'staff1' and u['role'] == 'admin' for u in users))

        with self.assertRaises(ValueError):
            self.store.create_admin_user('staff1', 'pw-1')

    def test_admin_user_authentication(self) -> None:
        self.store.ensure_admin_user('admin1', 'pw-123', role='admin')
        auth = self.store.authenticate_admin_user('admin1', 'pw-123')
        self.assertIsNotNone(auth)
        self.assertEqual(auth['username'], 'admin1')
        self.assertEqual(auth['role'], 'admin')
        self.assertIsNone(self.store.authenticate_admin_user('admin1', 'wrong'))

    def test_create_and_update_reservation(self) -> None:
        created = self.store.create_reservation(
            {
                "restaurantId": "resto-main",
                "guestName": "Alice",
                "partySize": 2,
                "reservationAt": "2026-01-10T18:00:00",
            }
        )
        self.assertEqual(created.status, "pending")

        updated = self.store.update_reservation(created.id, {"status": "confirmed", "notes": "Birthday"})
        self.assertEqual(updated.status, "confirmed")
        self.assertEqual(updated.notes, "Birthday")

    def test_list_reservations_filters(self) -> None:
        self.store.create_reservation(
            {
                "restaurantId": "resto-main",
                "guestName": "Main 1",
                "partySize": 2,
                "reservationAt": "2026-01-10T18:00:00",
            }
        )
        self.store.create_reservation(
            {
                "restaurantId": "resto-other",
                "guestName": "Other 1",
                "partySize": 2,
                "reservationAt": "2026-01-10T18:30:00",
            }
        )

        filtered = self.store.list_reservations(restaurant_id="resto-main", date="2026-01-10")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].guest_name, "Main 1")

    def test_capacity_limit(self) -> None:
        for i in range(4):
            self.store.create_reservation(
                {
                    "restaurantId": "resto-main",
                    "guestName": f"Guest {i}",
                    "partySize": 10,
                    "reservationAt": "2026-01-10T19:00:00",
                }
            )

        with self.assertRaises(ValueError):
            self.store.create_reservation(
                {
                    "restaurantId": "resto-main",
                    "guestName": "Overflow",
                    "partySize": 1,
                    "reservationAt": "2026-01-10T19:00:00",
                }
            )

    def test_waitlist_promotes_when_reservation_cancelled(self) -> None:
        reservation = self.store.create_reservation(
            {
                "restaurantId": "resto-main",
                "guestName": "Large Group",
                "partySize": 40,
                "reservationAt": "2026-01-10T20:00:00",
            }
        )
        waitlist_entry = self.store.add_waitlist_entry(
            {
                "restaurantId": "resto-main",
                "guestName": "Wait Guest",
                "partySize": 2,
                "desiredAt": "2026-01-10T20:00:00",
            }
        )

        self.store.cancel_reservation(reservation.id)

        reservations = self.store.list_reservations(restaurant_id="resto-main", date="2026-01-10")
        promoted = [item for item in reservations if item.guest_name == "Wait Guest"]
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0].status, "pending")
        self.assertIn(str(waitlist_entry.id), promoted[0].notes)

        waiting_entries = self.store.list_waitlist_entries(restaurant_id="resto-main", date="2026-01-10")
        self.assertEqual(waiting_entries, [])


    def test_daily_analytics(self) -> None:
        self.store.create_reservation(
            {
                "restaurantId": "resto-main",
                "guestName": "Comp",
                "partySize": 3,
                "reservationAt": "2026-01-11T18:00:00",
                "status": "completed",
            }
        )
        self.store.create_reservation(
            {
                "restaurantId": "resto-main",
                "guestName": "Cancel",
                "partySize": 2,
                "reservationAt": "2026-01-11T19:00:00",
                "status": "cancelled",
            }
        )
        self.store.create_reservation(
            {
                "restaurantId": "resto-main",
                "guestName": "NoShow",
                "partySize": 4,
                "reservationAt": "2026-01-11T20:00:00",
                "status": "no_show",
            }
        )
        self.store.add_waitlist_entry(
            {
                "restaurantId": "resto-main",
                "guestName": "Waiting",
                "partySize": 2,
                "desiredAt": "2026-01-11T20:00:00",
            }
        )

        analytics = self.store.get_daily_analytics("resto-main", "2026-01-11")

        self.assertEqual(analytics["totalReservations"], 3)
        self.assertEqual(analytics["totalCovers"], 9)
        self.assertEqual(analytics["completedReservations"], 1)
        self.assertEqual(analytics["cancelledReservations"], 1)
        self.assertEqual(analytics["noShowReservations"], 1)
        self.assertEqual(analytics["waitlistWaiting"], 1)
        self.assertEqual(analytics["waitlistPromoted"], 0)
        self.assertAlmostEqual(analytics["cancellationRate"], 1 / 3, places=4)
        self.assertAlmostEqual(analytics["noShowRate"], 1 / 3, places=4)


if __name__ == "__main__":
    unittest.main()
