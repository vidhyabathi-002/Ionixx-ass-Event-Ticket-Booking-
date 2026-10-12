from flask import Flask, request, jsonify
from datetime import date
from decimal import Decimal
import mysql.connector

from db import get_db_connection

app = Flask(__name__)
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Event Ticket Booking API is running",
       
        "endpoints": [
            "POST /api/events",
            "GET /api/events/<id>",
            "POST /api/bookings",
            "GET /api/events/<id>/bookings",
            "GET /api/events/<id>/seats",
            "GET /api/events/<id>/summary"
        ]
    }), 200

CATEGORIES = {"MUSIC", "TECH", "SPORTS", "THEATRE"}


def event_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "venue": row["venue"],
        "category": row["category"],
        "event_date": row["event_date"].isoformat(),
        "total_seats": row["total_seats"],
        "base_price": float(row["base_price"])
    }


def valid_positive_integer(value):
    return type(value) is int and value > 0


@app.route("/api/events", methods=["POST"])
def create_event():
    # Validate JSON request
    if not request.is_json:
        return jsonify({
            "error": "INVALID_REQUEST"
        }), 400

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "error": "INVALID_REQUEST"
        }), 400

    errors = {}

    # Name validation
    name = data.get("name")
    if not isinstance(name, str) or len(name.strip()) < 3:
        errors["name"] = "Must contain at least 3 characters"
    elif len(name.strip()) > 150:
        errors["name"] = "Must not exceed 150 characters"

    # Venue validation
    venue = data.get("venue")
    if not isinstance(venue, str) or not venue.strip():
        errors["venue"] = "Required"

    # Category validation
    category = data.get("category")
    if not isinstance(category, str) or category not in CATEGORIES:
        errors["category"] = (
            "Must be MUSIC, TECH, SPORTS or THEATRE"
        )

    # Event date validation
    event_date = None
    raw_date = data.get("event_date")

    if not isinstance(raw_date, str):
        errors["event_date"] = "Required in YYYY-MM-DD format"
    else:
        try:
            event_date = date.fromisoformat(raw_date)

            if event_date.isoformat() != raw_date:
                raise ValueError()

            if event_date < date.today():
                errors["event_date"] = "Cannot be in the past"

        except ValueError:
            errors["event_date"] = (
                "Must be a valid date in YYYY-MM-DD format"
            )

    # Total seats validation
    total_seats = data.get("total_seats")
    if (
        not valid_positive_integer(total_seats)
        or not 10 <= total_seats <= 10000
    ):
        errors["total_seats"] = "Must be an integer from 10 to 10000"

    # Base price validation
    raw_price = data.get("base_price")
    base_price = None

    if isinstance(raw_price, bool) or raw_price is None:
        errors["base_price"] = "Must be greater than 0"
    else:
        try:
            base_price = Decimal(str(raw_price))

            if (
                not base_price.is_finite()
                or base_price <= 0
                or base_price.as_tuple().exponent < -2
            ):
                errors["base_price"] = (
                    "Must be positive with at most 2 decimal places"
                )

        except Exception:
            errors["base_price"] = "Must be a valid number greater than 0"

    if errors:
        return jsonify({"errors": errors}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check duplicate event name and date
        cursor.execute(
            """
            SELECT id FROM events
            WHERE name = %s AND event_date = %s
            """,
            (name.strip(), event_date)
        )

        if cursor.fetchone():
            return jsonify({
                "error": "DUPLICATE_EVENT"
            }), 409

        cursor.execute(
            """
            INSERT INTO events
                (name, venue, category, event_date,
                 total_seats, base_price)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                name.strip(),
                venue.strip(),
                category,
                event_date,
                total_seats,
                base_price
            )
        )

        event_id = cursor.lastrowid
        connection.commit()

        cursor.execute(
            "SELECT * FROM events WHERE id = %s",
            (event_id,)
        )

        event = event_to_dict(cursor.fetchone())

        return jsonify(event), 201

    except mysql.connector.IntegrityError as exc:
        if connection:
            connection.rollback()

        if exc.errno == 1062:
            return jsonify({
                "error": "DUPLICATE_EVENT"
            }), 409

        app.logger.exception("Database integrity failure")
        return jsonify({"error": "INTERNAL_SERVER_ERROR"}), 500

    except Exception:
        if connection:
            connection.rollback()

        app.logger.exception("Unexpected event creation failure")
        return jsonify({"error": "INTERNAL_SERVER_ERROR"}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/events/<event_id>", methods=["GET"])
def get_event(event_id):
    # Invalid path ID
    if not event_id.isascii() or not event_id.isdigit():
        return jsonify({
            "error": "INVALID_EVENT_ID"
        }), 400

    if int(event_id) <= 0:
        return jsonify({
            "error": "INVALID_EVENT_ID"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM events WHERE id = %s",
            (int(event_id),)
        )

        row = cursor.fetchone()

        if not row:
            return jsonify({
                "error": "EVENT_NOT_FOUND"
            }), 404

        return jsonify(event_to_dict(row)), 200

    except Exception:
        app.logger.exception("Unexpected event retrieval failure")
        return jsonify({"error": "INTERNAL_SERVER_ERROR"}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import date


def money(value):
    return value.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def parse_stored_seats(seat_string):
    if not seat_string:
        return []

    return [
        int(number)
        for number in seat_string.split(",")
        if number.strip()
    ]


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    # 1. Validate JSON
    if not request.is_json:
        return jsonify({"error": "INVALID_REQUEST"}), 400

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({"error": "INVALID_REQUEST"}), 400

    errors = {}

    # 2. Validate event ID
    event_id = data.get("event_id")

    if not valid_positive_integer(event_id):
        errors["event_id"] = "Must be a positive integer"

    # 3. Validate customer name
    customer_name = data.get("customer_name")

    if (
        not isinstance(customer_name, str)
        or not customer_name.strip()
    ):
        errors["customer_name"] = "Required"
    elif len(customer_name.strip()) > 150:
        errors["customer_name"] = "Maximum 150 characters"

    # 4. Validate email
    customer_email = data.get("customer_email")

    if (
        not isinstance(customer_email, str)
        or len(customer_email) > 254
        or not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            customer_email.strip()
        )
    ):
        errors["customer_email"] = "Must be a valid email address"

    # 5. Validate seat numbers
    seat_numbers = data.get("seat_numbers")

    if (
        not isinstance(seat_numbers, list)
        or not 1 <= len(seat_numbers) <= 6
        or any(type(seat) is not int or seat <= 0
               for seat in seat_numbers)
    ):
        errors["seat_numbers"] = (
            "Must contain 1 to 6 positive integer seat numbers"
        )
    elif len(set(seat_numbers)) != len(seat_numbers):
        errors["seat_numbers"] = "Duplicate seat numbers are not allowed"

    if errors:
        return jsonify({"errors": errors}), 400

    # Normalize email so the same email is treated consistently
    customer_email = customer_email.strip().lower()
    customer_name = customer_name.strip()

    # 6. Open database
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # Lock the event row while checking and reserving seats.
        cursor.execute(
            """
            SELECT *
            FROM events
            WHERE id = %s
            FOR UPDATE
            """,
            (event_id,)
        )

        event = cursor.fetchone()

        if not event:
            connection.rollback()
            return jsonify({"error": "EVENT_NOT_FOUND"}), 404

        # 7. Validate requested seats against event capacity
        invalid_seats = [
            seat for seat in seat_numbers
            if seat > event["total_seats"]
        ]

        if invalid_seats:
            connection.rollback()
            return jsonify({
                "errors": {
                    "seat_numbers": [
                        f"Seat {seat} does not exist for this event"
                        for seat in invalid_seats
                    ]
                }
            }), 400

        seats_text = ",".join(map(str, seat_numbers))
        seat_count = len(seat_numbers)

        # 8. Past events: save a rejected booking
        if event["event_date"] < date.today():
            status = "REJECTED"
            rejection_reason = "Event date has passed"
            price_per_seat = None
            total_amount = None

        else:
            # 9. Check seats held by confirmed bookings only
            cursor.execute(
                """
                SELECT seat_numbers
                FROM bookings
                WHERE event_id = %s
                  AND status = 'CONFIRMED'
                """,
                (event_id,)
            )

            occupied = set()

            for row in cursor.fetchall():
                occupied.update(
                    parse_stored_seats(row["seat_numbers"])
                )

            already_booked = sorted(
                set(seat_numbers) & occupied
            )

            # 10. Check customer's existing confirmed seats
            cursor.execute(
                """
                SELECT COALESCE(SUM(seats), 0) AS seats_booked
                FROM bookings
                WHERE event_id = %s
                  AND LOWER(customer_email) = %s
                  AND status = 'CONFIRMED'
                """,
                (event_id, customer_email)
            )

            customer_row = cursor.fetchone()
            previous_seats = int(customer_row["seats_booked"])

            rejection_reasons = []

            if already_booked:
                rejection_reasons.append(
                    "Seats already booked: "
                    + ", ".join(map(str, already_booked))
                )

            if previous_seats + seat_count > 6:
                rejection_reasons.append(
                    "Customer cannot book more than 6 confirmed "
                    "seats for this event"
                )

            if rejection_reasons:
                status = "REJECTED"
                rejection_reason = "; ".join(rejection_reasons)
                price_per_seat = None
                total_amount = None

            else:
                # 11. Calculate discounts
                base_price = Decimal(str(event["base_price"]))
                price = base_price

                days_until_event = (
                    event["event_date"] - date.today()
                ).days

                if days_until_event >= 30:
                    price *= Decimal("0.90")

                if seat_count >= 4:
                    price *= Decimal("0.95")

                price_per_seat = money(price)
                total_amount = money(
                    price_per_seat * seat_count
                )

                status = "CONFIRMED"
                rejection_reason = None

        # 12. Save BOTH confirmed and rejected requests
        cursor.execute(
            """
            INSERT INTO bookings (
                event_id,
                customer_name,
                customer_email,
                seats,
                seat_numbers,
                price_per_seat,
                total_amount,
                status,
                rejection_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event_id,
                customer_name,
                customer_email,
                seat_count,
                seats_text,
                price_per_seat,
                total_amount,
                status,
                rejection_reason
            )
        )

        booking_id = cursor.lastrowid

        # Commit before sending the response
        connection.commit()

        # 13. Return the saved booking
        response = {
            "id": booking_id,
            "event_id": event_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "seat_numbers": seat_numbers,
            "seats": seat_count,
            "price_per_seat": (
                float(price_per_seat)
                if price_per_seat is not None else None
            ),
            "total_amount": (
                float(total_amount)
                if total_amount is not None else None
            ),
            "status": status,
            "rejection_reason": rejection_reason
        }

        return jsonify(response), 201

    except Exception:
        if connection:
            connection.rollback()

        app.logger.exception("Booking creation failed")

        return jsonify({
            "error": "INTERNAL_SERVER_ERROR"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


@app.route("/api/events/<event_id>/seats", methods=["GET"])
def get_event_seats(event_id):
    # Validate event ID
    if not event_id.isascii() or not event_id.isdigit():
        return jsonify({"error": "INVALID_EVENT_ID"}), 400

    event_id = int(event_id)

    if event_id <= 0:
        return jsonify({"error": "INVALID_EVENT_ID"}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check whether the event exists
        cursor.execute(
            "SELECT id, total_seats FROM events WHERE id = %s",
            (event_id,)
        )
        event = cursor.fetchone()

        if not event:
            return jsonify({"error": "EVENT_NOT_FOUND"}), 404

        # Only confirmed bookings occupy seats
        cursor.execute(
            """
            SELECT seat_numbers
            FROM bookings
            WHERE event_id = %s
              AND status = 'CONFIRMED'
            """,
            (event_id,)
        )

        booked = set()

        for row in cursor.fetchall():
            booked.update(
                parse_stored_seats(row["seat_numbers"])
            )

        booked_seats = sorted(booked)

        available_seats = [
            seat
            for seat in range(1, event["total_seats"] + 1)
            if seat not in booked
        ]

        return jsonify({
            "event_id": event_id,
            "total_seats": event["total_seats"],
            "booked_seats": booked_seats,
            "available_seats": available_seats
        }), 200

    except Exception:
        app.logger.exception("Seat availability retrieval failed")
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()



@app.route("/api/events/<event_id>/bookings", methods=["GET"])
def get_event_bookings(event_id):
    # Validate event ID
    if not event_id.isascii() or not event_id.isdigit():
        return jsonify({"error": "INVALID_EVENT_ID"}), 400

    event_id = int(event_id)

    if event_id <= 0:
        return jsonify({"error": "INVALID_EVENT_ID"}), 400

    # Validate optional status filter
    status = request.args.get("status")

    if status is not None and status not in {"CONFIRMED", "REJECTED"}:
        return jsonify({
            "error": "INVALID_STATUS",
            "message": "Status must be CONFIRMED or REJECTED"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check that the event exists
        cursor.execute(
            "SELECT id FROM events WHERE id = %s",
            (event_id,)
        )

        if not cursor.fetchone():
            return jsonify({"error": "EVENT_NOT_FOUND"}), 404

        # Retrieve bookings, newest first
        query = """
            SELECT
                id,
                event_id,
                customer_name,
                customer_email,
                seat_numbers,
                seats,
                price_per_seat,
                total_amount,
                status,
                rejection_reason,
                booked_on
            FROM bookings
            WHERE event_id = %s
        """
        params = [event_id]

        if status is not None:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY booked_on DESC, id DESC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        bookings = []

        for row in rows:
            bookings.append({
                "id": row["id"],
                "event_id": row["event_id"],
                "customer_name": row["customer_name"],
                "customer_email": row["customer_email"],
                "seat_numbers": parse_stored_seats(
                    row["seat_numbers"]
                ),
                "seats": row["seats"],
                "price_per_seat": (
                    float(row["price_per_seat"])
                    if row["price_per_seat"] is not None
                    else None
                ),
                "total_amount": (
                    float(row["total_amount"])
                    if row["total_amount"] is not None
                    else None
                ),
                "status": row["status"],
                "rejection_reason": row["rejection_reason"],
                "booked_on": (
                    row["booked_on"].isoformat(sep=" ")
                    if row["booked_on"] else None
                )
            })

        return jsonify(bookings), 200

    except Exception:
        app.logger.exception("Booking retrieval failed")
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()



@app.route("/api/events/<event_id>/summary", methods=["GET"])
def get_event_summary(event_id):
    # Validate event ID
    if not event_id.isascii() or not event_id.isdigit():
        return jsonify({"error": "INVALID_EVENT_ID"}), 400

    event_id = int(event_id)

    if event_id <= 0:
        return jsonify({"error": "INVALID_EVENT_ID"}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Find event details
        cursor.execute(
            """
            SELECT id, name, total_seats
            FROM events
            WHERE id = %s
            """,
            (event_id,)
        )

        event = cursor.fetchone()

        if not event:
            return jsonify({"error": "EVENT_NOT_FOUND"}), 404

        # Aggregate confirmed bookings only
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(seats), 0) AS seats_sold,
                COALESCE(SUM(total_amount), 0) AS total_revenue
            FROM bookings
            WHERE event_id = %s
              AND status = 'CONFIRMED'
            """,
            (event_id,)
        )

        result = cursor.fetchone()

        seats_sold = int(result["seats_sold"])
        total_revenue = Decimal(str(result["total_revenue"]))
        total_seats = int(event["total_seats"])

        seats_available = total_seats - seats_sold

        occupancy_pct = round(
            seats_sold / total_seats * 100, 1
        )

        if occupancy_pct < 40:
            demand_band = "LOW"
        elif occupancy_pct <= 70:
            demand_band = "MEDIUM"
        else:
            demand_band = "HIGH"

        return jsonify({
            "event_id": event_id,
            "event_name": event["name"],
            "total_seats": total_seats,
            "seats_sold": seats_sold,
            "seats_available": seats_available,
            "total_revenue": float(
                total_revenue.quantize(Decimal("0.01"))
            ),
            "occupancy_pct": occupancy_pct,
            "demand_band": demand_band
        }), 200

    except Exception:
        app.logger.exception("Event summary retrieval failed")
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    app.run(debug=True)