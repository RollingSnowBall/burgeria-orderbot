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
            SELECT si.component_product_id, p.product_name, p.price, si.quantity, si.is_default
            FROM Set_Items si
            JOIN Products p ON si.component_product_id = p.product_id
            WHERE si.set_product_id = ?
            """, (set_product_id,))
            
            components = []
            for row in cursor.fetchall():
                components.append({
                    "product_id": row[0],
                    "product_name": row[1],
                    "price": row[2],
                    "quantity": row[3],
                    "is_default": bool(row[4])
                })
            
            return components
        finally:
            conn.close()
    
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
            
            # Process modifications
            for mod in modifications:
                mod_type = mod.get("type")
                target_id = mod.get("target_product_id")
                new_id = mod.get("new_product_id")
                
                if mod_type == "add_topping":
                    # Add topping cost (standard 1000 won)
                    topping = self.get_product_by_id(new_id)
                    if topping:
                        modification_cost += topping["price"]
                        modification_details.append({
                            "description": f"{topping['product_name']} 추가",
                            "price_change": topping["price"]
                        })
                
                elif mod_type == "change_component" and order_type == "set":
                    # Calculate price difference for component change
                    old_component = self.get_product_by_id(target_id)
                    new_component = self.get_product_by_id(new_id)
                    
                    if old_component and new_component:
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
            
            # Calculate final prices
            subtotal = base_price + modification_cost
            line_total = subtotal * quantity
            
            # Generate cart item ID
            cart_item_id = str(uuid.uuid4())
            
            # Insert into cart
            cursor.execute("""
            INSERT INTO Cart (
                cart_item_id, session_id, product_id, product_name, order_type,
                quantity, base_price, modifications, line_total, special_requests
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cart_item_id, session_id, product_id, product["product_name"],
                order_type, quantity, base_price, json.dumps(modification_details),
                line_total, special_requests
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
            SELECT cart_item_id, product_name, order_type, quantity, base_price,
                   modifications, line_total, special_requests
            FROM Cart WHERE session_id = ?
            ORDER BY created_at
            """, (session_id,))
            
            cart_items = []
            total_quantity = 0
            subtotal = 0
            
            for row in cursor.fetchall():
                cart_item_id, product_name, order_type, quantity, base_price, modifications_json, line_total, special_requests = row
                
                modifications = json.loads(modifications_json) if modifications_json else []
                
                cart_items.append({
                    "cart_item_id": cart_item_id,
                    "product_name": product_name,
                    "order_type": order_type,
                    "quantity": quantity,
                    "base_price": base_price,
                    "modifications": modifications,
                    "line_total": line_total,
                    "special_requests": special_requests
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


# Example usage and testing functions
def main():
    """Test the order bot functionality"""
    bot = BurgeriaOrderBot()
    session_id = "test_session_001"
    
    print("=== Burgeria Order Bot Test ===")
    
    # Test 1: Find products
    print("\n1. 제품 검색 테스트:")
    result = bot.findProduct("양념감자가 먹고 싶어요", category="sides")
    print(f"검색 결과: {result['total_found']}개 발견")
    for match in result["matches"]:
        print(f"- {match['product_name']} ({match['product_id']}) - {match['price']}원")
    
    # Test 2: Add to cart
    print("\n2. 장바구니 추가 테스트:")
    if result["matches"]:
        first_product = result["matches"][0]
        add_result = bot.addToCart(
            session_id=session_id,
            product_id=first_product["product_id"],
            quantity=2,
            order_type="single",
            modifications=[{
                "type": "add_topping",
                "target_product_id": first_product["product_id"],
                "new_product_id": "D00002"  # 치즈토핑
            }]
        )
        print(f"추가 결과: {add_result['message']}")
        print(f"총 금액: {add_result['price_breakdown']['line_total']}원")
    
    # Test 3: View cart
    print("\n3. 장바구니 조회 테스트:")
    cart = bot.getCartDetails(session_id)
    print(f"장바구니 상태: {cart['message']}")
    print(f"총 금액: {cart['summary']['total_amount']}원")
    
    # Test 4: Process order
    print("\n4. 주문 처리 테스트:")
    order_result = bot.processOrder(
        session_id=session_id,
        customer_info={"name": "홍길동", "phone": "010-1234-5678"},
        order_type="takeout"
    )
    if order_result["success"]:
        print(f"주문 완료: {order_result['message']}")
    else:
        print(f"주문 실패: {order_result['error']}")

if __name__ == "__main__":
    main()