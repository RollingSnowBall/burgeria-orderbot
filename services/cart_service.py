"""
Cart service - handles cart operations
"""
import uuid
import json
from typing import Dict, List, Any, Optional

from models.cart import CartItem, CartSummary, CartDetails
from models.product import Modification
from database.repository import CartRepository
from .product_service import ProductService


class CartService:
    """Service for cart-related operations"""

    def __init__(self, cart_repository: CartRepository, product_service: ProductService):
        self.cart_repo = cart_repository
        self.product_service = product_service

    def add_to_cart(self, session_id: str, product_id: str, quantity: int = 1,
                   order_type: str = "single", modifications: List[Dict] = None,
                   special_requests: str = "") -> Dict[str, Any]:
        """Add item to cart with modifications"""
        if modifications is None:
            modifications = []

        try:
            # Get product details
            product = self.product_service.get_product_by_id(product_id)
            if not product:
                return {
                    "success": False,
                    "error": "Product not found"
                }

            # Check stock
            if product["stock_quantity"] < quantity:
                return {
                    "success": False,
                    "error": f"Insufficient stock. Available: {product['stock_quantity']}"
                }

            base_price = product["price"]
            modification_cost = 0
            modification_details = []

            # Special handling for set orders
            set_component_map = {}
            if order_type == "set" and product["product_type"] == "set":
                # Get set components for validation
                set_components = self.product_service.get_set_components(product_id)
                set_component_map = {comp["product_type"]: comp for comp in set_components}

            # Process modifications
            for mod in modifications:
                mod_type = mod.get("type")
                target_id = mod.get("target_product_id")
                new_id = mod.get("new_product_id")

                if mod_type == "add_topping":
                    # Add topping cost
                    topping = self.product_service.get_product_by_id(new_id)
                    if topping:
                        modification_cost += topping["price"]
                        modification_details.append(Modification(
                            type=mod_type,
                            target_product_id=target_id,
                            new_product_id=new_id,
                            description=f"{topping['product_name']} 추가",
                            price_change=topping["price"]
                        ))

                elif mod_type == "change_component" and order_type == "set":
                    # Enhanced set component change logic
                    old_component = self.product_service.get_product_by_id(target_id)
                    new_component = self.product_service.get_product_by_id(new_id)

                    if old_component and new_component:
                        # Validate that we're changing the right type
                        component_type = new_component["product_type"]
                        if component_type in set_component_map:
                            default_component = set_component_map[component_type]
                            # Calculate price difference from default component
                            price_diff = new_component["price"] - default_component["price"]
                            modification_cost += price_diff
                            modification_details.append(Modification(
                                type=mod_type,
                                target_product_id=target_id,
                                new_product_id=new_id,
                                description=f"{component_type.title()}: {default_component['product_name']} → {new_component['product_name']}",
                                price_change=price_diff
                            ))
                        else:
                            # Fallback to old logic
                            price_diff = new_component["price"] - old_component["price"]
                            modification_cost += price_diff
                            modification_details.append(Modification(
                                type=mod_type,
                                target_product_id=target_id,
                                new_product_id=new_id,
                                description=f"{old_component['product_name']} → {new_component['product_name']}",
                                price_change=price_diff
                            ))

                elif mod_type == "size_upgrade":
                    # Size upgrade cost (standard 200 won)
                    modification_cost += 200
                    modification_details.append(Modification(
                        type=mod_type,
                        description="라지사이즈 업그레이드",
                        price_change=200
                    ))

            # Handle set orders - save components individually
            if order_type == "set" and product["product_type"] == "set":
                if not set_component_map:
                    return {
                        "success": False,
                        "error": f"세트 구성품을 찾을 수 없습니다: {product_id}"
                    }

                set_group_id = str(uuid.uuid4())
                component_modifications = {}

                # Map modifications to components
                for mod in modifications:
                    if mod.get("type") == "change_component":
                        new_component = self.product_service.get_product_by_id(mod.get("new_product_id"))
                        if new_component:
                            component_modifications[new_component["product_type"]] = mod

                # Save each component individually
                for comp_type, component in set_component_map.items():
                    comp_cart_item_id = str(uuid.uuid4())
                    comp_base_price = component["price"]
                    comp_modification_details = []
                    comp_modification_cost = 0

                    # Check if this component was modified
                    if comp_type in component_modifications:
                        mod = component_modifications[comp_type]
                        new_component = self.product_service.get_product_by_id(mod.get("new_product_id"))
                        if new_component:
                            comp_modification_cost = new_component["price"] - component["price"]
                            comp_modification_details.append(Modification(
                                type="change_component",
                                description=f"{comp_type.title()}: {component['product_name']} → {new_component['product_name']}",
                                price_change=comp_modification_cost
                            ))
                            # Use new component for display
                            display_name = new_component["product_name"]
                            actual_product_id = new_component["product_id"]
                            actual_price = new_component["price"]
                        else:
                            display_name = component["product_name"]
                            actual_product_id = component["product_id"]
                            actual_price = component["price"]
                    else:
                        display_name = component["product_name"]
                        actual_product_id = component["product_id"]
                        actual_price = component["price"]

                    comp_line_total = actual_price * quantity

                    cart_item = CartItem(
                        cart_item_id=comp_cart_item_id,
                        product_id=actual_product_id,
                        product_name=f"{display_name} (세트구성)",
                        order_type="set_component",
                        quantity=quantity,
                        base_price=comp_base_price,
                        modifications=comp_modification_details,
                        line_total=comp_line_total,
                        special_requests=special_requests,
                        set_group_id=set_group_id
                    )

                    if not self.cart_repo.add_item(cart_item, session_id):
                        return {
                            "success": False,
                            "error": "장바구니 추가 중 오류가 발생했습니다."
                        }

                # Calculate total for response
                total_price = sum(comp["price"] for comp in set_component_map.values()) + modification_cost
                line_total = total_price * quantity

                return {
                    "success": True,
                    "cart_item_id": set_group_id,
                    "message": f"{product['product_name']}이(가) 장바구니에 추가되었습니다.",
                    "item_details": {
                        "product_name": product["product_name"],
                        "base_price": base_price,
                        "modifications": [mod.__dict__ for mod in modification_details],
                        "total_price": total_price,
                        "quantity": quantity,
                        "components": list(set_component_map.values())
                    },
                    "price_breakdown": {
                        "base_price": base_price,
                        "modification_cost": modification_cost,
                        "subtotal": total_price,
                        "quantity": quantity,
                        "line_total": line_total
                    }
                }

            else:
                # Regular single item order
                subtotal = base_price + modification_cost
                line_total = subtotal * quantity

                # Generate cart item ID
                cart_item_id = str(uuid.uuid4())

                cart_item = CartItem(
                    cart_item_id=cart_item_id,
                    product_id=product_id,
                    product_name=product["product_name"],
                    order_type=order_type,
                    quantity=quantity,
                    base_price=base_price,
                    modifications=modification_details,
                    line_total=line_total,
                    special_requests=special_requests
                )

                if not self.cart_repo.add_item(cart_item, session_id):
                    return {
                        "success": False,
                        "error": "장바구니 추가 중 오류가 발생했습니다."
                    }

                return {
                    "success": True,
                    "cart_item_id": cart_item_id,
                    "message": f"{product['product_name']}이(가) 장바구니에 추가되었습니다.",
                    "item_details": {
                        "product_name": product["product_name"],
                        "base_price": base_price,
                        "modifications": [mod.__dict__ for mod in modification_details],
                        "total_price": subtotal,
                        "quantity": quantity
                    },
                    "price_breakdown": {
                        "base_price": base_price,
                        "modification_cost": modification_cost,
                        "subtotal": subtotal,
                        "quantity": quantity,
                        "line_total": line_total
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_cart_details(self, session_id: str) -> Dict[str, Any]:
        """Get current cart contents for a session"""
        try:
            cart_items = self.cart_repo.get_cart_items(session_id)

            total_quantity = 0
            subtotal = 0

            cart_items_dict = []
            for item in cart_items:
                cart_items_dict.append(item.to_dict())
                total_quantity += item.quantity
                subtotal += item.line_total

            message = f"장바구니에 {len(cart_items)}개의 상품이 있습니다." if cart_items else "장바구니가 비어있습니다."

            return {
                "success": True,
                "cart_items": cart_items_dict,
                "summary": {
                    "total_items": len(cart_items),
                    "total_quantity": total_quantity,
                    "subtotal": subtotal,
                    "tax": 0,
                    "total_amount": subtotal
                },
                "message": message
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "cart_items": [],
                "summary": {
                    "total_items": 0,
                    "total_quantity": 0,
                    "subtotal": 0,
                    "tax": 0,
                    "total_amount": 0
                },
                "message": "장바구니 조회 중 오류가 발생했습니다."
            }

    def clear_cart(self, session_id: str, cart_item_id: Optional[str] = None,
                  clear_all: bool = False) -> Dict[str, Any]:
        """Clear cart completely or remove specific item"""
        try:
            if clear_all:
                result = self.cart_repo.clear_cart(session_id)
                if result["success"]:
                    result["message"] = "장바구니가 비워졌습니다."
                return result

            elif cart_item_id:
                result = self.cart_repo.clear_cart(session_id, cart_item_id)
                if result["success"]:
                    if result["removed_items"] > 0:
                        result["message"] = "선택한 항목이 장바구니에서 제거되었습니다."
                    else:
                        return {
                            "success": False,
                            "error": "해당 항목을 찾을 수 없습니다."
                        }
                return result

            else:
                return {
                    "success": False,
                    "error": "clear_all 또는 cart_item_id 중 하나를 지정해야 합니다."
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def update_cart_item(self, session_id: str, cart_item_id: str,
                        new_quantity: Optional[int] = None,
                        action: str = "update_quantity") -> Dict[str, Any]:
        """Update cart item quantity"""
        try:
            if action == "update_quantity" and new_quantity:
                if self.cart_repo.update_cart_item(session_id, cart_item_id, new_quantity):
                    return {
                        "success": True,
                        "message": f"주문 수량이 {new_quantity}개로 변경되었습니다."
                    }
                else:
                    return {
                        "success": False,
                        "error": "장바구니에서 해당 항목을 찾을 수 없습니다."
                    }
            else:
                return {
                    "success": False,
                    "error": "지원하지 않는 업데이트 작업입니다."
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }