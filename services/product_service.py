"""
Product service - handles product search and retrieval logic
"""
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

from models.product import Product, ProductSearchResult, SetComponent
from database.repository import ProductRepository


class ProductService:
    # 제품 관련 비즈니스 로직을 처리하는 서비스 클래스

    def __init__(self, product_repository: ProductRepository):
        # ProductRepository 인스턴스를 주입받아 데이터 접근 계층과 연결
        self.product_repo = product_repository

    def similarity(self, a: str, b: str) -> float:
        # 두 문자열 간의 유사도 점수를 계산 (0.0~1.0 범위)
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def find_product(self, query: str, category: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        # 검색어와 일치하는 제품들을 유사도 점수와 함께 반환
        try:
            # 카테고리별로 제품 데이터 가져오기
            products = self.product_repo.find_products(category)

            # 각 제품에 대해 유사도 점수 계산
            matches = []
            for product in products:
                # 제품명과 설명에 대해 유사도 계산
                name_score = self.similarity(query, product.product_name)
                desc_score = self.similarity(query, product.description or "")

                # 더 높은 점수를 사용
                match_score = max(name_score, desc_score)

                # 임계값 0.3 이상인 경우만 결과에 포함
                if match_score > 0.3:
                    product.match_score = round(match_score, 2)
                    matches.append(product)

            # 유사도 점수 내림차순 정렬
            matches.sort(key=lambda x: x.match_score, reverse=True)

            # 결과 개수 제한
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
        # 제품 ID로 특정 제품의 상세 정보 조회
        try:
            product = self.product_repo.get_product_by_id(product_id)
            return product.to_dict() if product else None
        except Exception:
            return None

    def get_set_components(self, set_product_id: str) -> List[Dict[str, Any]]:
        # 세트 상품의 구성품들(버거, 사이드, 음료) 목록 조회
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
        # 특정 구성품 타입에 대해 변경 가능한 옵션들 조회 (사이드/음료)
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
        # 세트 구성품과 변경 가능한 옵션들을 모두 조회하여 반환
        try:
            # 현재 세트의 기본 구성품들 가져오기
            components = self.get_set_components(set_product_id)
            if not components:
                return {
                    "success": False,
                    "error": "세트 구성품을 찾을 수 없습니다."
                }

            # 구성품들을 타입별로 분류
            set_info = {
                "burger": None,
                "sides": None,
                "beverage": None
            }

            for comp in components:
                comp_type = comp["product_type"]
                if comp_type in set_info:
                    set_info[comp_type] = comp

            # 변경 가능한 사이드와 음료 옵션들 가져오기
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