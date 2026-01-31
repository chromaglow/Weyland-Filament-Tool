"""
Weyland Filament Tool - Main Entry Point
Research and generate Bambu Studio filament profiles
"""

import sys
import tkinter as tk
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui.main_window import BambuFilamentApp
from src.utils.logger import get_logger

logger = get_logger()


def main():
    """
    Main entry point for the Weyland Filament Tool
    """
    # Fix for Windows Unicode printing
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 70)
    print("     WEYLAND FILAMENT TOOL")
    print("     Building Better Worlds... One Filament at a Time")
    print("=" * 70)
    print()
    print("Initiating profile generation system...")
    print()

    logger.info("Application starting...")

    # Create and run the application
    try:
        root = tk.Tk()
        app = BambuFilamentApp(root)

        logger.info("GUI initialized successfully")
        print("System online - GUI launched")
        print()

        root.mainloop()

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        print(f"\nERROR: Application failed to start: {e}")
        sys.exit(1)

    logger.info("Application shutdown")


if __name__ == "__main__":
    main()
