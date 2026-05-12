"""Mock commerce tools used by seeded sandbox agents."""

from __future__ import annotations

import re

from agent_runtime.infrastructure.tools.orders import MOCK_ORDERS, get_order_status

MOCK_PRODUCTS = [
    {"sku": "PRD-001", "name": "Laptop Pro 14", "category": "laptop", "price": "$1499", "stock": "in stock"},
    {"sku": "PRD-002", "name": "Laptop Air 13", "category": "laptop", "price": "$1099", "stock": "in stock"},
    {"sku": "PRD-003", "name": "Wireless Mouse", "category": "accessories", "price": "$39", "stock": "low stock"},
    {"sku": "PRD-004", "name": "Mechanical Keyboard", "category": "accessories", "price": "$129", "stock": "in stock"},
    {"sku": "PRD-005", "name": "USB-C Dock", "category": "accessories", "price": "$89", "stock": "out of stock"},
]

MOCK_USERS = [
    {"user_id": "USR-001", "name": "Ava Chen", "email": "ava.chen@example.com", "phone": "+1-415-555-0101"},
    {"user_id": "USR-002", "name": "Marcus Hill", "email": "marcus.hill@example.com", "phone": "+1-212-555-0112"},
    {"user_id": "USR-003", "name": "Priya Patel", "email": "priya.patel@example.com", "phone": "+1-646-555-0178"},
]


def get_orders(order_id: str = "", customer_id: str = "") -> str:
    """Return one order or a compact list of known orders."""
    normalized_order_id = order_id.strip().upper()
    if normalized_order_id:
        return get_order_status(normalized_order_id)

    lines = ["Orders:"]
    for order in MOCK_ORDERS.values():
        lines.append(
            f"- {order['order_id']} | {order['customer_name']} | {order['status']} | {', '.join(order['items'])}"
        )

    if customer_id:
        lines.append(f"Customer filter requested: {customer_id}")
    return "\n".join(lines)


def search_products(query: str) -> str:
    """Search mock products by keyword/category."""
    query_lower = query.lower().strip()
    matches = [
        product
        for product in MOCK_PRODUCTS
        if query_lower in product["name"].lower() or query_lower in product["category"].lower()
    ]

    if not matches:
        return f"No products matched '{query}'."

    lines = [f"Products matching '{query}':"]
    for product in matches[:5]:
        lines.append(
            f"- {product['sku']} | {product['name']} | {product['category']} | {product['price']} | {product['stock']}"
        )
    return "\n".join(lines)


def get_users(query: str = "") -> str:
    """Return mock users, optionally filtered by a free-text query."""
    query_lower = query.lower().strip()
    matches = [
        user
        for user in MOCK_USERS
        if not query_lower
        or query_lower in user["user_id"].lower()
        or query_lower in user["name"].lower()
        or query_lower in user["email"].lower()
    ]

    if not matches:
        return f"No users matched '{query}'."

    lines = ["Users:"]
    for user in matches:
        lines.append(f"- {user['user_id']} | {user['name']} | {user['email']} | {user['phone']}")
    return "\n".join(lines)


def update_order(order_id: str, status: str, note: str = "") -> str:
    """Pretend to update an order and return a confirmation summary."""
    normalized_order_id = order_id.strip().upper()
    if normalized_order_id not in MOCK_ORDERS:
        return f"Order {normalized_order_id} not found."

    normalized_status = status.strip().lower()
    MOCK_ORDERS[normalized_order_id]["status"] = normalized_status
    summary = f"Order {normalized_order_id} updated to status '{normalized_status}'."
    if note:
        summary += f" Note: {note.strip()}"
    return summary


def update_user(user_id: str, email: str = "", name: str = "", phone: str = "") -> str:
    """Pretend to update a user record and return the new field values."""
    normalized_user_id = user_id.strip().upper()
    user = next((candidate for candidate in MOCK_USERS if candidate["user_id"] == normalized_user_id), None)
    if user is None:
        return f"User {normalized_user_id} not found."

    if email:
        user["email"] = email.strip()
    if name:
        user["name"] = name.strip()
    if phone:
        user["phone"] = phone.strip()

    return f"User {normalized_user_id} updated: name={user['name']}, email={user['email']}, phone={user['phone']}"


def extract_status_from_message(message: str) -> str | None:
    """Best-effort order status extraction for deterministic routing."""
    match = re.search(r"\b(processing|shipped|delivered|cancelled|returned)\b", message.lower())
    if match:
        return match.group(1)
    return None
