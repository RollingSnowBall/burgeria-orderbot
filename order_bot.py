import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from difflib import SequenceMatcher

class BurgeriaOrderBot:
    def __init__(self, db_path: str = "C:\\data\\BurgeriaDB.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize database connection and create tables if needed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create cart table for session management
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Cart (
            cart_item_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            order_type TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            base_price INTEGER NOT NULL,
            modifications TEXT,
            line_total INTEGER NOT NULL,
            special_requests TEXT,
            set_group_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create orders table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Orders (
            order_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            total_amount INTEGER NOT NULL,
            order_type TEXT NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            status TEXT DEFAULT 'pending',
            estimated_time INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create order items table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Order_Items (
            order_item_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            order_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            base_price INTEGER NOT NULL,
            modifications TEXT,
            line_total INTEGER NOT NULL,
            special_requests TEXT,
            set_group_id TEXT,
            FOREIGN KEY(order_id) REFERENCES Orders(order_id)
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity score between two strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        
    def findProduct(self, query: str, category: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Find products matching the query"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Base query
            sql = """
            SELECT product_id, product_name, product_type, price, description, stock_quantity
            FROM Products 
            WHERE stock_quantity > 0
            """
            params = []
            
            # Add category filter if provided
            if category:
                sql += " AND product_type = ?"
                params.append(category)
                
            cursor.execute(sql, params)
            products = cursor.fetchall()
            
            # Calculate similarity scores
            matches = []
            for product in products:
                product_id, product_name, product_type, price, description, stock_quantity = product
                
                # Calculate similarity with product name
                name_score = self.similarity(query, product_name)
                desc_score = self.similarity(query, description or "")
                
                # Use higher score
                match_score = max(name_score, desc_score)
                
                # Only include if similarity is above threshold
                if match_score > 0.3:
                    matches.append({
                        "product_id": product_id,
                        "product_name": product_name,
                        "product_type": product_type,
                        "price": price,
                        "description": description,
                        "stock_quantity": stock_quantity,
                        "match_score": round(match_score, 2)
                    })
            
            # Sort by match score descending
            matches.sort(key=lambda x: x["match_score"], reverse=True)
            
            # Limit results
            matches = matches[:limit]
            
            return {
                "success": True,
                "matches": matches,
                "total_found": len(matches)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "matches": [],
                "total_found": 0
            }
        finally:
            conn.close()
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            SELECT product_id, product_name, product_type, price, description, stock_quantity
            FROM Products WHERE product_id = ?
            """, (product_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    "product_id": result[0],
                    "product_name": result[1],
                    "product_type": result[2],
                    "price": result[3],
                    "description": result[4],
                    "stock_quantity": result[5]
                }
            return None
        finally:
            conn.close()
    
    def get_set_components(self, set_product_id: str) -> List[Dict[str, Any]]:
        """Get components of a set product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            SELECT si.component_product_id, p.product_name, p.product_type, p.price, si.quantity, si.is_default
            FROM Set_Items si
            JOIN Products p ON si.component_product_id = p.product_id
            WHERE si.set_product_id = ?
            """, (set_product_id,))

            components = []
            for row in cursor.fetchall():
                components.append({
                    "product_id": row[0],
                    "product_name": row[1],
                    "product_type": row[2],
                    "price": row[3],
                    "quantity": row[4],
                    "is_default": bool(row[5])
                })

            return components
        finally:
            conn.close()

    def get_changeable_options(self, component_type: str) -> List[Dict[str, Any]]:
        """Get available options for component change (sides/beverages)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            SELECT product_id, product_name, price, description
            FROM Products
            WHERE product_type = ? AND stock_quantity > 0
            ORDER BY price ASC
            """, (component_type,))

            options = []
            for row in cursor.fetchall():
                options.append({
                    "product_id": row[0],
                    "product_name": row[1],
                    "price": row[2],
                    "description": row[3]
                })

            return options
        finally:
            conn.close()

    def getSetChangeOptions(self, set_product_id: str) -> Dict[str, Any]:
        """Get set components and available change options"""
        try:
            # Get current set components
            components = self.get_set_components(set_product_id)
            if not components:
                return {
                    "success": False,
                    "error": "세트 구성품을 찾을 수 없습니다."
                }

            # Separate components by type
            set_info = {
                "burger": None,
                "sides": None,
                "beverage": None
            }

            for comp in components:
                comp_type = comp["product_type"]
                if comp_type in set_info:
                    set_info[comp_type] = comp

            # Get changeable options
            sides_options = self.get_changeable_options("sides")
            beverage_options = self.get_changeable_options("beverage")

            return {
                "success": True,
                "set_product_id": set_product_id,
                "current_components": {
                    "burger": set_info["burger"],
                    "sides": set_info["sides"],
                    "beverage": set_info["beverage"]
                },
                "change_options": {
                    "sides": sides_options,
                    "beverage": beverage_options
                },
                "message": "세트 구성품과 변경 가능한 옵션을 조회했습니다."
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def addToCart(self, session_id: str, product_id: str, quantity: int = 1, 
                  order_type: str = "single", modifications: List[Dict] = None, 
                  special_requests: str = "") -> Dict[str, Any]:
        """Add item to cart with modifications"""
        if modifications is None:
            modifications = []
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get product details
            product = self.get_product_by_id(product_id)
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
                set_components = self.get_set_components(product_id)
                set_component_map = {comp["product_type"]: comp for comp in set_components}

            # Process modifications
            for mod in modifications:
                mod_type = mod.get("type")
                target_id = mod.get("target_product_id")
                new_id = mod.get("new_product_id")

                if mod_type == "add_topping":
                    # Add topping cost
                    topping = self.get_product_by_id(new_id)
                    if topping:
                        modification_cost += topping["price"]
                        modification_details.append({
                            "description": f"{topping['product_name']} 추가",
                            "price_change": topping["price"]
                        })

                elif mod_type == "change_component" and order_type == "set":
                    # Enhanced set component change logic
                    old_component = self.get_product_by_id(target_id)
                    new_component = self.get_product_by_id(new_id)

                    if old_component and new_component:
                        # Validate that we're changing the right type
                        component_type = new_component["product_type"]
                        if component_type in set_component_map:
                            default_component = set_component_map[component_type]
                            # Calculate price difference from default component
                            price_diff = new_component["price"] - default_component["price"]
                            modification_cost += price_diff
                            modification_details.append({
                                "description": f"{component_type.title()}: {default_component['product_name']} → {new_component['product_name']}",
                                "price_change": price_diff
                            })
                        else:
                            # Fallback to old logic
                            price_diff = new_component["price"] - old_component["price"]
                            modification_cost += price_diff
                            modification_details.append({
                                "description": f"{old_component['product_name']} → {new_component['product_name']}",
                                "price_change": price_diff
                            })

                elif mod_type == "size_upgrade":
                    # Size upgrade cost (standard 200 won)
                    modification_cost += 200
                    modification_details.append({
                        "description": "라지사이즈 업그레이드",
                        "price_change": 200
                    })
            
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
                        new_component = self.get_product_by_id(mod.get("new_product_id"))
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
                        new_component = self.get_product_by_id(mod.get("new_product_id"))
                        if new_component:
                            comp_modification_cost = new_component["price"] - component["price"]
                            comp_modification_details.append({
                                "description": f"{comp_type.title()}: {component['product_name']} → {new_component['product_name']}",
                                "price_change": comp_modification_cost
                            })
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

                    cursor.execute("""
                    INSERT INTO Cart (
                        cart_item_id, session_id, product_id, product_name, order_type,
                        quantity, base_price, modifications, line_total, special_requests, set_group_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        comp_cart_item_id, session_id, actual_product_id, f"{display_name} (세트구성)",
                        "set_component", quantity, comp_base_price, json.dumps(comp_modification_details),
                        comp_line_total, special_requests, set_group_id
                    ))

                conn.commit()

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
                        "modifications": modification_details,
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

                # Insert into cart
                cursor.execute("""
                INSERT INTO Cart (
                    cart_item_id, session_id, product_id, product_name, order_type,
                    quantity, base_price, modifications, line_total, special_requests, set_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cart_item_id, session_id, product_id, product["product_name"],
                    order_type, quantity, base_price, json.dumps(modification_details),
                    line_total, special_requests, None
                ))
            
            conn.commit()
            
            return {
                "success": True,
                "cart_item_id": cart_item_id,
                "message": f"{product['product_name']}이(가) 장바구니에 추가되었습니다.",
                "item_details": {
                    "product_name": product["product_name"],
                    "base_price": base_price,
                    "modifications": modification_details,
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
        finally:
            conn.close()
    
    def getCartDetails(self, session_id: str) -> Dict[str, Any]:
        """Get current cart contents for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            SELECT cart_item_id, product_id, product_name, order_type, quantity, base_price,
                   modifications, line_total, special_requests, set_group_id
            FROM Cart WHERE session_id = ?
            ORDER BY created_at
            """, (session_id,))
            
            cart_items = []
            total_quantity = 0
            subtotal = 0
            
            for row in cursor.fetchall():
                cart_item_id, product_id, product_name, order_type, quantity, base_price, modifications_json, line_total, special_requests, set_group_id = row

                modifications = json.loads(modifications_json) if modifications_json else []

                cart_items.append({
                    "cart_item_id": cart_item_id,
                    "product_id": product_id,
                    "product_name": product_name,
                    "order_type": order_type,
                    "quantity": quantity,
                    "base_price": base_price,
                    "modifications": modifications,
                    "line_total": line_total,
                    "special_requests": special_requests,
                    "set_group_id": set_group_id
                })
                
                total_quantity += quantity
                subtotal += line_total
            
            message = f"장바구니에 {len(cart_items)}개의 상품이 있습니다." if cart_items else "장바구니가 비어있습니다."
            
            return {
                "success": True,
                "cart_items": cart_items,
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
        finally:
            conn.close()
    
    def clearCart(self, session_id: str, cart_item_id: Optional[str] = None, 
                  clear_all: bool = False) -> Dict[str, Any]:
        """Clear cart completely or remove specific item"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if clear_all:
                # Remove all items for session
                cursor.execute("SELECT COUNT(*) FROM Cart WHERE session_id = ?", (session_id,))
                removed_items = cursor.fetchone()[0]
                
                cursor.execute("DELETE FROM Cart WHERE session_id = ?", (session_id,))
                
                message = "장바구니가 비워졌습니다."
                
            elif cart_item_id:
                # Remove specific item
                cursor.execute("DELETE FROM Cart WHERE cart_item_id = ? AND session_id = ?", 
                             (cart_item_id, session_id))
                removed_items = cursor.rowcount
                
                if removed_items > 0:
                    message = "선택한 항목이 장바구니에서 제거되었습니다."
                else:
                    return {
                        "success": False,
                        "error": "해당 항목을 찾을 수 없습니다."
                    }
            else:
                return {
                    "success": False,
                    "error": "clear_all 또는 cart_item_id 중 하나를 지정해야 합니다."
                }
            
            # Get remaining items count
            cursor.execute("SELECT COUNT(*) FROM Cart WHERE session_id = ?", (session_id,))
            remaining_items = cursor.fetchone()[0]
            
            conn.commit()
            
            return {
                "success": True,
                "message": message,
                "removed_items": removed_items,
                "remaining_items": remaining_items
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
    
    def updateCartItem(self, session_id: str, cart_item_id: str, 
                      new_quantity: Optional[int] = None, 
                      modifications: Optional[List[Dict]] = None,
                      action: str = "update_quantity") -> Dict[str, Any]:
        """Update cart item quantity or modifications"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current cart item
            cursor.execute("""
            SELECT product_id, product_name, base_price, modifications
            FROM Cart WHERE cart_item_id = ? AND session_id = ?
            """, (cart_item_id, session_id))
            
            result = cursor.fetchone()
            if not result:
                return {
                    "success": False,
                    "error": "장바구니에서 해당 항목을 찾을 수 없습니다."
                }
            
            product_id, product_name, base_price, current_mods_json = result
            
            if action == "update_quantity" and new_quantity:
                # Update quantity and recalculate price
                current_mods = json.loads(current_mods_json) if current_mods_json else []
                modification_cost = sum(mod.get("price_change", 0) for mod in current_mods)
                new_line_total = (base_price + modification_cost) * new_quantity
                
                cursor.execute("""
                UPDATE Cart SET quantity = ?, line_total = ?
                WHERE cart_item_id = ? AND session_id = ?
                """, (new_quantity, new_line_total, cart_item_id, session_id))
                
                conn.commit()
                
                return {
                    "success": True,
                    "updated_item": {
                        "cart_item_id": cart_item_id,
                        "product_name": product_name,
                        "new_quantity": new_quantity,
                        "new_line_total": new_line_total
                    },
                    "message": f"주문 수량이 {new_quantity}개로 변경되었습니다."
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
        finally:
            conn.close()
    
    def processOrder(self, session_id: str, customer_info: Optional[Dict[str, str]] = None,
                    order_type: str = "takeout") -> Dict[str, Any]:
        """Process final order from cart"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get cart details
            cart_details = self.getCartDetails(session_id)
            if not cart_details["success"] or not cart_details["cart_items"]:
                return {
                    "success": False,
                    "error": "장바구니가 비어있습니다."
                }
            
            cart_items = cart_details["cart_items"]
            total_amount = cart_details["summary"]["total_amount"]
            
            # Generate order ID
            order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Calculate estimated time (base 10 minutes + 3 minutes per item)
            estimated_time = 10 + (len(cart_items) * 3)
            
            # Extract customer info
            customer_name = customer_info.get("name", "") if customer_info else ""
            customer_phone = customer_info.get("phone", "") if customer_info else ""
            
            # Insert order
            cursor.execute("""
            INSERT INTO Orders (
                order_id, session_id, total_amount, order_type,
                customer_name, customer_phone, estimated_time, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, session_id, total_amount, order_type,
                customer_name, customer_phone, estimated_time, "confirmed"
            ))

            # Insert order items (주문 상세 정보 저장)
            for cart_item in cart_items:
                order_item_id = str(uuid.uuid4())
                cursor.execute("""
                INSERT INTO Order_Items (
                    order_item_id, order_id, product_id, product_name, order_type,
                    quantity, base_price, modifications, line_total, special_requests, set_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_item_id, order_id, cart_item["product_id"],
                    cart_item["product_name"], cart_item["order_type"],
                    cart_item["quantity"], cart_item["base_price"],
                    json.dumps(cart_item["modifications"]), cart_item["line_total"],
                    cart_item["special_requests"], cart_item.get("set_group_id")
                ))

            # Clear the cart after successful order
            cursor.execute("DELETE FROM Cart WHERE session_id = ?", (session_id,))
            
            conn.commit()
            
            return {
                "success": True,
                "order_id": order_id,
                "estimated_time": estimated_time,
                "total_amount": total_amount,
                "order_summary": {
                    "items": cart_items,
                    "total_quantity": cart_details["summary"]["total_quantity"]
                },
                "message": f"주문이 완료되었습니다. 주문번호: {order_id}, 예상 대기시간: {estimated_time}분"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()

    def getOrderDetails(self, order_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific order"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get order information
            cursor.execute("""
            SELECT order_id, session_id, total_amount, order_type, customer_name,
                   customer_phone, status, estimated_time, created_at
            FROM Orders WHERE order_id = ?
            """, (order_id,))

            order_row = cursor.fetchone()
            if not order_row:
                return {
                    "success": False,
                    "error": "주문을 찾을 수 없습니다."
                }

            # Get order items
            cursor.execute("""
            SELECT order_item_id, product_id, product_name, order_type, quantity,
                   base_price, modifications, line_total, special_requests, set_group_id
            FROM Order_Items WHERE order_id = ?
            ORDER BY set_group_id, order_item_id
            """, (order_id,))

            order_items = []
            for item_row in cursor.fetchall():
                order_item_id, product_id, product_name, order_type, quantity, base_price, modifications_json, line_total, special_requests, set_group_id = item_row

                modifications = json.loads(modifications_json) if modifications_json else []

                order_items.append({
                    "order_item_id": order_item_id,
                    "product_id": product_id,
                    "product_name": product_name,
                    "order_type": order_type,
                    "quantity": quantity,
                    "base_price": base_price,
                    "modifications": modifications,
                    "line_total": line_total,
                    "special_requests": special_requests,
                    "set_group_id": set_group_id
                })

            return {
                "success": True,
                "order_info": {
                    "order_id": order_row[0],
                    "session_id": order_row[1],
                    "total_amount": order_row[2],
                    "order_type": order_row[3],
                    "customer_name": order_row[4],
                    "customer_phone": order_row[5],
                    "status": order_row[6],
                    "estimated_time": order_row[7],
                    "created_at": order_row[8]
                },
                "order_items": order_items,
                "message": f"주문 {order_id} 상세 정보를 조회했습니다."
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()


# Example usage and testing functions
def main():
    """Test the order bot functionality with new set features"""
    bot = BurgeriaOrderBot()
    session_id = "test_session_001"

    print("=== Burgeria Order Bot Test (Updated) ===")

    # Clear any existing cart
    bot.clearCart(session_id, clear_all=True)

    # Check if we have set items data
    print("\n0. 데이터베이스 상태 확인:")
    test_set = bot.get_set_components("G00001")
    if not test_set:
        print("⚠️  Set_Items 테이블에 데이터가 없습니다.")
        print("   다음 명령으로 데이터를 로드하세요:")
        print("   sqlite3 BurgeriaDB.db < SET.sql")
        return
    else:
        print(f"✅ 세트 구성품 {len(test_set)}개 발견")

    # Test 1: Find products
    print("\n1. 제품 검색 테스트:")
    result = bot.findProduct("한우불고기", category="burger")
    print(f"검색 결과: {result['total_found']}개 발견")
    for match in result["matches"]:
        print(f"- {match['product_name']} ({match['product_id']}) - {match['price']}원")

    # Test 2: Set change options test (NEW)
    print("\n2. 세트 변경 옵션 테스트:")
    set_options = bot.getSetChangeOptions("G00001")  # 한우불고기버거 세트
    if set_options["success"]:
        print("현재 세트 구성:")
        for comp_type, comp in set_options["current_components"].items():
            if comp:
                print(f"- {comp_type}: {comp['product_name']} ({comp['price']}원)")

        print("\n변경 가능한 음료 (처음 3개):")
        for beverage in set_options["change_options"]["beverage"][:6]:
            print(f"- {beverage['product_name']} ({beverage['price']}원)")

        print("\n변경 가능한 사이드 (처음 3개):")
        for side in set_options["change_options"]["sides"][:6]:
            print(f"- {side['product_name']} ({side['price']}원)")

    # Test 3: Add set to cart with modifications
    print("\n3. 세트 주문 테스트 (음료 변경):")
    set_result = bot.addToCart(
        session_id=session_id,
        product_id="G00001",  # 한우불고기버거 세트
        quantity=1,
        order_type="set",
        modifications=[{
            "type": "change_component",
            "target_product_id": "C00001",  # 기본 콜라
            "new_product_id": "C00007"      # 아이스티로 변경
        }]
    )
    if set_result.get("success"):
        print(f"세트 추가 결과: {set_result.get('message', '세트가 장바구니에 추가되었습니다.')}")
        print(f"총 금액: {set_result['price_breakdown']['line_total']}원")
        if set_result['item_details']['modifications']:
            print("변경사항:")
            for mod in set_result['item_details']['modifications']:
                print(f"- {mod['description']}: {mod['price_change']:+d}원")
    else:
        print(f"세트 추가 실패: {set_result.get('error', '알 수 없는 오류')}")
        print(f"전체 응답: {set_result}")

    # Test 4: Add single item with topping
    print("\n4. 단품 주문 테스트 (토핑 추가):")
    single_result = bot.addToCart(
        session_id=session_id,
        product_id="A00003",  # 리아 불고기버거
        quantity=1,
        order_type="single",
        modifications=[{
            "type": "add_topping",
            "target_product_id": "A00003",
            "new_product_id": "D00002"  # 치즈토핑
        }]
    )
    if single_result.get("success"):
        print(f"단품 추가 결과: {single_result.get('message', '단품이 장바구니에 추가되었습니다.')}")
        print(f"총 금액: {single_result['price_breakdown']['line_total']}원")
    else:
        print(f"단품 추가 실패: {single_result.get('error', '알 수 없는 오류')}")
        print(f"전체 응답: {single_result}")

    # Test 5: View cart
    print("\n5. 장바구니 조회 테스트:")
    cart = bot.getCartDetails(session_id)
    print(f"장바구니 상태: {cart['message']}")
    print(f"총 금액: {cart['summary']['total_amount']}원")
    print("\n장바구니 상세:")
    for item in cart['cart_items']:
        print(f"- {item['product_name']} x{item['quantity']}: {item['line_total']}원")
        if item['modifications']:
            for mod in item['modifications']:
                print(f"  └ {mod['description']}: {mod['price_change']:+d}원")

    # Test 6: Process order
    print("\n6. 주문 처리 테스트:")
    order_result = bot.processOrder(
        session_id=session_id,
        customer_info={"name": "홍길동", "phone": "010-1234-5678"},
        order_type="takeout"
    )
    order_id = None
    if order_result["success"]:
        print(f"주문 완료: {order_result['message']}")
        order_id = order_result["order_id"]
    else:
        print(f"주문 실패: {order_result['error']}")

    # Test 7: Verify cart is empty after order
    print("\n7. 주문 후 장바구니 확인:")
    empty_cart = bot.getCartDetails(session_id)
    print(f"주문 후 장바구니: {empty_cart['message']}")

    # Test 8: Get order details (NEW)
    if order_id:
        print(f"\n8. 주문 상세 조회 테스트 (주문번호: {order_id}):")
        order_details = bot.getOrderDetails(order_id)
        if order_details["success"]:
            order_info = order_details["order_info"]
            print(f"고객명: {order_info['customer_name']}")
            print(f"전화번호: {order_info['customer_phone']}")
            print(f"총 금액: {order_info['total_amount']}원")
            print(f"예상 시간: {order_info['estimated_time']}분")
            print(f"주문 상태: {order_info['status']}")

            print("\n주문 상품 목록:")
            for item in order_details["order_items"]:
                print(f"- {item['product_name']} x{item['quantity']}: {item['line_total']}원")
                if item['modifications']:
                    for mod in item['modifications']:
                        print(f"  └ {mod['description']}: {mod['price_change']:+d}원")
        else:
            print(f"주문 조회 실패: {order_details['error']}")

    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()