"""
Product service - handles product search and retrieval logic
"""
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

from models.product import Product, ProductSearchResult, SetComponent
from database.repository import ProductRepository


class ProductService:
    """Service for product-related operations"""

    def __init__(self, product_repository: ProductRepository):
        self.product_repo = product_repository

    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity score between two strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def find_product(self, query: str, category: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Find products matching the query"""
        try:
            products = self.product_repo.find_products(category)

            # Calculate similarity scores
            matches = []
            for product in products:
                # Calculate similarity with product name
                name_score = self.similarity(query, product.product_name)
                desc_score = self.similarity(query, product.description or "")

                # Use higher score
                match_score = max(name_score, desc_score)

                # Only include if similarity is above threshold
                if match_score > 0.3:
                    product.match_score = round(match_score, 2)
                    matches.append(product)

            # Sort by match score descending
            matches.sort(key=lambda x: x.match_score, reverse=True)

            # Limit results
            matches = matches[:limit]

            return {
                "success": True,
                "matches": [match.to_dict() for match in matches],
                "total_found": len(matches)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "matches": [],
                "total_found": 0
            }

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by ID"""
        try:
            product = self.product_repo.get_product_by_id(product_id)
            return product.to_dict() if product else None
        except Exception:
            return None

    def get_set_components(self, set_product_id: str) -> List[Dict[str, Any]]:
        """Get components of a set product"""
        try:
            components = self.product_repo.get_set_components(set_product_id)
            return [
                {
                    "product_id": comp.product_id,
                    "product_name": comp.product_name,
                    "product_type": comp.product_type,
                    "price": comp.price,
                    "quantity": comp.quantity,
                    "is_default": comp.is_default
                }
                for comp in components
            ]
        except Exception:
            return []

    def get_changeable_options(self, component_type: str) -> List[Dict[str, Any]]:
        """Get available options for component change (sides/beverages)"""
        try:
            options = self.product_repo.get_changeable_options(component_type)
            return [
                {
                    "product_id": option.product_id,
                    "product_name": option.product_name,
                    "price": option.price,
                    "description": option.description
                }
                for option in options
            ]
        except Exception:
            return []

    def get_set_change_options(self, set_product_id: str) -> Dict[str, Any]:
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