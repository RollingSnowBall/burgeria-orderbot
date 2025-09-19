"""
Main BurgeriaOrderBot class - orchestrates all services
"""
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

from database.connection import DatabaseConnection
from database.repository import ProductRepository, CartRepository, OrderRepository
from services.product_service import ProductService
from services.cart_service import CartService
from services.order_service import OrderService


class BurgeriaOrderBot:
    """Main order bot class that orchestrates all services"""

    def __init__(self, db_path: str = "C:\\\\data\\\\BurgeriaDB.db"):
        # Initialize database connection
        self.db_connection = DatabaseConnection(db_path)

        # Initialize repositories
        self.product_repo = ProductRepository(self.db_connection)
        self.cart_repo = CartRepository(self.db_connection)
        self.order_repo = OrderRepository(self.db_connection)

        # Initialize services
        self.product_service = ProductService(self.product_repo)
        self.cart_service = CartService(self.cart_repo, self.product_service)
        self.order_service = OrderService(self.order_repo, self.cart_service)

    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity score between two strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    # Product-related methods
    def find_product(self, query: str, category: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Find products matching the query"""
        return self.product_service.find_product(query, category, limit)

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by ID"""
        return self.product_service.get_product_by_id(product_id)

    def get_set_components(self, set_product_id: str) -> List[Dict[str, Any]]:
        """Get components of a set product"""
        return self.product_service.get_set_components(set_product_id)

    def get_changeable_options(self, component_type: str) -> List[Dict[str, Any]]:
        """Get available options for component change"""
        return self.product_service.get_changeable_options(component_type)

    def get_set_change_options(self, set_product_id: str) -> Dict[str, Any]:
        """Get set components and available change options"""
        return self.product_service.get_set_change_options(set_product_id)

    # Cart-related methods
    def add_to_cart(self, session_id: str, product_id: str, quantity: int = 1,
                   order_type: str = "single", modifications: List[Dict] = None,
                   special_requests: str = "") -> Dict[str, Any]:
        """Add item to cart with modifications"""
        return self.cart_service.add_to_cart(
            session_id, product_id, quantity, order_type, modifications, special_requests
        )

    def get_cart_details(self, session_id: str) -> Dict[str, Any]:
        """Get current cart contents for a session"""
        return self.cart_service.get_cart_details(session_id)

    def clear_cart(self, session_id: str, cart_item_id: Optional[str] = None,
                  clear_all: bool = False) -> Dict[str, Any]:
        """Clear cart completely or remove specific item"""
        return self.cart_service.clear_cart(session_id, cart_item_id, clear_all)

    def update_cart_item(self, session_id: str, cart_item_id: str,
                        new_quantity: Optional[int] = None,
                        modifications: Optional[List[Dict]] = None,
                        action: str = "update_quantity") -> Dict[str, Any]:
        """Update cart item quantity or modifications"""
        return self.cart_service.update_cart_item(session_id, cart_item_id, new_quantity, action)

    # Order-related methods
    def process_order(self, session_id: str, customer_info: Optional[Dict[str, str]] = None,
                     order_type: str = "takeout") -> Dict[str, Any]:
        """Process final order from cart"""
        return self.order_service.process_order(session_id, customer_info, order_type)

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific order"""
        return self.order_service.get_order_details(order_id)

    # Compatibility methods for backward compatibility with old interface
    def findProduct(self, query: str, category: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Legacy method name - redirects to find_product"""
        return self.find_product(query, category, limit)

    def getSetChangeOptions(self, set_product_id: str) -> Dict[str, Any]:
        """Legacy method name - redirects to get_set_change_options"""
        return self.get_set_change_options(set_product_id)

    def addToCart(self, session_id: str, product_id: str, quantity: int = 1,
                  order_type: str = "single", modifications: List[Dict] = None,
                  special_requests: str = "") -> Dict[str, Any]:
        """Legacy method name - redirects to add_to_cart"""
        return self.add_to_cart(session_id, product_id, quantity, order_type, modifications, special_requests)

    def getCartDetails(self, session_id: str) -> Dict[str, Any]:
        """Legacy method name - redirects to get_cart_details"""
        return self.get_cart_details(session_id)

    def clearCart(self, session_id: str, cart_item_id: Optional[str] = None,
                  clear_all: bool = False) -> Dict[str, Any]:
        """Legacy method name - redirects to clear_cart"""
        return self.clear_cart(session_id, cart_item_id, clear_all)

    def updateCartItem(self, session_id: str, cart_item_id: str,
                      new_quantity: Optional[int] = None,
                      modifications: Optional[List[Dict]] = None,
                      action: str = "update_quantity") -> Dict[str, Any]:
        """Legacy method name - redirects to update_cart_item"""
        return self.update_cart_item(session_id, cart_item_id, new_quantity, modifications, action)

    def processOrder(self, session_id: str, customer_info: Optional[Dict[str, str]] = None,
                    order_type: str = "takeout") -> Dict[str, Any]:
        """Legacy method name - redirects to process_order"""
        return self.process_order(session_id, customer_info, order_type)

    def getOrderDetails(self, order_id: str) -> Dict[str, Any]:
        """Legacy method name - redirects to get_order_details"""
        return self.get_order_details(order_id)