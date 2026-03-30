# Distributed E-Commerce Order Engine 🛒

**Hackathon Submission** — `VardhanJakka_Ecommerce_Order_Engine_Hackathon`

---

## Project Overview

A robust, scalable backend engine for an e-commerce platform built with **Django + Django REST Framework**. Simulates real-world challenges faced by platforms like Amazon, Flipkart, and Meesho — including inventory conflicts, payment failures, concurrent users, fraud detection, and event-driven architecture.

---

## Features Implemented (All 20 Tasks)

| # | Task | Status |
|---|------|--------|
| 1 | Product Management (add, update stock, unique IDs) | ✅ |
| 2 | Multi-User Cart System | ✅ |
| 3 | Real-Time Stock Reservation | ✅ |
| 4 | Concurrency Simulation (select_for_update locking) | ✅ |
| 5 | Order Placement Engine (atomic: validate→lock→create→clear) | ✅ |
| 6 | Payment Simulation (random success/failure) | ✅ |
| 7 | Transaction Rollback System | ✅ |
| 8 | Order State Machine (CREATED→PAID→SHIPPED→DELIVERED) | ✅ |
| 9 | Discount & Coupon Engine (SAVE10, FLAT200, bulk/total rules) | ✅ |
| 10 | Inventory Alert System (low stock, block if stock=0) | ✅ |
| 11 | Order Management (view, search, filter by status) | ✅ |
| 12 | Order Cancellation Engine (restore stock, edge cases) | ✅ |
| 13 | Return & Refund System (partial return, stock restore) | ✅ |
| 14 | Event-Driven System (ORDER_CREATED, PAYMENT_SUCCESS, etc.) | ✅ |
| 15 | Inventory Reservation Expiry (auto-release) | ✅ |
| 16 | Audit Logging System (immutable logs) | ✅ |
| 17 | Fraud Detection (3 orders/min, high-value flagging) | ✅ |
| 18 | Failure Injection System (random payment/order/inventory fail) | ✅ |
| 19 | Idempotency Handling (prevent duplicate orders) | ✅ |
| 20 | Microservice Simulation (Product/Cart/Order/Payment apps) | ✅ |

---

## Design Approach

- **Modular Django apps** simulate microservices (Task 20): `products`, `cart`, `orders`, `payments`, `events`, `logs`
- **`select_for_update()`** for row-level database locking prevents race conditions (Task 4)
- **`transaction.atomic()`** ensures all-or-nothing order placement and rollback (Tasks 5, 7)
- **Order State Machine** enforces valid lifecycle transitions only (Task 8)
- **Immutable AuditLog** model raises exceptions on update/delete (Task 16)
- **Event queue** with sequence ordering — failure stops downstream events (Task 14)
- **JWT Authentication** for all API endpoints
- **Swagger UI** auto-generated at `/api/docs/`

---

## Assumptions

- SQLite used for development; PostgreSQL supported via environment variables
- Payment simulation uses 70% success / 30% failure random rate
- Fraud threshold: 3+ orders in 1 minute, or order value ≥ ₹10,000
- Inventory reservation expiry: 15 minutes (configurable)
- CLI runs in single-process mode; threading simulates concurrency for Task 4

---

## How to Run the Project

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create a superuser (for admin panel)
```bash
python manage.py createsuperuser
```

### 4. Run the Django dev server
```bash
python manage.py runserver
```

### 5. Access Swagger API Docs
Open: http://127.0.0.1:8000/api/docs/

### 6. Run the CLI Menu
```bash
python cli.py
```

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/token/` | Get JWT token |
| GET/POST | `/api/products/` | List / add products |
| POST | `/api/products/{id}/update_stock/` | Update stock |
| GET | `/api/products/low_stock/` | Low stock alert |
| POST | `/api/products/{id}/reserve/` | Reserve stock |
| GET | `/api/cart/` | View cart |
| POST | `/api/cart/add/` | Add to cart |
| DELETE | `/api/cart/remove/{product_id}/` | Remove from cart |
| POST | `/api/cart/apply-coupon/` | Apply coupon |
| POST | `/api/orders/place/` | Place order (atomic) |
| POST | `/api/orders/{id}/cancel/` | Cancel order |
| POST | `/api/orders/{id}/return/` | Return items |
| POST | `/api/orders/{id}/transition/` | Change order status |
| POST | `/api/payments/process/` | Process payment |
| POST | `/api/payments/inject-failure/` | Inject failure (Task 18) |
| GET | `/api/logs/` | View audit logs |
| GET | `/api/events/` | View event queue |

---

## Project Structure

```
ecommerce_engine/
├── config/              # Django settings, URLs, WSGI
├── apps/
│   ├── products/        # Task 1, 3, 10, 15
│   ├── cart/            # Task 2, 4, 9
│   ├── orders/          # Task 5, 7, 8, 11, 12, 13, 17, 19
│   ├── payments/        # Task 6, 18
│   ├── events/          # Task 14
│   └── logs/            # Task 16
├── cli.py               # CLI Menu (all 14 options)
├── manage.py
├── requirements.txt
└── README.md
```
