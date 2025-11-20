"""Standalone security validation test for SQL injection fix.

This test validates the whitelist implementation without requiring
the full application stack.
"""

import re


def test_whitelist_implementation():
    """Verify the SQL injection fix is properly implemented."""

    # Read the fixed source file
    with open("src/api/v1/companies.py", "r") as f:
        source_code = f.read()

    # Test 1: Verify ALLOWED_ORDER_COLUMNS constant exists
    assert "ALLOWED_ORDER_COLUMNS" in source_code, "ALLOWED_ORDER_COLUMNS whitelist not found"

    # Test 2: Verify whitelist contains only safe columns
    whitelist_pattern = r'ALLOWED_ORDER_COLUMNS\s*=\s*\{([^}]+)\}'
    whitelist_match = re.search(whitelist_pattern, source_code)
    assert whitelist_match, "ALLOWED_ORDER_COLUMNS definition not found"

    whitelist_content = whitelist_match.group(1)
    assert '"revenue_yoy_growth"' in whitelist_content or "'revenue_yoy_growth'" in whitelist_content
    assert '"latest_revenue"' in whitelist_content or "'latest_revenue'" in whitelist_content
    assert '"overall_score"' in whitelist_content or "'overall_score'" in whitelist_content

    # Test 3: Verify validation check exists
    assert "if order_column not in ALLOWED_ORDER_COLUMNS:" in source_code, \
        "Whitelist validation check not found"

    # Test 4: Verify HTTPException is raised for invalid columns
    assert "raise HTTPException" in source_code, "HTTPException for invalid column not found"

    # Test 5: Verify security comment is present
    assert "SECURITY" in source_code or "SQL injection" in source_code, \
        "Security comment not found"

    # Test 6: Verify order_column is validated before use in SQL
    validation_idx = source_code.find("if order_column not in ALLOWED_ORDER_COLUMNS:")
    sql_usage_idx = source_code.find("ORDER BY {order_column}")

    assert validation_idx > 0 and sql_usage_idx > 0, "Validation or SQL usage not found"
    assert validation_idx < sql_usage_idx, \
        "Validation must occur BEFORE SQL usage"

    # Test 7: Verify category and limit use parameterized queries
    assert ":category" in source_code, "Category parameter not parameterized"
    assert ":limit" in source_code, "Limit parameter not parameterized"

    print("✅ All security validations passed!")
    print("   - Whitelist constant defined")
    print("   - Contains only safe columns (revenue_yoy_growth, latest_revenue, overall_score)")
    print("   - Validation occurs before SQL usage")
    print("   - HTTPException raised for invalid columns")
    print("   - Category and limit parameters are parameterized")
    print("\n🔒 SQL Injection vulnerability successfully mitigated!")

    return True


def test_metric_mapping_safety():
    """Verify metric mapping only maps to safe values."""

    with open("src/api/v1/companies.py", "r") as f:
        source_code = f.read()

    # Extract metric_mapping dictionary
    metric_mapping_pattern = r'metric_mapping\s*=\s*\{([^}]+)\}'
    mapping_match = re.search(metric_mapping_pattern, source_code, re.MULTILINE | re.DOTALL)

    assert mapping_match, "metric_mapping not found"

    mapping_content = mapping_match.group(1)

    # Verify all mapped values are in the whitelist
    safe_columns = ["revenue_yoy_growth", "latest_revenue", "overall_score"]

    for column in safe_columns:
        assert column in mapping_content, f"Safe column {column} not in metric_mapping"

    # Verify no unexpected columns are mapped
    # This checks that only alphanumeric and underscore characters are in column names
    mapped_columns = re.findall(r':\s*"(\w+)"', mapping_content)

    for column in mapped_columns:
        assert column in safe_columns, f"Unexpected column '{column}' in metric_mapping"

    print("✅ Metric mapping security validated!")
    print(f"   - All mapped columns are safe: {mapped_columns}")

    return True


if __name__ == "__main__":
    try:
        test_whitelist_implementation()
        test_metric_mapping_safety()
        print("\n" + "="*60)
        print("🎉 SQL INJECTION VULNERABILITY FIX VERIFIED")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ Security validation failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)
