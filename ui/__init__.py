"""
UI package for Burgeria Order Bot
Contains user interface implementations
"""

from .simple_ui import SimpleOrderUI
from .ai_ui import AIOrderUI

__all__ = [
    'SimpleOrderUI', 'AIOrderUI'
]