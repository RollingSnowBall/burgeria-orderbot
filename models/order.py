"""
Order related data models
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from .product import Modification


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class OrderItem:
    """Order item data model"""
    order_item_id: str
    order_id: str
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
            "order_item_id": self.order_item_id,
            "order_id": self.order_id,
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
class CustomerInfo:
    """Customer information"""
    name: str = ""
    phone: str = ""


@dataclass
class Order:
    """Order data model"""
    order_id: str
    session_id: str
    total_amount: int
    order_type: str
    customer_name: str
    customer_phone: str
    status: OrderStatus
    estimated_time: int
    created_at: str
    items: List[OrderItem]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "order_id": self.order_id,
            "session_id": self.session_id,
            "total_amount": self.total_amount,
            "order_type": self.order_type,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "status": self.status.value,
            "estimated_time": self.estimated_time,
            "created_at": self.created_at,
            "items": [item.to_dict() for item in self.items]
        }