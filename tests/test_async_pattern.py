"""Simple test to verify async pattern works without pytest."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_asyncio_run_pattern():
    """Test that asyncio.run() works correctly for dashboard pattern."""

    async def fetch_data():
        # Simulate async database query
        await asyncio.sleep(0.1)
        return {"data": "test"}, {"market": "test"}, {"freshness": "test"}

    # This is the pattern used in the fixed dashboard
    try:
        data, market, freshness = asyncio.run(fetch_data())
        print("✓ asyncio.run() pattern works correctly")
        print(f"  Data: {data}")
        print(f"  Market: {market}")
        print(f"  Freshness: {freshness}")
        return True
    except RuntimeError as e:
        if "coroutine" in str(e).lower():
            print(f"✗ FAILED: Coroutine not awaited - {e}")
            return False
        raise


def test_old_broken_pattern():
    """Show why the old pattern was broken."""

    async def fetch_data():
        await asyncio.sleep(0.1)
        return "test"

    # Old broken pattern - creates and runs event loop manually
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # This pattern can cause issues with nested event loops
        result = loop.run_until_complete(fetch_data())
        loop.close()

        print("✓ Old pattern technically works but is less clean")
        print(f"  Result: {result}")
        return True
    except Exception as e:
        print(f"✗ Old pattern failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing async patterns for Dash callback fix...\n")

    print("1. Testing fixed pattern (asyncio.run):")
    test1 = test_asyncio_run_pattern()

    print("\n2. Testing old pattern (manual event loop):")
    test2 = test_old_broken_pattern()

    print("\n" + "="*50)
    if test1 and test2:
        print("✓ All patterns tested successfully")
        print("\nThe fix uses asyncio.run() which is:")
        print("  - Cleaner and more Pythonic")
        print("  - Handles event loop lifecycle automatically")
        print("  - Better error handling")
        print("  - Works correctly with async context managers")
        sys.exit(0)
    else:
        print("✗ Some patterns failed")
        sys.exit(1)
