"""
Basic tests for order bot functionality
"""
import unittest
import tempfile
import os
from core.order_bot import BurgeriaOrderBot


class TestBurgeriaOrderBot(unittest.TestCase):
    """Test cases for BurgeriaOrderBot"""

    def setUp(self):
        """Set up test database"""
        # Create temporary database for testing
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.bot = BurgeriaOrderBot(self.test_db.name)
        self.session_id = "test_session"

    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.test_db.name)

    def test_initialization(self):
        """Test that bot initializes correctly"""
        self.assertIsNotNone(self.bot)
        self.assertIsNotNone(self.bot.db_connection)
        self.assertIsNotNone(self.bot.product_service)
        self.assertIsNotNone(self.bot.cart_service)
        self.assertIsNotNone(self.bot.order_service)

    def test_similarity_calculation(self):
        """Test similarity calculation"""
        # Exact match
        self.assertEqual(self.bot.similarity("burger", "burger"), 1.0)

        # Partial match
        similarity = self.bot.similarity("burger", "hamburger")
        self.assertGreater(similarity, 0.5)

        # No match
        similarity = self.bot.similarity("burger", "pizza")
        self.assertLess(similarity, 0.5)

    def test_empty_cart_details(self):
        """Test getting details of empty cart"""
        result = self.bot.get_cart_details(self.session_id)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["cart_items"]), 0)
        self.assertEqual(result["summary"]["total_amount"], 0)
        self.assertIn("비어있습니다", result["message"])

    def test_clear_empty_cart(self):
        """Test clearing empty cart"""
        result = self.bot.clear_cart(self.session_id, clear_all=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["removed_items"], 0)
        self.assertEqual(result["remaining_items"], 0)

    def test_legacy_method_names(self):
        """Test that legacy method names still work"""
        # Test legacy method names redirect correctly
        result1 = self.bot.findProduct("test")
        result2 = self.bot.find_product("test")

        # Both should return the same structure
        self.assertEqual(set(result1.keys()), set(result2.keys()))

    def test_process_empty_cart_order(self):
        """Test processing order with empty cart"""
        result = self.bot.process_order(self.session_id)

        self.assertFalse(result["success"])
        self.assertIn("비어있습니다", result["error"])


if __name__ == '__main__':
    unittest.main()