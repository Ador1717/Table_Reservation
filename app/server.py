from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.auth import AdminSessionManager, get_authorized_admin
from app.reservation_store import ReservationStore, reservation_to_dict, waitlist_entry_to_dict


ROOT = Path(__file__).resolve().parent.parent
store = ReservationStore()
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-admin-key")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-admin-password")
SESSION_MANAGER = AdminSessionManager(ttl_minutes=480)
store.ensure_admin_user(ADMIN_USERNAME, ADMIN_PASSWORD, role="admin")


class ReservationHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_no_content(self, status: int = 204) -> None:
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(body or "{}")

    def _bad_request(self, message: str) -> None:
        self._send_json({"error": message}, status=HTTPStatus.BAD_REQUEST)

    def _require_admin(self) -> dict | None:
        principal = get_authorized_admin(self.headers, ADMIN_API_KEY, session_manager=SESSION_MANAGER)
        if not principal:
            self._send_json({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
            return None
        return principal

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Key, Authorization")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/availability":
            query = parse_qs(parsed.query)
            restaurant_id = query.get("restaurantId", [None])[0]
            date = query.get("date", [None])[0]
            party_size = query.get("partySize", [None])[0]
            if not restaurant_id or not date or not party_size:
                return self._bad_request("restaurantId, date, and partySize are required")

            try:
                party_size_int = int(party_size)
            except ValueError:
                return self._bad_request("partySize must be an integer")

            slots = store.get_availability(restaurant_id, date, party_size_int)
            return self._send_json({"slots": slots})

        if parsed.path == "/reservations":
            if not self._require_admin():
                return
            query = parse_qs(parsed.query)
            restaurant_id = query.get("restaurantId", [None])[0]
            date = query.get("date", [None])[0]
            reservations = store.list_reservations(restaurant_id=restaurant_id, date=date)
            return self._send_json({"reservations": [reservation_to_dict(r) for r in reservations]})

        if parsed.path == "/waitlist":
            if not self._require_admin():
                return
            query = parse_qs(parsed.query)
            restaurant_id = query.get("restaurantId", [None])[0]
            date = query.get("date", [None])[0]
            waitlist = store.list_waitlist_entries(restaurant_id=restaurant_id, date=date)
            return self._send_json({"entries": [waitlist_entry_to_dict(entry) for entry in waitlist]})

        if parsed.path == "/analytics":
            if not self._require_admin():
                return
            query = parse_qs(parsed.query)
            restaurant_id = query.get("restaurantId", [None])[0]
            date = query.get("date", [None])[0]
            if not restaurant_id or not date:
                return self._bad_request("restaurantId and date are required")
            analytics = store.get_daily_analytics(restaurant_id=restaurant_id, date=date)
            return self._send_json(analytics)

        if parsed.path == "/admin/users":
            if not self._require_admin():
                return
            users = store.list_admin_users()
            return self._send_json({"users": users})

        if parsed.path == "/" or parsed.path.startswith("/web"):
            return self._serve_static(parsed.path)

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/admin/login":
            payload = self._read_json_body()
            username = payload.get("username")
            password = payload.get("password")
            if not username or not password:
                return self._bad_request("username and password are required")

            user = store.authenticate_admin_user(username, password)
            if not user:
                return self._send_json({"error": "Invalid credentials"}, status=HTTPStatus.UNAUTHORIZED)

            session = SESSION_MANAGER.create_session(user["username"], "admin")
            return self._send_json(
                {
                    "accessToken": session.token,
                    "tokenType": "Bearer",
                    "expiresAt": session.expires_at.isoformat(),
                    "user": {"username": user["username"], "role": "admin"},
                },
                status=HTTPStatus.OK,
            )

        if self.path == "/admin/users":
            if not self._require_admin():
                return
            payload = self._read_json_body()
            username = payload.get("username")
            password = payload.get("password")
            if not username or not password:
                return self._bad_request("username and password are required")

            try:
                store.create_admin_user(username=username, password=password)
            except ValueError as exc:
                return self._bad_request(str(exc))

            return self._send_json({"created": True, "username": username, "role": "admin"}, status=HTTPStatus.CREATED)

        if self.path == "/reservations":
            payload = self._read_json_body()
            required = ["restaurantId", "guestName", "partySize", "reservationAt"]
            missing = [field for field in required if field not in payload]
            if missing:
                return self._bad_request(f"Missing required fields: {', '.join(missing)}")

            try:
                reservation = store.create_reservation(payload)
            except ValueError as exc:
                return self._bad_request(str(exc))

            return self._send_json(reservation_to_dict(reservation), status=HTTPStatus.CREATED)

        if self.path == "/waitlist":
            payload = self._read_json_body()
            required = ["restaurantId", "guestName", "partySize", "desiredAt"]
            missing = [field for field in required if field not in payload]
            if missing:
                return self._bad_request(f"Missing required fields: {', '.join(missing)}")

            try:
                entry = store.add_waitlist_entry(payload)
            except ValueError as exc:
                return self._bad_request(str(exc))

            return self._send_json(waitlist_entry_to_dict(entry), status=HTTPStatus.CREATED)

        return self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_PATCH(self) -> None:  # noqa: N802
        if not self._require_admin():
            return
        parts = self.path.split("/")
        if len(parts) != 3 or parts[1] != "reservations":
            return self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        try:
            reservation_id = int(parts[2])
        except ValueError:
            return self._bad_request("Invalid reservationId")

        payload = self._read_json_body()
        try:
            reservation = store.update_reservation(reservation_id, payload)
        except KeyError:
            return self._send_json({"error": "Reservation not found"}, status=HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            return self._bad_request(str(exc))

        return self._send_json(reservation_to_dict(reservation), status=HTTPStatus.OK)

    def do_DELETE(self) -> None:  # noqa: N802
        if not self._require_admin():
            return
        parts = self.path.split("/")
        if len(parts) != 3 or parts[1] != "reservations":
            return self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        try:
            reservation_id = int(parts[2])
        except ValueError:
            return self._bad_request("Invalid reservationId")

        try:
            store.cancel_reservation(reservation_id)
        except KeyError:
            return self._send_json({"error": "Reservation not found"}, status=HTTPStatus.NOT_FOUND)

        return self._send_no_content(status=HTTPStatus.NO_CONTENT)

    def _serve_static(self, path: str) -> None:
        rel_path = "web/index.html" if path in {"/", "/web", "/web/"} else path.removeprefix("/")
        file_path = ROOT / rel_path
        if not file_path.exists() or not file_path.is_file():
            return self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        mime = "text/plain"
        if file_path.suffix == ".html":
            mime = "text/html"
        elif file_path.suffix == ".js":
            mime = "application/javascript"
        elif file_path.suffix == ".css":
            mime = "text/css"

        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    host, port = "0.0.0.0", 8000
    print(f"Serving reservation API and widget at http://{host}:{port}")
    ThreadingHTTPServer((host, port), ReservationHandler).serve_forever()
