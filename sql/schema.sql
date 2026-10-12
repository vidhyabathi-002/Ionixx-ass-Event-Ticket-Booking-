CREATE DATABASE IF NOT EXISTS event_ticket_db;

USE event_ticket_db;

CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    venue VARCHAR(200) NOT NULL,
    category ENUM(
        'MUSIC',
        'TECH',
        'SPORTS',
        'THEATRE'
    ) NOT NULL,
    event_date DATE NOT NULL,
    total_seats INT NOT NULL,
    base_price DECIMAL(10,2) NOT NULL,

    CONSTRAINT chk_total_seats
        CHECK (total_seats BETWEEN 10 AND 10000),

    CONSTRAINT chk_base_price
        CHECK (base_price > 0),

    CONSTRAINT uq_event_name_date
        UNIQUE (name, event_date)
);

CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_email VARCHAR(254) NOT NULL,
    seats INT NOT NULL,
    price_per_seat DECIMAL(10,2) NULL,
    total_amount DECIMAL(12,2) NULL,
    status ENUM('CONFIRMED', 'REJECTED') NOT NULL,
    rejection_reason VARCHAR(500) NULL,
    booked_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_booking_event
        FOREIGN KEY (event_id)
        REFERENCES events(id),

    CONSTRAINT chk_booking_seats
        CHECK (seats BETWEEN 1 AND 6),

    INDEX idx_booking_event_status_date
        (event_id, status, booked_on),

    INDEX idx_booking_customer
        (event_id, customer_email, status)
);

CREATE TABLE booking_seats (
    booking_id INT NOT NULL,
    seat_number INT NOT NULL,

    PRIMARY KEY (booking_id, seat_number),

    CONSTRAINT fk_seat_booking
        FOREIGN KEY (booking_id)
        REFERENCES bookings(id)
);