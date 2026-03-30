"""
Management command: python manage.py seed_data
Seeds demo products, users, and sample orders for testing.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from apps.products.models import Product
from apps.cart.models import Cart, CartItem
from apps.logs.utils import write_log


class Command(BaseCommand):
    help = 'Seed demo data for the E-Commerce Order Engine'

    def handle(self, *args, **kwargs):
        self.stdout.write('🌱 Seeding demo data...\n')

        # Create users
        admin, _ = User.objects.get_or_create(username='admin')
        admin.set_password('admin123')
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        self.stdout.write('  ✅ Admin user: admin / admin123')

        users = []
        for i in range(1, 4):
            user, created = User.objects.get_or_create(username=f'user{i}')
            if created:
                user.set_password('pass1234')
                user.save()
            users.append(user)
            self.stdout.write(f'  ✅ User: user{i} / pass1234')

        # Create products
        products_data = [
            ('PHONE-001', 'Smartphone X12', 15999, 50),
            ('LAPTOP-002', 'ProBook 15', 54999, 20),
            ('EARBUDS-003', 'AirBuds Pro', 2999, 100),
            ('TABLET-004', 'Pad Ultra', 24999, 30),
            ('WATCH-005', 'SmartWatch S3', 8999, 15),
            ('CABLE-006', 'USB-C Cable', 299, 4),    # low stock
            ('MOUSE-007', 'Wireless Mouse', 1499, 0), # out of stock
            ('KEYBOARD-008', 'Mech Keyboard', 3499, 8),
        ]

        for pid, name, price, stock in products_data:
            product, created = Product.objects.get_or_create(
                product_id=pid,
                defaults={'name': name, 'price': Decimal(str(price)), 'stock': stock}
            )
            icon = '✅' if created else '⏭️ '
            flag = ' ⚠️  LOW STOCK' if stock <= 5 else ''
            flag += ' 🚫 OUT OF STOCK' if stock == 0 else ''
            self.stdout.write(f'  {icon} Product: {pid} - {name} ₹{price} (stock={stock}){flag}')

        # Seed a cart for user1
        user1 = users[0]
        cart, _ = Cart.objects.get_or_create(user=user1)
        phone = Product.objects.get(product_id='PHONE-001')
        earbuds = Product.objects.get(product_id='EARBUDS-003')
        CartItem.objects.get_or_create(cart=cart, product=phone, defaults={'quantity': 1})
        CartItem.objects.get_or_create(cart=cart, product=earbuds, defaults={'quantity': 2})
        self.stdout.write(f'  ✅ Cart seeded for user1 (1x PHONE-001, 2x EARBUDS-003)')

        write_log(admin, 'SEED_DATA', 'Demo data seeded via management command')

        self.stdout.write('\n🎉 Done! Run the server: python manage.py runserver')
        self.stdout.write('📖 API Docs: http://127.0.0.1:8000/api/docs/')
        self.stdout.write('🖥️  CLI Menu: python cli.py\n')
