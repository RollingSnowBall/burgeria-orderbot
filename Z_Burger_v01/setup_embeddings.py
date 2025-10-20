"""
Task 3.1: 시맨틱 검색을 위한 임베딩 설정 스크립트
1. Products 테이블에 embedding 컬럼 추가
2. 모든 상품에 대한 임베딩 생성 및 저장
"""

import sqlite3
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from db_functions import get_default_db_path
import sys
import io

# Windows 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 환경변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def add_embedding_column(db_path: str):
    """Products 테이블에 embedding 컬럼 추가"""
    print("Step 1: Products 테이블에 embedding 컬럼 추가 중...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # embedding 컬럼이 이미 있는지 확인
        cursor.execute("PRAGMA table_info(Products)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'embedding' not in columns:
            cursor.execute("ALTER TABLE Products ADD COLUMN embedding TEXT")
            conn.commit()
            print("✅ embedding 컬럼 추가 완료!")
        else:
            print("ℹ️  embedding 컬럼이 이미 존재합니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

    finally:
        conn.close()


def get_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """OpenAI API를 사용하여 텍스트의 임베딩 벡터 생성"""
    try:
        response = client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ 임베딩 생성 오류: {e}")
        return None


def generate_product_embeddings(db_path: str):
    """모든 상품에 대한 임베딩 생성 및 저장"""
    print("\nStep 2: 모든 상품에 대한 임베딩 생성 중...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # embedding이 없는 상품들 조회
        cursor.execute("""
            SELECT product_id, product_name, description, product_type
            FROM Products
            WHERE embedding IS NULL
        """)
        products = cursor.fetchall()

        if not products:
            print("ℹ️  모든 상품이 이미 임베딩을 가지고 있습니다.")
            return

        print(f"📋 총 {len(products)}개 상품의 임베딩을 생성합니다...\n")

        for idx, (product_id, product_name, description, product_type) in enumerate(products, 1):
            # 임베딩을 위한 텍스트 생성 (상품명 + 설명 + 타입)
            embedding_text = f"{product_name}. {description or ''} ({product_type})"

            print(f"[{idx}/{len(products)}] {product_name} ... ", end='')

            # 임베딩 생성
            embedding_vector = get_embedding(embedding_text)

            if embedding_vector:
                # JSON 문자열로 변환하여 저장
                embedding_json = json.dumps(embedding_vector)

                cursor.execute("""
                    UPDATE Products
                    SET embedding = ?
                    WHERE product_id = ?
                """, (embedding_json, product_id))

                conn.commit()
                print("✅")
            else:
                print("❌ 실패")

        print(f"\n✅ 총 {len(products)}개 상품의 임베딩 생성 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        conn.rollback()

    finally:
        conn.close()


def verify_embeddings(db_path: str):
    """임베딩이 제대로 저장되었는지 확인"""
    print("\nStep 3: 임베딩 저장 상태 확인 중...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 전체 상품 수
        cursor.execute("SELECT COUNT(*) FROM Products")
        total_count = cursor.fetchone()[0]

        # 임베딩이 있는 상품 수
        cursor.execute("SELECT COUNT(*) FROM Products WHERE embedding IS NOT NULL")
        embedded_count = cursor.fetchone()[0]

        print(f"📊 전체 상품: {total_count}개")
        print(f"📊 임베딩 완료: {embedded_count}개")

        if total_count == embedded_count:
            print("✅ 모든 상품의 임베딩이 완료되었습니다!")
        else:
            print(f"⚠️  임베딩이 누락된 상품이 {total_count - embedded_count}개 있습니다.")

        # 샘플 임베딩 확인
        cursor.execute("""
            SELECT product_id, product_name,
                   SUBSTR(embedding, 1, 50) as embedding_preview
            FROM Products
            WHERE embedding IS NOT NULL
            LIMIT 3
        """)
        samples = cursor.fetchall()

        print("\n📋 임베딩 샘플:")
        for product_id, product_name, embedding_preview in samples:
            print(f"  - {product_name} ({product_id}): {embedding_preview}...")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

    finally:
        conn.close()


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("시맨틱 검색을 위한 임베딩 설정")
    print("=" * 60)

    db_path = get_default_db_path()
    print(f"DB 경로: {db_path}\n")

    # 1. 임베딩 컬럼 추가
    add_embedding_column(db_path)

    # 2. 임베딩 생성 및 저장
    generate_product_embeddings(db_path)

    # 3. 검증
    verify_embeddings(db_path)

    print("\n" + "=" * 60)
    print("🎉 임베딩 설정 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
