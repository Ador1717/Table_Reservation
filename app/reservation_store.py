from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from app.auth import hash_password, verify_password


ALLOWED_STATUSES = {"pending", "confirmed", "seated", "completed", "cancelled", "no_show"}
ACTIVE_STATUSES = {"pending", "confirmed", "seated"}
@dataclass
class Reservation:
    id: int
    restaurant_id: str
    guest_name: str
    guest_phone: str | None
    guest_email: str | None
    party_size: int
    reservation_at: str
    status: str
    notes: str | None
    created_at: str


@dataclass
class WaitlistEntry:
    id: int
    restaurant_id: str
    guest_name: str
    guest_phone: str | None
    guest_email: str | None
    party_size: int
    desired_at: str
    status: str
    created_at: str
    promoted_reservation_id: int | None


class ReservationStore:
    def __init__(self, db_path: str = "data/reservations.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    restaurant_id TEXT NOT NULL,
                    guest_name TEXT NOT NULL,
                    guest_phone TEXT,
                    guest_email TEXT,
                    party_size INTEGER NOT NULL CHECK(party_size > 0),
                    reservation_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS waitlist_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    restaurant_id TEXT NOT NULL,
                    guest_name TEXT NOT NULL,
                    guest_phone TEXT,
                    guest_email TEXT,
                    party_size INTEGER NOT NULL CHECK(party_size > 0),
                    desired_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    promoted_reservation_id INTEGER,
                    FOREIGN KEY(promoted_reservation_id) REFERENCES reservations(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )


    def ensure_admin_user(self, username: str, password: str, role: str = "admin") -> None:
        created_at = datetime.utcnow().isoformat()
        with self._conn() as conn:
            existing = conn.execute("SELECT id FROM admin_users WHERE username = ?", (username,)).fetchone()
            if existing:
                return
            conn.execute(
                "INSERT INTO admin_users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, hash_password(password), role, created_at),
            )

    def authenticate_admin_user(self, username: str, password: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT username, password_hash, role FROM admin_users WHERE username = ?",
                (username,),
            ).fetchone()

        if not row:
            return None
        if not verify_password(password, row["password_hash"]):
            return None

        return {"username": row["username"], "role": row["role"]}


    def create_admin_user(self, username: str, password: str) -> None:
        created_at = datetime.utcnow().isoformat()
        with self._conn() as conn:
            existing = conn.execute("SELECT id FROM admin_users WHERE username = ?", (username,)).fetchone()
            if existing:
                raise ValueError("Username already exists")
            conn.execute(
                "INSERT INTO admin_users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, hash_password(password), "admin", created_at),
            )

    def list_admin_users(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT username, role, created_at FROM admin_users ORDER BY created_at ASC, username ASC"
            ).fetchall()
        return [{"username": row["username"], "role": row["role"], "createdAt": row["created_at"]} for row in rows]

    def get_availability(self, restaurant_id: str, date_str: str, party_size: int) -> list[dict]:
        date_start = datetime.fromisoformat(f"{date_str}T12:00:00")
        slots = []
        for start_hour, end_hour in [(12, 15), (18, 22)]:
            current = date_start.replace(hour=start_hour, minute=0)
            end = date_start.replace(hour=end_hour, minute=0)
            while current <= end:
                start_time = current.isoformat()
                end_time = (current + timedelta(hours=2)).isoformat()
                available = self._slot_is_available(restaurant_id, start_time, party_size)
                slots.append({"startTime": start_time, "endTime": end_time, "available": available})
                current += timedelta(minutes=30)
        return slots

    def _slot_is_available(self, restaurant_id: str, reservation_at: str, party_size: int) -> bool:
        max_covers = 40
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(party_size), 0) AS used_covers
                FROM reservations
                WHERE restaurant_id = ?
                  AND reservation_at = ?
                  AND status IN ('pending', 'confirmed', 'seated')
                """,
                (restaurant_id, reservation_at),
            ).fetchone()
        used = int(row["used_covers"])
        return used + party_size <= max_covers

    def create_reservation(self, payload: dict) -> Reservation:
        status = payload.get("status", "pending")
        if status not in ALLOWED_STATUSES:
            raise ValueError("Invalid reservation status")

        party_size = int(payload["partySize"])
        if not self._slot_is_available(payload["restaurantId"], payload["reservationAt"], party_size):
            raise ValueError("Selected slot is no longer available")

        created_at = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO reservations (
                    restaurant_id, guest_name, guest_phone, guest_email,
                    party_size, reservation_at, status, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["restaurantId"],
                    payload["guestName"],
                    payload.get("guestPhone"),
                    payload.get("guestEmail"),
                    party_size,
                    payload["reservationAt"],
                    status,
                    payload.get("notes"),
                    created_at,
                ),
            )
            row = conn.execute("SELECT * FROM reservations WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._to_reservation(row)

    def list_reservations(self, restaurant_id: str | None = None, date: str | None = None) -> list[Reservation]:
        query = "SELECT * FROM reservations"
        clauses = []
        params: list[str] = []

        if restaurant_id:
            clauses.append("restaurant_id = ?")
            params.append(restaurant_id)
        if date:
            clauses.append("reservation_at >= ? AND reservation_at < ?")
            params.append(f"{date}T00:00:00")
            params.append(f"{date}T23:59:59")

        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY reservation_at ASC, id ASC"

        with self._conn() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._to_reservation(row) for row in rows]

    def update_reservation(self, reservation_id: int, payload: dict) -> Reservation:
        if "status" in payload and payload["status"] not in ALLOWED_STATUSES:
            raise ValueError("Invalid reservation status")

        with self._conn() as conn:
            current_row = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
            if not current_row:
                raise KeyError("Reservation not found")

            status = payload.get("status", current_row["status"])
            notes = payload.get("notes", current_row["notes"])
            conn.execute("UPDATE reservations SET status = ?, notes = ? WHERE id = ?", (status, notes, reservation_id))
            updated_row = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()

        previous = self._to_reservation(current_row)
        updated = self._to_reservation(updated_row)
        if self._slot_released(previous, updated):
            self.promote_waitlist_for_slot(updated.restaurant_id, updated.reservation_at)
        return updated

    def cancel_reservation(self, reservation_id: int) -> None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
            if not row:
                raise KeyError("Reservation not found")
            conn.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (reservation_id,))

        cancelled = self._to_reservation(row)
        if cancelled.status in ACTIVE_STATUSES:
            self.promote_waitlist_for_slot(cancelled.restaurant_id, cancelled.reservation_at)

    def add_waitlist_entry(self, payload: dict) -> WaitlistEntry:
        party_size = int(payload["partySize"])
        created_at = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO waitlist_entries (
                    restaurant_id, guest_name, guest_phone, guest_email,
                    party_size, desired_at, status, created_at, promoted_reservation_id
                ) VALUES (?, ?, ?, ?, ?, ?, 'waiting', ?, NULL)
                """,
                (
                    payload["restaurantId"],
                    payload["guestName"],
                    payload.get("guestPhone"),
                    payload.get("guestEmail"),
                    party_size,
                    payload["desiredAt"],
                    created_at,
                ),
            )
            row = conn.execute("SELECT * FROM waitlist_entries WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._to_waitlist_entry(row)

    def list_waitlist_entries(self, restaurant_id: str | None = None, date: str | None = None) -> list[WaitlistEntry]:
        query = "SELECT * FROM waitlist_entries"
        clauses = ["status = 'waiting'"]
        params: list[str] = []

        if restaurant_id:
            clauses.append("restaurant_id = ?")
            params.append(restaurant_id)
        if date:
            clauses.append("desired_at >= ? AND desired_at < ?")
            params.append(f"{date}T00:00:00")
            params.append(f"{date}T23:59:59")

        query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY desired_at ASC, created_at ASC"

        with self._conn() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._to_waitlist_entry(row) for row in rows]


    def get_daily_analytics(self, restaurant_id: str, date: str) -> dict:
        start = f"{date}T00:00:00"
        end = f"{date}T23:59:59"

        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_reservations,
                    COALESCE(SUM(party_size), 0) AS total_covers,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_count,
                    SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END) AS no_show_count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_count
                FROM reservations
                WHERE restaurant_id = ?
                  AND reservation_at >= ?
                  AND reservation_at <= ?
                """,
                (restaurant_id, start, end),
            ).fetchone()

            waitlist_row = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'waiting' THEN 1 ELSE 0 END) AS waiting_count,
                    SUM(CASE WHEN status = 'promoted' THEN 1 ELSE 0 END) AS promoted_count
                FROM waitlist_entries
                WHERE restaurant_id = ?
                  AND desired_at >= ?
                  AND desired_at <= ?
                """,
                (restaurant_id, start, end),
            ).fetchone()

        total_reservations = int(row["total_reservations"] or 0)
        total_covers = int(row["total_covers"] or 0)
        cancelled_count = int(row["cancelled_count"] or 0)
        no_show_count = int(row["no_show_count"] or 0)
        completed_count = int(row["completed_count"] or 0)
        waiting_count = int(waitlist_row["waiting_count"] or 0)
        promoted_count = int(waitlist_row["promoted_count"] or 0)

        cancellation_rate = (cancelled_count / total_reservations) if total_reservations else 0.0
        no_show_rate = (no_show_count / total_reservations) if total_reservations else 0.0

        return {
            "restaurantId": restaurant_id,
            "date": date,
            "totalReservations": total_reservations,
            "totalCovers": total_covers,
            "completedReservations": completed_count,
            "cancelledReservations": cancelled_count,
            "noShowReservations": no_show_count,
            "cancellationRate": round(cancellation_rate, 4),
            "noShowRate": round(no_show_rate, 4),
            "waitlistWaiting": waiting_count,
            "waitlistPromoted": promoted_count,
        }

    def promote_waitlist_for_slot(self, restaurant_id: str, reservation_at: str) -> list[Reservation]:
        promoted: list[Reservation] = []

        while True:
            with self._conn() as conn:
                waiting_rows = conn.execute(
                    """
                    SELECT * FROM waitlist_entries
                    WHERE restaurant_id = ?
                      AND desired_at = ?
                      AND status = 'waiting'
                    ORDER BY created_at ASC, id ASC
                    """,
                    (restaurant_id, reservation_at),
                ).fetchall()

                chosen = None
                for candidate in waiting_rows:
                    if self._slot_is_available(restaurant_id, reservation_at, int(candidate["party_size"])):
                        chosen = candidate
                        break

                if not chosen:
                    break

                created_at = datetime.utcnow().isoformat()
                notes = f"Auto-promoted from waitlist entry #{chosen['id']}"
                reservation_cur = conn.execute(
                    """
                    INSERT INTO reservations (
                        restaurant_id, guest_name, guest_phone, guest_email,
                        party_size, reservation_at, status, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                    """,
                    (
                        chosen["restaurant_id"],
                        chosen["guest_name"],
                        chosen["guest_phone"],
                        chosen["guest_email"],
                        int(chosen["party_size"]),
                        chosen["desired_at"],
                        notes,
                        created_at,
                    ),
                )
                reservation_id = reservation_cur.lastrowid
                conn.execute(
                    "UPDATE waitlist_entries SET status = 'promoted', promoted_reservation_id = ? WHERE id = ?",
                    (reservation_id, chosen["id"]),
                )
                reservation_row = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
            promoted.append(self._to_reservation(reservation_row))

        return promoted

    @staticmethod
    def _slot_released(previous: Reservation, updated: Reservation) -> bool:
        return previous.status in ACTIVE_STATUSES and updated.status not in ACTIVE_STATUSES

    @staticmethod
    def _to_reservation(row: sqlite3.Row) -> Reservation:
        return Reservation(
            id=row["id"],
            restaurant_id=row["restaurant_id"],
            guest_name=row["guest_name"],
            guest_phone=row["guest_phone"],
            guest_email=row["guest_email"],
            party_size=row["party_size"],
            reservation_at=row["reservation_at"],
            status=row["status"],
            notes=row["notes"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_waitlist_entry(row: sqlite3.Row) -> WaitlistEntry:
        return WaitlistEntry(
            id=row["id"],
            restaurant_id=row["restaurant_id"],
            guest_name=row["guest_name"],
            guest_phone=row["guest_phone"],
            guest_email=row["guest_email"],
            party_size=row["party_size"],
            desired_at=row["desired_at"],
            status=row["status"],
            created_at=row["created_at"],
            promoted_reservation_id=row["promoted_reservation_id"],
        )


def reservation_to_dict(reservation: Reservation) -> dict:
    return {
        "id": str(reservation.id),
        "restaurantId": reservation.restaurant_id,
        "guestName": reservation.guest_name,
        "guestPhone": reservation.guest_phone,
        "guestEmail": reservation.guest_email,
        "partySize": reservation.party_size,
        "reservationAt": reservation.reservation_at,
        "status": reservation.status,
        "notes": reservation.notes,
    }


def waitlist_entry_to_dict(entry: WaitlistEntry) -> dict:
    return {
        "id": str(entry.id),
        "restaurantId": entry.restaurant_id,
        "guestName": entry.guest_name,
        "guestPhone": entry.guest_phone,
        "guestEmail": entry.guest_email,
        "partySize": entry.party_size,
        "desiredAt": entry.desired_at,
        "status": entry.status,
        "promotedReservationId": str(entry.promoted_reservation_id) if entry.promoted_reservation_id else None,
    }
