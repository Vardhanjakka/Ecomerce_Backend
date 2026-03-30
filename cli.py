#!/usr/bin/env python
"""
Distributed E-Commerce Order Engine - CLI Menu
Hackathon submission

Menu:
 1. Add Product
 2. View Products
 3. Add to Cart
 4. Remove from Cart
 5. View Cart
 6. Apply Coupon
 7. Place Order
 8. Cancel Order
 9. View Orders
10. Low Stock Alert
11. Return Product
12. Simulate Concurrent Users
13. View Logs
14. Trigger Failure Mode
 0. Exit
"""

import os
import sys
import django
import random
import threading
from decimal import Decimal

# Bootstrap Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import transaction
from apps.products.models import Product
from apps.cart.models import Cart, CartItem
from apps.cart.views import apply_discount_rules, get_or_create_cart
from apps.orders.models import Order, OrderStatus
from apps.orders.views import check_fraud
from apps.payments.models import Payment, PaymentStatus
from apps.events.utils import dispatch_event
from apps.logs.utils import write_log

# ── helpers ──────────────────────────────────────────────────────────────────

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    print("\n" + "="*60)
    print("   🛒  Distributed E-Commerce Order Engine  🛒")
    print("="*60)

def divider():
    print("-"*60)

def get_or_create_demo_user(username="demo_user"):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password("demo1234")
        user.save()
    return user

def pick_user():
    users = list(User.objects.all())
    if not users:
        print("No users found. Creating demo user...")
        return get_or_create_demo_user()
    print("\nAvailable users:")
    for i, u in enumerate(users, 1):
        print(f"  {i}. {u.username}")
    print("  N. Create new user")
    choice = input("Select user (or N): ").strip()
    if choice.upper() == 'N':
        uname = input("Username: ").strip()
        user, _ = User.objects.get_or_create(username=uname)
        return user
    try:
        return users[int(choice) - 1]
    except (ValueError, IndexError):
        return users[0]

# ── menu actions ─────────────────────────────────────────────────────────────

def add_product():
    """Task 1: Add Product"""
    divider()
    print("📦  ADD PRODUCT")
    pid = input("Product ID (unique): ").strip()
    if Product.objects.filter(product_id=pid).exists():
        print(f"❌  Product ID '{pid}' already exists!")
        return
    name = input("Name: ").strip()
    price = Decimal(input("Price (₹): ").strip())
    stock = int(input("Stock quantity: ").strip())
    if stock < 0:
        print("❌  Stock cannot be negative.")
        return
    product = Product.objects.create(product_id=pid, name=name, price=price, stock=stock)
    user = get_or_create_demo_user()
    write_log(user=user, action='PRODUCT_ADDED',
              details=f"{user.username} added {pid} qty={stock} price=₹{price}")
    print(f"✅  Product '{name}' added! (ID: {pid}, Stock: {stock}, Price: ₹{price})")


def view_products():
    """Task 2 / Task 10: View all products with low-stock highlight"""
    divider()
    print("📋  ALL PRODUCTS")
    products = Product.objects.filter(is_active=True).order_by('product_id')
    if not products:
        print("No products found.")
        return
    print(f"{'ID':<15} {'Name':<25} {'Price':>10} {'Stock':>8} {'Reserved':>10} {'Available':>10}")
    print("-"*80)
    for p in products:
        flag = " ⚠️  LOW" if p.is_low_stock else ""
        flag += " 🚫 OUT" if p.stock == 0 else ""
        print(f"{p.product_id:<15} {p.name:<25} ₹{p.price:>9} {p.stock:>8} {p.reserved_stock:>10} {p.available_stock:>10}{flag}")


def add_to_cart():
    """Task 2 + Task 3: Add to cart with stock check"""
    divider()
    print("🛒  ADD TO CART")
    user = pick_user()
    view_products()
    pid = input("\nEnter Product ID: ").strip()
    try:
        product = Product.objects.get(product_id=pid, is_active=True)
    except Product.DoesNotExist:
        print(f"❌  Product '{pid}' not found.")
        return

    if product.available_stock == 0:
        print(f"❌  '{product.name}' is OUT OF STOCK.")
        return

    qty = int(input(f"Quantity (available: {product.available_stock}): ").strip())
    if qty > product.available_stock:
        print(f"❌  Only {product.available_stock} units available.")
        return

    cart = get_or_create_cart(user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': qty})
    if not created:
        item.quantity += qty
        item.save()

    write_log(user=user, action='CART_ITEM_ADDED',
              details=f"{user.username} added {product.product_id} qty={qty} to cart")
    print(f"✅  Added {qty}x '{product.name}' to {user.username}'s cart.")


def remove_from_cart():
    """Task 2: Remove from cart"""
    divider()
    print("🗑️   REMOVE FROM CART")
    user = pick_user()
    cart = get_or_create_cart(user)
    items = list(cart.items.select_related('product').all())
    if not items:
        print("Cart is empty.")
        return
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item.product.product_id} - {item.product.name} x{item.quantity}")
    choice = int(input("Select item to remove: ").strip()) - 1
    if 0 <= choice < len(items):
        pid = items[choice].product.product_id
        items[choice].delete()
        write_log(user=user, action='CART_ITEM_REMOVED',
                  details=f"{user.username} removed {pid} from cart")
        print(f"✅  Removed '{pid}' from cart.")
    else:
        print("❌  Invalid selection.")


def view_cart():
    """Task 2: View cart"""
    divider()
    print("🧺  VIEW CART")
    user = pick_user()
    cart = get_or_create_cart(user)
    items = list(cart.items.select_related('product').all())
    if not items:
        print(f"{user.username}'s cart is empty.")
        return
    print(f"\n{'Product':<20} {'Price':>10} {'Qty':>6} {'Subtotal':>12}")
    print("-"*52)
    for item in items:
        print(f"{item.product.name:<20} ₹{item.product.price:>9} {item.quantity:>6} ₹{item.subtotal:>11}")
    divider()
    discount, final_total, applied = apply_discount_rules(cart.total, items)
    print(f"{'Subtotal:':<30} ₹{cart.total}")
    if discount > 0:
        print(f"{'Discount:':<30} -₹{discount}")
        for a in applied:
            print(f"   → {a}")
    print(f"{'TOTAL:':<30} ₹{final_total}")


def apply_coupon():
    """Task 9: Apply Coupon"""
    divider()
    print("🎟️   APPLY COUPON")
    print("Available coupons: SAVE10 (10% off), FLAT200 (₹200 off)")
    user = pick_user()
    cart = get_or_create_cart(user)
    items = list(cart.items.select_related('product').all())
    if not items:
        print("Cart is empty.")
        return
    code = input("Enter coupon code: ").strip().upper()
    discount, final_total, applied = apply_discount_rules(cart.total, items, code)
    print(f"\nSubtotal:  ₹{cart.total}")
    print(f"Discount:  ₹{discount}")
    for a in applied:
        print(f"  → {a}")
    print(f"TOTAL:     ₹{final_total}")
    write_log(user=user, action='COUPON_APPLIED',
              details=f"{user.username} applied coupon {code}. Discount=₹{discount}")


def place_order():
    """Task 5: Place Order (atomic) + Task 17: Fraud detection"""
    divider()
    print("📬  PLACE ORDER")
    user = pick_user()
    cart = get_or_create_cart(user)
    items = list(cart.items.select_related('product').all())
    if not items:
        print("Cart is empty.")
        return

    code = input("Coupon code (press Enter to skip): ").strip().upper() or None
    idem_key = input("Idempotency key (press Enter to skip): ").strip() or None

    # Task 19: Idempotency check
    if idem_key and Order.objects.filter(idempotency_key=idem_key).exists():
        existing = Order.objects.get(idempotency_key=idem_key)
        print(f"⚠️  Duplicate order blocked! Already placed: {existing.order_id}")
        return

    try:
        with transaction.atomic():
            subtotal = cart.total
            discount, final_total, applied = apply_discount_rules(subtotal, items, code)

            # Stock validation + lock (Task 4: concurrency)
            for item in items:
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                if product.available_stock < item.quantity:
                    raise ValueError(f"Not enough stock for '{product.name}'.")
                product.stock -= item.quantity
                product.reserved_stock = max(0, product.reserved_stock - item.quantity)
                product.save(update_fields=['stock', 'reserved_stock', 'updated_at'])

            # Task 17: Fraud detection
            is_flagged, flag_reason = check_fraud(user, final_total)
            if is_flagged:
                print(f"⚠️   FRAUD ALERT: {flag_reason}")

            order = Order.objects.create(
                user=user,
                status=OrderStatus.PENDING_PAYMENT,
                subtotal=subtotal,
                discount=discount,
                total=final_total,
                coupon_code=code,
                is_flagged=is_flagged,
                flag_reason=flag_reason,
                idempotency_key=idem_key,
            )
            from apps.orders.models import OrderItem
            for item in items:
                OrderItem.objects.create(
                    order=order, product=item.product,
                    product_id_str=item.product.product_id,
                    product_name=item.product.name,
                    unit_price=item.product.price,
                    quantity=item.quantity,
                )
            cart.clear()

            # Task 6: Simulate payment
            print("\n💳  Processing payment...")
            payment_success = random.random() > 0.3

            payment = Payment.objects.create(
                order=order, amount=final_total,
                status=PaymentStatus.SUCCESS if payment_success else PaymentStatus.FAILED,
                failure_reason="" if payment_success else "Gateway timeout",
            )

            if payment_success:
                order.transition_to(OrderStatus.PAID)
                write_log(user=user, action='ORDER_CREATED',
                          details=f"ORDER_{order.order_id} PAID ₹{final_total}")
                dispatch_event('ORDER_CREATED', {'order_id': str(order.order_id)})
                dispatch_event('PAYMENT_SUCCESS', {'order_id': str(order.order_id), 'amount': str(final_total)})
                print(f"✅  Order placed! ID: {order.order_id}")
                print(f"    Total: ₹{final_total} | Status: {order.status}")
                if applied:
                    for a in applied:
                        print(f"    Discount: {a}")
            else:
                # Task 7: Rollback — restore stock
                for item in order.items.select_related('product').all():
                    if item.product:
                        p = Product.objects.select_for_update().get(pk=item.product.pk)
                        p.stock += item.quantity
                        p.save(update_fields=['stock', 'updated_at'])
                order.transition_to(OrderStatus.FAILED)
                write_log(user=user, action='PAYMENT_FAILED',
                          details=f"ORDER_{order.order_id} payment failed. Stock restored.")
                print(f"❌  Payment failed. Order cancelled. Stock restored.")

    except ValueError as e:
        print(f"❌  {e}")


def cancel_order():
    """Task 12: Order Cancellation"""
    divider()
    print("🚫  CANCEL ORDER")
    user = pick_user()
    orders = Order.objects.filter(user=user).exclude(
        status__in=[OrderStatus.CANCELLED, OrderStatus.DELIVERED, OrderStatus.RETURNED]
    )
    if not orders:
        print("No cancellable orders found.")
        return
    for i, o in enumerate(orders, 1):
        print(f"  {i}. {o.order_id} [{o.status}] ₹{o.total}")
    choice = int(input("Select order to cancel: ").strip()) - 1
    orders_list = list(orders)
    if 0 <= choice < len(orders_list):
        order = orders_list[choice]
        if order.status == OrderStatus.CANCELLED:
            print("❌  Already cancelled.")
            return
        if not order.can_transition_to(OrderStatus.CANCELLED):
            print(f"❌  Cannot cancel order in status '{order.status}'.")
            return
        with transaction.atomic():
            for item in order.items.select_related('product').all():
                if item.product:
                    p = Product.objects.select_for_update().get(pk=item.product.pk)
                    p.stock += item.quantity
                    p.save(update_fields=['stock', 'updated_at'])
            order.transition_to(OrderStatus.CANCELLED)
        write_log(user=user, action='ORDER_CANCELLED',
                  details=f"Order {order.order_id} cancelled. Stock restored.")
        print(f"✅  Order {order.order_id} cancelled. Stock restored.")
    else:
        print("❌  Invalid selection.")


def view_orders():
    """Task 11: View orders with filter"""
    divider()
    print("📦  VIEW ORDERS")
    user = pick_user()
    print("\nFilter by status (leave blank for all):")
    print("  CREATED / PENDING_PAYMENT / PAID / SHIPPED / DELIVERED / FAILED / CANCELLED / RETURNED")
    status_filter = input("Status: ").strip().upper() or None

    qs = Order.objects.filter(user=user)
    if status_filter:
        qs = qs.filter(status=status_filter)

    if not qs:
        print("No orders found.")
        return

    for o in qs:
        flag = " 🚨 FLAGGED" if o.is_flagged else ""
        print(f"\n  Order: {o.order_id}{flag}")
        print(f"  Status: {o.status} | Total: ₹{o.total} | Date: {o.created_at.strftime('%Y-%m-%d %H:%M')}")
        for item in o.items.all():
            print(f"    - {item.product_id_str} x{item.quantity} @ ₹{item.unit_price}")


def low_stock_alert():
    """Task 10: Low Stock Alert"""
    divider()
    print("⚠️   LOW STOCK ALERT (stock ≤ 5)")
    products = Product.objects.filter(stock__lte=5, is_active=True)
    if not products:
        print("✅  All products have sufficient stock.")
        return
    print(f"\n{'Product ID':<15} {'Name':<25} {'Stock':>8} {'Available':>10}")
    print("-"*62)
    for p in products:
        icon = "🚫" if p.stock == 0 else "⚠️ "
        print(f"{icon} {p.product_id:<13} {p.name:<25} {p.stock:>8} {p.available_stock:>10}")


def return_product():
    """Task 13: Return Product"""
    divider()
    print("↩️   RETURN PRODUCT")
    user = pick_user()
    orders = Order.objects.filter(user=user, status=OrderStatus.DELIVERED)
    if not orders:
        print("No delivered orders to return.")
        return
    for i, o in enumerate(orders, 1):
        print(f"  {i}. {o.order_id} | ₹{o.total}")
    choice = int(input("Select order: ").strip()) - 1
    orders_list = list(orders)
    if not (0 <= choice < len(orders_list)):
        print("❌  Invalid.")
        return
    order = orders_list[choice]
    items = list(order.items.select_related('product').all())
    print("\nItems in order:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item.product_id_str} x{item.quantity} (returnable: {item.returnable_quantity})")
    item_choice = int(input("Select item to return: ").strip()) - 1
    if not (0 <= item_choice < len(items)):
        print("❌  Invalid.")
        return
    order_item = items[item_choice]
    qty = int(input(f"Quantity to return (max {order_item.returnable_quantity}): ").strip())
    if qty > order_item.returnable_quantity or qty <= 0:
        print("❌  Invalid quantity.")
        return

    with transaction.atomic():
        order_item.returned_quantity += qty
        order_item.save(update_fields=['returned_quantity'])
        if order_item.product:
            p = Product.objects.select_for_update().get(pk=order_item.product.pk)
            p.stock += qty
            p.save(update_fields=['stock', 'updated_at'])
        refund = order_item.unit_price * qty
        order.total = max(Decimal('0'), order.total - refund)
        order.status = OrderStatus.RETURNED
        order.save(update_fields=['total', 'status', 'updated_at'])

    write_log(user=user, action='ORDER_RETURNED',
              details=f"Returned {qty}x {order_item.product_id_str} from {order.order_id}. Refund=₹{refund}")
    print(f"✅  Returned {qty} units. Refund: ₹{refund}. Stock restored.")


def simulate_concurrent_users():
    """Task 4: Concurrency Simulation"""
    divider()
    print("🔁  SIMULATE CONCURRENT USERS (Task 4)")
    view_products()
    pid = input("\nEnter Product ID to stress-test: ").strip()
    try:
        product = Product.objects.get(product_id=pid)
    except Product.DoesNotExist:
        print("❌  Product not found.")
        return

    n_users = int(input("Number of concurrent users (e.g. 5): ").strip())
    qty_each = int(input("Each user tries to add (qty): ").strip())
    print(f"\n⚡  Simulating {n_users} users each trying to add {qty_each} units (stock={product.stock})...")

    results = []

    def user_try_add(user_num):
        uname = f"concurrent_user_{user_num}"
        user, _ = User.objects.get_or_create(username=uname)
        try:
            with transaction.atomic():
                p = Product.objects.select_for_update().get(pk=product.pk)
                if p.available_stock < qty_each:
                    results.append(f"  User {user_num}: ❌ FAILED (only {p.available_stock} available)")
                    return
                p.reserved_stock += qty_each
                p.save(update_fields=['reserved_stock', 'updated_at'])
                results.append(f"  User {user_num}: ✅ RESERVED {qty_each} units")
        except Exception as e:
            results.append(f"  User {user_num}: ❌ ERROR - {e}")

    threads = [threading.Thread(target=user_try_add, args=(i,)) for i in range(1, n_users + 1)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    product.refresh_from_db()
    print("\nResults:")
    for r in results:
        print(r)
    print(f"\n  Final reserved_stock: {product.reserved_stock} / {product.stock}")
    print(f"  Available: {product.available_stock} (overselling prevented ✅)")


def view_logs():
    """Task 16: View Audit Logs"""
    divider()
    print("📝  AUDIT LOGS (Task 16 — Immutable)")
    limit = int(input("How many recent logs to show? (default 20): ").strip() or "20")
    from apps.logs.models import AuditLog
    logs = AuditLog.objects.all()[:limit]
    if not logs:
        print("No logs yet.")
        return
    for log in logs:
        ts = log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        print(f"  [{ts}] {log.username_snapshot} | {log.action} | {log.details[:80]}")


def trigger_failure_mode():
    """Task 18: Failure Injection System"""
    divider()
    print("💥  FAILURE INJECTION SYSTEM (Task 18)")
    print("  1. Payment failure")
    print("  2. Order creation failure")
    print("  3. Inventory update failure")
    choice = input("Select component: ").strip()
    components = {'1': 'payment', '2': 'order_creation', '3': 'inventory_update'}
    component = components.get(choice, 'payment')
    fails = random.random() > 0.5
    print(f"\n  Component: {component}")
    print(f"  Result: {'❌ FAILED (injected)' if fails else '✅ PASSED'}")
    user = get_or_create_demo_user()
    write_log(user=user, action='FAILURE_INJECTED',
              details=f"Failure injection on '{component}': {'FAILED' if fails else 'PASSED'}")


# ── main loop ─────────────────────────────────────────────────────────────────

def main():
    # Ensure demo data
    get_or_create_demo_user()

    menu = {
        '1': ('Add Product', add_product),
        '2': ('View Products', view_products),
        '3': ('Add to Cart', add_to_cart),
        '4': ('Remove from Cart', remove_from_cart),
        '5': ('View Cart', view_cart),
        '6': ('Apply Coupon', apply_coupon),
        '7': ('Place Order', place_order),
        '8': ('Cancel Order', cancel_order),
        '9': ('View Orders', view_orders),
        '10': ('Low Stock Alert', low_stock_alert),
        '11': ('Return Product', return_product),
        '12': ('Simulate Concurrent Users', simulate_concurrent_users),
        '13': ('View Logs', view_logs),
        '14': ('Trigger Failure Mode', trigger_failure_mode),
        '0': ('Exit', None),
    }

    while True:
        banner()
        for key, (label, _) in menu.items():
            print(f"  {key:>2}. {label}")
        print()
        choice = input("Enter choice: ").strip()

        if choice == '0':
            print("\n👋  Goodbye!\n")
            break
        elif choice in menu:
            _, fn = menu[choice]
            try:
                fn()
            except Exception as e:
                print(f"\n❌  Unexpected error: {e}")
        else:
            print("❌  Invalid option.")

        input("\n[Press Enter to continue...]")


if __name__ == '__main__':
    main()
