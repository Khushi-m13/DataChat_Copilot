"""Creates a small SQLite database (sample.db) for testing the DataChat Copilot."""
import random
import sqlite3
from datetime import date, timedelta

random.seed(42)
conn = sqlite3.connect("sample.db")
cur = conn.cursor()

cur.executescript(
    """
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS customers;

    CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        city TEXT NOT NULL
    );
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL
    );
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity INTEGER NOT NULL,
        order_date TEXT NOT NULL  -- ISO format YYYY-MM-DD
    );
    """
)

customers = [
    (1, "Asha Patil", "Pune"), (2, "Rohan Mehta", "Mumbai"),
    (3, "Neha Singh", "Delhi"), (4, "Vikram Rao", "Bengaluru"),
    (5, "Sana Khan", "Hyderabad"), (6, "Arjun Nair", "Chennai"),
]
products = [
    (1, "Laptop", "Electronics", 55000.0), (2, "Headphones", "Electronics", 2500.0),
    (3, "Notebook", "Stationery", 120.0), (4, "Pen Pack", "Stationery", 80.0),
    (5, "Office Chair", "Furniture", 7500.0), (6, "Desk", "Furniture", 12000.0),
]
cur.executemany("INSERT INTO customers VALUES (?,?,?)", customers)
cur.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

start = date(2026, 1, 1)
orders = []
for i in range(1, 301):
    d = start + timedelta(days=random.randint(0, 270))
    orders.append((i, random.choice(customers)[0], random.choice(products)[0],
                   random.randint(1, 5), d.isoformat()))
cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", orders)

conn.commit()
conn.close()
print("Created sample.db with customers, products and orders.")
