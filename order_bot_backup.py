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


def simple_order_system():
    """간단한 채팅 주문 시스템"""
    bot = BurgeriaOrderBot()
    session_id = "customer_session"

    print("버거리아 키오스크")
    print("원하시는 메뉴를 말씀해주세요! (예: '한우불고기버거', '불고기 세트')")
    print("명령어: 장바구니, 주문, 비우기, 종료")

    while True:
        user_input = input("\n무엇을 드릴까요? ").strip()

        if user_input in ["종료", "quit"]:
            print("이용해주셔서 감사합니다!")
            break

        elif user_input in ["장바구니", "cart"]:
            cart = bot.getCartDetails(session_id)
            print(f"\n{cart['message']}")
            if cart['cart_items']:
                for item in cart['cart_items']:
                    print(f"- {item['product_name']} x{item['quantity']}: {item['line_total']:,}원")
                print(f"총 금액: {cart['summary']['total_amount']:,}원")

        elif user_input in ["비우기", "clear"]:
            bot.clearCart(session_id, clear_all=True)
            print("장바구니를 비웠습니다!")

        elif user_input in ["주문", "order"]:
            order_result = bot.processOrder(
                session_id=session_id,
                customer_info=None,
                order_type="takeout"
            )

            if order_result["success"]:
                print(f"주문 완료! {order_result['message']}")
            else:
                print(f"주문 실패: {order_result['error']}")

        else:
            # 자연어 처리로 제품 검색 및 주문 처리
            search_result = bot.findProduct(user_input, limit=5)

            if search_result["success"] and search_result["matches"]:
                # 단품과 세트 분리
                single_items = []
                set_items = []

                for match in search_result["matches"]:
                    if match['product_type'] == 'set':
                        set_items.append(match)
                    else:
                        single_items.append(match)

                print(f"\n'{user_input}' 검색 결과:")

                if single_items:
                    print("\n[단품]")
                    for item in single_items:
                        print(f"- {item['product_name']} ({item['price']:,}원)")

                if set_items:
                    print("\n[세트]")
                    for item in set_items:
                        print(f"- {item['product_name']} ({item['price']:,}원)")

                # 다음 입력 대기
                print("\n어떤 것으로 하시겠어요? (예: '더블 한우불고기버거 세트 2개', '한우불고기버거 단품')")

            else:
                print("해당 메뉴를 찾을 수 없습니다. 다른 키워드로 검색해보세요.")

        # 두 번째 입력 처리 (주문 확정)
        if search_result["success"] and search_result["matches"]:
            order_input = input("").strip()

            if not order_input:
                continue

            # 입력에서 제품 매칭
            selected_item = None
            quantity = 1

            # 수량 추출
            import re
            qty_match = re.search(r'(\d+)개', order_input)
            if qty_match:
                quantity = int(qty_match.group(1))

            # 제품 매칭 (가장 유사한 것 선택)
            best_match = None
            best_score = 0

            all_items = search_result["matches"]
            for item in all_items:
                # 제품명 매칭
                score = bot.similarity(order_input, item['product_name'])
                if score > best_score:
                    best_score = score
                    best_match = item

            if best_match and best_score > 0.3:
                selected_item = best_match
                print(f"\n{selected_item['product_name']} {quantity}개를 선택하셨습니다.")

                # 세트 주문 처리
                if selected_item['product_type'] == 'set':
                    set_options = bot.getSetChangeOptions(selected_item['product_id'])
                    modifications = []

                    if set_options["success"]:
                        print(f"\n{selected_item['product_name']} 기본 구성:")
                        components = set_options["current_components"]
                        for comp_type, comp in components.items():
                            if comp:
                                print(f"- {comp['product_name']}")

                        # 변경사항 확인
                        change_input = input("\n변경하고 싶은 음료나 사이드가 있으시면 말씀해주세요 (없으면 엔터): ").strip()

                        if change_input:
                            beverage_options = set_options["change_options"]["beverage"]
                            sides_options = set_options["change_options"]["sides"]

                            # 음료 변경 매칭
                            for bev in beverage_options:
                                if bot.similarity(change_input, bev['product_name']) > 0.5:
                                    modifications.append({
                                        "type": "change_component",
                                        "target_product_id": components['beverage']['product_id'],
                                        "new_product_id": bev['product_id']
                                    })
                                    print(f"음료를 {bev['product_name']}로 변경합니다.")
                                    break

                            # 사이드 변경 매칭
                            for side in sides_options:
                                if bot.similarity(change_input, side['product_name']) > 0.5:
                                    modifications.append({
                                        "type": "change_component",
                                        "target_product_id": components['sides']['product_id'],
                                        "new_product_id": side['product_id']
                                    })
                                    print(f"사이드를 {side['product_name']}로 변경합니다.")
                                    break

                    # 세트를 장바구니에 추가
                    result = bot.addToCart(
                        session_id=session_id,
                        product_id=selected_item['product_id'],
                        quantity=quantity,
                        order_type="set",
                        modifications=modifications
                    )
                else:
                    # 단품을 장바구니에 추가
                    result = bot.addToCart(
                        session_id=session_id,
                        product_id=selected_item['product_id'],
                        quantity=quantity,
                        order_type="single"
                    )

                if result["success"]:
                    print(f"장바구니에 추가했습니다! {result['message']}")
                    print("계속 주문하시거나 '장바구니'로 확인, '주문'으로 결제하세요.")
                else:
                    print(f"오류: {result['error']}")
            else:
                print("선택하신 상품을 찾을 수 없습니다. 다시 말씀해주세요.")


def ai_order_system():
    """AI 기반 자연어 주문 시스템"""
    bot = BurgeriaOrderBot()
    session_id = "ai_customer_session"

    print("🍔 버거리아 AI 주문 시스템")
    print("자연스럽게 대화하면서 주문하세요!")
    print("예: '추천 메뉴 뭐가 있어요?', '매운 거 말고 담백한 버거 주세요', '콜라 말고 다른 음료로 바꿔주세요'")
    print("명령어: '장바구니', '주문 완료', '종료'\n")

    # 시스템 프롬프트
    system_prompt = """
    당신은 버거리아의 친절한 직원입니다. 고객과 자연스럽게 대화하면서 주문을 받아주세요.
    고객이 메뉴를 물어볼 땐, 우선 단품 기준으로만 대답해주세요. 이후에 고객에게 단품인지, 세트인지 확인하세요.

    주요 역할:
    1. 메뉴 추천 및 상담
    2. 고객 취향에 맞는 제품 제안
    3. 세트 구성 변경 안내
    4. 주문 확인 및 장바구니 관리

    대화 스타일:
    - 친근하고 자연스럽게
    - 고객의 의도를 파악해서 적절한 제품 추천
    - 추가 질문이나 변경 요청에 유연하게 대응
    - 드라이브 스루에서도 사용할 수 있도록 음성 대화에 적합하게

    사용 가능한 함수들:
    - findProduct(query): 제품 검색
    - getSetChangeOptions(product_id): 세트 변경 옵션 조회
    - addToCart(session_id, product_id, quantity, order_type, modifications): 장바구니 추가
    - getCartDetails(session_id): 장바구니 조회
    - clearCart(session_id): 장바구니 비우기

    응답 형식:
    자연스러운 대화 + 필요시 함수 호출 제안
    """

    conversation_history = []

    while True:
        user_input = input("\n고객: ").strip()

        if user_input in ["종료", "quit", "exit"]:
            print("직원: 이용해주셔서 감사합니다! 좋은 하루 되세요!")
            break

        elif user_input in ["장바구니", "cart"]:
            cart = bot.getCartDetails(session_id)
            print(f"\n직원: {cart['message']}")
            if cart['cart_items']:
                print("현재 주문하신 내용:")
                for item in cart['cart_items']:
                    print(f"- {item['product_name']} x{item['quantity']}: {item['line_total']:,}원")
                print(f"총 금액: {cart['summary']['total_amount']:,}원")
                print("추가 주문이나 변경사항이 있으시면 말씀해주세요!")
            continue

        elif user_input in ["주문 완료", "결제", "주문"]:
            order_result = bot.processOrder(
                session_id=session_id,
                customer_info=None,
                order_type="takeout"
            )
            if order_result["success"]:
                print(f"직원: {order_result['message']}")
                print("맛있게 드세요!")
            else:
                print(f"직원: 죄송합니다. {order_result['error']}")
            continue

        # AI 응답 시뮬레이션 (실제로는 LLM API 호출)
        ai_response = simulate_ai_response(user_input, bot, session_id, conversation_history)
        print(f"직원: {ai_response}")

        # 대화 히스토리 저장
        conversation_history.append({"user": user_input, "assistant": ai_response})
        if len(conversation_history) > 10:  # 최근 10개 대화만 유지
            conversation_history.pop(0)


def simulate_ai_response(user_input, bot, session_id, history):
    """AI 응답 시뮬레이션 (실제 구현시 LLM API 호출)"""
    user_lower = user_input.lower()

    # 추천 요청
    if any(word in user_lower for word in ["추천", "뭐가 좋아", "인기", "맛있는"]):
        return "저희 인기 메뉴는 한우불고기버거와 더블 한우불고기버거입니다! 세트로 드시면 더 알찬 구성으로 즐기실 수 있어요. 어떤 걸로 해드릴까요?"

    # 주문 의사 표현 (우선 처리)
    elif any(word in user_lower for word in ["주세요", "할게요", "하나", "개", "드릴게요", "할께", "로 해", "으로 해"]):
        # 주문 처리 로직
        search_result = bot.findProduct(user_input, limit=3)
        if search_result["success"] and search_result["matches"]:

            # 수량 추출
            import re
            qty_match = re.search(r'(\d+)개', user_input)
            quantity = int(qty_match.group(1)) if qty_match else 1

            # 세트 여부 명시적 확인
            if "세트" in user_input:
                # 세트 메뉴 찾기
                set_items = [item for item in search_result["matches"] if item['product_type'] == 'set']
                if set_items:
                    item = set_items[0]
                    order_type = "set"
                else:
                    return "죄송합니다. 해당 세트 메뉴를 찾을 수 없습니다."

            elif "단품" in user_input:
                # 단품 메뉴 찾기
                single_items = [item for item in search_result["matches"] if item['product_type'] != 'set']
                if single_items:
                    item = single_items[0]
                    order_type = "single"
                else:
                    return "죄송합니다. 해당 단품 메뉴를 찾을 수 없습니다."

            else:
                # 세트/단품 미명시 - 단품으로 추론하고 확인
                single_items = [item for item in search_result["matches"] if item['product_type'] != 'set']
                if single_items:
                    item_name = single_items[0]['product_name']
                    return f"{item_name} 단품을 말씀하시는게 맞나요?"
                else:
                    return "어떤 메뉴를 원하시는지 좀 더 구체적으로 말씀해주시겠어요?"

            result = bot.addToCart(
                session_id=session_id,
                product_id=item['product_id'],
                quantity=quantity,
                order_type=order_type
            )

            if result["success"]:
                return f"네! {item['product_name']} {quantity}개 주문 받았습니다. 다른 메뉴도 더 필요하시거나 변경사항이 있으시면 말씀해주세요!"
            else:
                return f"죄송합니다. 주문 처리 중 문제가 발생했어요: {result['error']}"
        else:
            return "어떤 메뉴를 원하시는지 좀 더 구체적으로 말씀해주시겠어요?"

    # 제품 검색 및 제안 (단품 기준) - 단순 문의일 때만
    elif any(word in user_lower for word in ["버거", "불고기", "치킨"]) and "세트" not in user_lower and not any(word in user_lower for word in ["할게", "할께", "주세요", "로 해", "으로 해"]):
        search_result = bot.findProduct(user_input, limit=5)
        if search_result["success"] and search_result["matches"]:
            # 단품만 필터링
            single_items = [item for item in search_result["matches"] if item['product_type'] != 'set']

            if single_items:
                response = "네! 이런 메뉴들이 있어요:\n"
                for item in single_items[:3]:  # 최대 3개까지
                    response += f"- {item['product_name']} ({item['price']:,}원)\n"
                response += "\n어떤 것으로 하시겠어요? 단품으로 드실지 세트로 드실지도 말씀해주세요!"
                return response
            else:
                return "죄송합니다. 해당 메뉴를 찾지 못했어요. 다른 키워드로 말씀해주시면 찾아드릴게요!"
        else:
            return "죄송합니다. 해당 메뉴를 찾지 못했어요. 다른 키워드로 말씀해주시면 찾아드릴게요!"

    # 세트 메뉴 문의
    elif "세트" in user_lower:
        search_result = bot.findProduct(user_input.replace("세트", ""), limit=5)
        if search_result["success"] and search_result["matches"]:
            # 세트만 필터링
            set_items = [item for item in search_result["matches"] if item['product_type'] == 'set']

            if set_items:
                response = "네! 세트 메뉴들이 있어요:\n"
                for item in set_items[:3]:
                    response += f"- {item['product_name']} ({item['price']:,}원)\n"
                response += "\n어떤 세트로 하시겠어요?"
                return response
            else:
                return "죄송합니다. 해당 세트 메뉴를 찾지 못했어요."
        else:
            return "죄송합니다. 해당 세트 메뉴를 찾지 못했어요."

    # 맵기/담백함 등 취향 관련
    elif any(word in user_lower for word in ["매운", "맵지", "순한", "담백"]):
        if "매운" in user_lower or "맵" in user_lower:
            return "매운 걸 원하시는군요! 아쉽게도 저희는 매운 메뉴가 많지 않아서... 한우불고기버거나 리아 불고기버거 같은 담백한 맛은 어떠세요?"
        else:
            return "담백한 맛을 원하시는군요! 한우불고기버거나 리아 불고기버거를 추천드려요. 세트로 하시겠어요?"

    # 음료/사이드 변경 관련
    elif any(word in user_lower for word in ["음료", "콜라", "사이드", "감자"]):
        return "네! 음료는 콜라, 사이다, 아이스티, 아메리카노 등이 있고, 사이드는 포테이토, 치킨너겟, 양파링 등이 있어요. 어떤 걸로 바꿔드릴까요?"

    # 확인 질문에 대한 응답 (맞아, 네, 아니야, 아니오 등)
    elif any(word in user_lower for word in ["맞아", "맞습니다", "네", "예", "응", "맞네", "그래"]):
        # 직전 대화에서 확인 질문이 있었다면 처리
        if history and len(history) > 0:
            last_response = history[-1].get("assistant", "")
            if "말씀하시는게 맞나요?" in last_response:
                # 메뉴명과 타입 추출
                import re
                menu_match = re.search(r'(\S+) (단품|세트)을 말씀하시는게 맞나요?', last_response)
                if menu_match:
                    menu_name = menu_match.group(1)
                    order_type_text = menu_match.group(2)

                    search_result = bot.findProduct(menu_name, limit=3)
                    if search_result["success"] and search_result["matches"]:
                        if order_type_text == "세트":
                            set_items = [item for item in search_result["matches"] if item['product_type'] == 'set']
                            if set_items:
                                item = set_items[0]
                                order_type = "set"
                            else:
                                return "죄송합니다. 해당 세트 메뉴를 찾을 수 없습니다."
                        else:  # 단품
                            single_items = [item for item in search_result["matches"] if item['product_type'] != 'set']
                            if single_items:
                                item = single_items[0]
                                order_type = "single"
                            else:
                                return "죄송합니다. 해당 단품 메뉴를 찾을 수 없습니다."

                        result = bot.addToCart(
                            session_id=session_id,
                            product_id=item['product_id'],
                            quantity=1,
                            order_type=order_type
                        )

                        if result["success"]:
                            return f"네! {item['product_name']} 1개 주문 받았습니다. 다른 메뉴도 더 필요하시거나 변경사항이 있으시면 말씀해주세요!"
                        else:
                            return f"죄송합니다. 주문 처리 중 문제가 발생했어요: {result['error']}"

        return "네, 알겠습니다!"

    # 부정 응답 (아니야, 아니오 등)
    elif any(word in user_lower for word in ["아니야", "아니요", "아니오", "아니", "틀려", "틀렸어"]):
        # 직전 대화에서 확인 질문이 있었다면 다시 물어보기
        if history and len(history) > 0:
            last_response = history[-1].get("assistant", "")
            if "단품을 말씀하시는게 맞나요?" in last_response:
                # 메뉴명 추출
                import re
                menu_match = re.search(r'(\S+) 단품을 말씀하시는게 맞나요?', last_response)
                if menu_match:
                    menu_name = menu_match.group(1)
                    return f"아! 그럼 {menu_name} 세트를 원하시는 건가요?"

        return "어떤 걸 원하시는지 다시 말씀해주세요!"

    # 단품/세트 선택 응답 (세트로 바뀌는 경우)
    elif any(word in user_lower for word in ["단품", "세트"]):
        return "어떤 메뉴를 말씀하시는 건가요?"

    # 기타 질문
    else:
        return "네, 말씀해주세요! 메뉴 추천이나 주문, 궁금한 점이 있으시면 언제든 말씀해주세요."


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
    # AI 기반 자연어 주문 시스템 실행
    ai_order_system()

    # 기존 시스템이 필요할 때는 아래 주석을 해제하세요
    # simple_order_system()
    # main()