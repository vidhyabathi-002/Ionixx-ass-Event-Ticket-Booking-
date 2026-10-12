
# Event Ticket Booking API

## 1. Project Overview

The Event Ticket Booking API is a REST API developed using Python, Flask, and MySQL. It allows users to create events, book seats, check seat availability, retrieve booking details, and view event summaries.

The API validates requests, checks seat conflicts, applies discounts, stores booking records, and returns JSON responses.

## 2. Technologies Used

- Python — application logic
- Flask — REST API development
- MySQL — database storage
- mysql.connector — database connectivity
- Postman — API testing
- JSON — request and response format

## 3. Project Architecture

Postman / Client
        |
        v
Flask Application (app.py)
        |
        v
Database Connection (db.py)
        |
        v
MySQL Database
        |
        v
JSON Response

## 4. Database Tables

### Events Table

| Column | Description |
|---|---|
| id | Unique event ID |
| name | Event name |
| venue | Event location |
| category | Event category |
| event_date | Event date |
| total_seats | Total available capacity |
| base_price | Original price per seat |

Allowed categories:
- MUSIC
- TECH
- SPORTS
- THEATRE

### Bookings Table

| Column | Description |
|---|---|
| id | Unique booking ID |
| event_id | Related event ID |
| customer_name | Customer name |
| customer_email | Customer email |
| seats | Number of requested seats |
| seat_numbers | Requested seat numbers |
| price_per_seat | Discounted price per seat |
| total_amount | Total booking price |
| status | CONFIRMED or REJECTED |
| rejection_reason | Reason for rejection |
| booked_on | Booking timestamp |

Rejected booking attempts are stored, but they do not reserve seats or contribute to revenue.

## 5. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/events | Create an event |
| GET | /api/events/1 | Retrieve event details |
| POST | /api/bookings | Submit a booking |
| GET | /api/events/1/seats | Check booked and available seats |
| GET | /api/events/1/bookings | List event bookings |
| GET | /api/events/1/bookings?status=CONFIRMED | List confirmed bookings |
| GET | /api/events/1/bookings?status=REJECTED | List rejected bookings |
| GET | /api/events/1/summary | View event summary |

Replace `1` with the required event ID.

## 6. HTTP Status Codes

| Status Code | Meaning |
|---|---|
| 200 OK | Request completed successfully |
| 201 Created | A new event or booking record was created |
| 400 Bad Request | Invalid request or validation failure |
| 404 Not Found | Requested event does not exist |
| 409 Conflict | Duplicate event with the same name and date |
| 500 Internal Server Error | Unexpected server error |

A booking may return HTTP 201 even when its booking status is REJECTED because the rejection record was successfully created.

## 7. Event Creation

Endpoint: `POST /api/events`

Example request:

```json
{
  "name": "AI Tech Meetup",
  "venue": "Chennai Trade Centre",
  "category": "TECH",
  "event_date": "2026-12-20",
  "total_seats": 200,
  "base_price": 1500
}
```

Validation rules:
- Event name must satisfy the minimum length requirement.
- Category must be valid.
- Event date must not be in the past.
- Total seats must be between 10 and 10,000.
- Base price must be greater than zero.
- Duplicate event names on the same date are not allowed.

## 8. Booking Workflow

1. Receive the booking request as JSON.
2. Validate customer details and event ID.
3. Require between 1 and 6 unique seat numbers.
4. Check whether the event exists.
5. Validate seat numbers against event capacity.
6. Check whether the event date has passed.
7. Check requested seats against confirmed bookings.
8. Verify the customer's maximum of six confirmed seats per event.
9. Save rejected booking attempts with a reason.
10. Calculate discounts for eligible bookings.
11. Save the booking to MySQL.
12. Return a JSON response.

## 9. Booking Validation Rules

- Each booking can request between 1 and 6 seats.
- Seat numbers must be unique within a request.
- Seat numbers must be within event capacity.
- Confirmed bookings cannot reserve the same seat twice.
- Rejected bookings do not occupy seats.
- Each customer can have at most six confirmed seats per event.
- Booking attempts for past events are rejected.
- Invalid customer email addresses are rejected.

## 10. Discount Calculation

### Early-Bird Discount

A 10% discount applies when the event is at least 30 days away.

### Group Discount

An additional 5% discount applies when a booking contains at least four seats.

The group discount is applied after the early-bird discount.

### Validation 19 Example

Base price per seat: ₹1,500  
Number of seats: 4  
Event date: 71 days away

Early-bird calculation:

1500 × 0.90 = ₹1,350.00

Group discount calculation:

1350 × 0.95 = ₹1,282.50

Total booking amount:

1282.50 × 4 = ₹5,130.00

Expected result:

```json
{
  "status": "CONFIRMED",
  "seats": 4,
  "price_per_seat": 1282.50,
  "total_amount": 5130.00
}
```

Use Python's `Decimal` for monetary calculations and round prices to two decimal places.

## 11. Seat Availability

Endpoint:

`GET /api/events/1/seats`

The response contains:
- `event_id`
- `total_seats`
- `booked_seats`
- `available_seats`

Only confirmed bookings count as occupied seats.

Always check the latest availability response before submitting a new booking.

## 12. Booking List

List confirmed bookings:

`GET /api/events/1/bookings?status=CONFIRMED`

List rejected bookings:

`GET /api/events/1/bookings?status=REJECTED`

An invalid status, such as `PENDING`, should return HTTP 400.

## 13. Event Summary

Endpoint:

`GET /api/events/1/summary`

The summary includes:
- Total seats
- Seats sold
- Seats available
- Occupancy percentage
- Total revenue
- Demand band

Only confirmed bookings contribute to seats sold and revenue.

Occupancy formula:

Occupancy (%) = (Seats Sold / Total Seats) × 100

The implementation discussed uses:
- LOW: below 40%
- MEDIUM: 40% through 70%
- HIGH: above 70%

Confirm the final demand thresholds against your requirements before submission, since an earlier requirement specified HIGH as above 75%.

## 14. SQL Verification Queries

### Check event details

```sql
SELECT id, name, event_date, total_seats, base_price
FROM events
WHERE id = 1;
```

### Check confirmed bookings

```sql
SELECT *
FROM bookings
WHERE event_id = 1
  AND status = 'CONFIRMED'
ORDER BY id DESC;
```

### Check a test booking

```sql
SELECT *
FROM bookings
WHERE customer_email = 'test19@example.com'
ORDER BY id DESC;
```

### Calculate seats sold and revenue

```sql
SELECT
    COALESCE(SUM(seats), 0) AS seats_sold,
    COALESCE(SUM(total_amount), 0) AS total_revenue
FROM bookings
WHERE event_id = 1
  AND status = 'CONFIRMED';
```

## 15. Postman Testing

### Create an Event

Method: POST

URL:
`http://127.0.0.1:5000/api/events`

Choose Body → raw → JSON and enter the event data.

### Check Seat Availability

Method: GET

URL:
`http://127.0.0.1:5000/api/events/1/seats`

### Create a Booking

Method: POST

URL:
`http://127.0.0.1:5000/api/bookings`

Example body:

```json
{
  "event_id": 1,
  "customer_name": "Test Customer",
  "customer_email": "test19@example.com",
  "seat_numbers": [23, 24, 25, 26]
}
```

Use these seats only if all four are currently available.

### View the Event Summary

Method: GET

URL:
`http://127.0.0.1:5000/api/events/1/summary`

## 16. Validation Checklist

| Test Case | Expected Result |
|---|---|
| Create event with valid data | 201 Created |
| Invalid event name | 400 Bad Request |
| Invalid category | 400 Bad Request |
| Past event date | 400 Bad Request |
| Invalid seat capacity | 400 Bad Request |
| Multiple invalid fields | 400 with applicable errors |
| Duplicate event | 409 Conflict |
| Invalid JSON | 400 Bad Request |
| Missing event | 404 Not Found |
| Empty seat list or more than six seats | 400 Bad Request |
| Duplicate seat numbers in one request | 400 Bad Request |
| Seat exceeds capacity | 400 Bad Request |
| Invalid customer email | 400 Bad Request |
| Booking for a past event | 201 with REJECTED status |
| Seat already confirmed | 201 with REJECTED status |
| Seats from rejected booking | Can be booked if otherwise available |
| Customer exceeds six confirmed seats | Booking rejected |
| Four seats, 71 days away, base price ₹1,500 | ₹1,282.50 per seat |
| Two seats, 10 days away, base price ₹1,000 | ₹1,000 per seat |
| Invalid booking status filter | 400 Bad Request |
| Summary with no bookings | Zero sales and revenue; LOW demand |

## 17. Interview Explanation

I developed an Event Ticket Booking REST API using Python Flask and MySQL. It supports event creation, booking attempts, seat availability checks, booking retrieval, and event summaries.

I implemented server-side validation, duplicate-event detection, seat-conflict checking, customer booking limits, and early-bird and group discounts. I used Postman to test API endpoints, HTTP status codes, validation failures, and JSON responses.

The application stores both confirmed and rejected booking attempts, while only confirmed bookings occupy seats and contribute to revenue.

## 18. Common Interview Questions

### Why did you use Flask?

Flask is a lightweight Python framework that makes it easy to create REST API routes and handle HTTP requests.

### Why did you use MySQL?

MySQL stores event and booking records persistently and supports queries, relationships, and aggregate calculations.

### Why does a rejected booking return 201?

The booking attempt was successfully saved as a new database record. HTTP 201 describes resource creation, while REJECTED describes the booking outcome.

### Why don't rejected bookings occupy seats?

The seat availability logic considers confirmed bookings only, so rejected requests do not block seats for other customers.

### Why use Decimal for prices?

Decimal supports predictable decimal arithmetic and helps avoid floating-point precision issues in currency calculations.

### How do you test the API?

I use Postman to send HTTP requests, inspect JSON responses and status codes, and use MySQL queries to verify saved records.

### How can you prevent duplicate seat bookings under concurrent requests?

The seat check and booking operation should be protected by a database transaction and appropriate locking or constraints. This prevents simultaneous requests from reserving the same seat.

## 19. Final Checklist Before Submission

- All endpoints return JSON.
- Validation errors use the required status codes.
- SQL queries use parameters.
- Rejected bookings do not occupy seats or contribute to revenue.
- Discount calculations and rounding are correct.
- Concurrent seat bookings are handled safely.
- Demand thresholds match the final specification.
- Postman responses match the database records.

---

**Note:** This README describes the project requirements and implementation workflow discussed during development. Verify details against your actual `app.py`, `db.py`, and MySQL schema before submitting the project.
