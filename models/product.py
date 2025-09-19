"""
Product related data models
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class ProductType(Enum):
    BURGER = "burger"
    SET = "set"
    SIDES = "sides"
    BEVERAGE = "beverage"
    TOPPING = "topping"


@dataclass
class Product:
    """Product data model"""
    product_id: str
    product_name: str
    product_type: str
    price: int
    description: Optional[str] = None
    stock_quantity: int = 0
    match_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_type": self.product_type,
            "price": self.price,
            "description": self.description,
            "stock_quantity": self.stock_quantity,
            "match_score": self.match_score
        }


@dataclass
class SetComponent:
    """Set component data model"""
    product_id: str
    product_name: str
    product_type: str
    price: int
    quantity: int
    is_default: bool


@dataclass
class ProductSearchResult:
    """Product search result"""
    success: bool
    matches: List[Product]
    total_found: int
    error: Optional[str] = None


@dataclass
class Modification:
    """Order modification data model"""
    type: str  # add_topping, change_component, size_upgrade
    target_product_id: Optional[str] = None
    new_product_id: Optional[str] = None
    description: str = ""
    price_change: int = 0