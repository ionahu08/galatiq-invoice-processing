"""Database utilities for inventory management."""

from src.database.setup import (
    check_stock,
    create_inventory_database,
    query_inventory,
)

__all__ = ["create_inventory_database", "query_inventory", "check_stock"]
