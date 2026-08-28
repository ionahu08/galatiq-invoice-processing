"""Database initialization and schema setup."""

import sqlite3
from pathlib import Path
from typing import Optional


def create_inventory_database(db_path: Path) -> None:
    """
    Create and seed the inventory database.

    Args:
        db_path: Path to the SQLite database file
    """
    # Create connection
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create inventory table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            item_id TEXT PRIMARY KEY,
            item_name TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            unit_price REAL NOT NULL DEFAULT 0.0,
            category TEXT DEFAULT 'General',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Seed with core items referenced in sample invoices
    seed_data = [
        ("WIDGETA", "Widget A", 15, 50.00, "Widgets"),
        ("WIDGETB", "Widget B", 10, 75.00, "Widgets"),
        ("GADGETX", "Gadget X", 5, 150.00, "Gadgets"),
        ("FAKEITEM", "Fake Item", 0, 0.00, "Unknown"),
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO inventory
        (item_id, item_name, stock, unit_price, category)
        VALUES (?, ?, ?, ?, ?)
    """,
        seed_data,
    )

    conn.commit()
    conn.close()


def query_inventory(db_path: Path, item_id: str) -> Optional[dict]:
    """
    Query inventory for an item.

    Args:
        db_path: Path to the SQLite database file
        item_id: Item ID to look up

    Returns:
        Dictionary with item details or None if not found
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM inventory WHERE item_id = ?", (item_id.upper(),))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def check_stock(db_path: Path, item_id: str, quantity: int) -> tuple[bool, str]:
    """
    Check if requested quantity is in stock.

    Args:
        db_path: Path to the SQLite database file
        item_id: Item ID to check
        quantity: Requested quantity

    Returns:
        Tuple of (is_available, message)
    """
    item = query_inventory(db_path, item_id)

    if item is None:
        return False, f"Item '{item_id}' not found in inventory"

    if item["stock"] == 0:
        return False, f"Item '{item['item_name']}' is out of stock"

    if item["stock"] < quantity:
        return (
            False,
            f"Insufficient stock for '{item['item_name']}'. "
            f"Requested: {quantity}, Available: {item['stock']}",
        )

    return True, f"Item available: {item['item_name']} ({item['stock']} in stock)"
