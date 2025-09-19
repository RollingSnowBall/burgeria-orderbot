"""
Cart related data models
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from .product import Modification


@dataclass
class CartItem:
    """Cart item data model"""
    cart_item_id: str
    product_id: str
    product_name: str
    order_type: str
    quantity: int
    base_price: int
    modifications: List[Modification]
    line_total: int
    special_requests: str = ""
    set_group_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "cart_item_id": self.cart_item_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "base_price": self.base_price,
            "modifications": [mod.__dict__ for mod in self.modifications],
            "line_total": self.line_total,
            "special_requests": self.special_requests,
            "set_group_id": self.set_group_id
        }


@dataclass
class CartSummary:
    """Cart summary data model"""
    total_items: int
    total_quantity: int
    subtotal: int
    tax: int
    total_amount: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_items": self.total_items,
            "total_quantity": self.total_quantity,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "total_amount": self.total_amount
        }


@dataclass
class CartDetails:
    """Complete cart details"""
    success: bool
    cart_items: List[CartItem]
    summary: CartSummary
    message: str
    error: Optional[str] = None