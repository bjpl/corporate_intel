# Migration Tests

Comprehensive test suite for database migrations.

## Quick Start

```bash
# Install dependencies
npm install

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode for development
npm run test:watch

# Validate migrations
npm run validate
```

## Test Structure

```
tests/migrations/
├── migration.test.js       # Main migration test suite
├── package.json           # Test dependencies and scripts
├── jest.config.js         # Jest configuration
├── setup.js               # Test environment setup
└── README.md             # This file
```

## Test Categories

### 1. Migration Up/Down Tests
- Tests forward migration (up)
- Tests backward migration (down)
- Verifies idempotency

### 2. Data Integrity Tests
- Validates data preservation
- Checks referential integrity
- Verifies constraints

### 3. TimescaleDB Features Tests
- Hypertable creation
- Compression policies
- Retention policies
- Continuous aggregates

### 4. Performance Tests
- Migration duration
- Index creation efficiency
- Query performance

### 5. Conflict Detection
- Duplicate version detection
- Migration order validation
- Schema conflict detection

## Environment Variables

```bash
TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_NAME=corporate_intel_test
TEST_DB_USER=postgres
TEST_DB_PASSWORD=postgres
```

## Running Specific Tests

```bash
# Run specific test file
npm test migration.test.js

# Run specific test suite
npm test -- --testNamePattern="Migration Up/Down"

# Run tests matching pattern
npm test -- --testNamePattern="TimescaleDB"
```

## Coverage Requirements

Minimum coverage thresholds:
- Branches: 80%
- Functions: 80%
- Lines: 80%
- Statements: 80%

## CI/CD Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Changes to migration files

See `.github/workflows/test-migrations.yml` for details.

## Troubleshooting

### Tests Fail to Connect to Database

1. Ensure PostgreSQL is running:
```bash
pg_isready -h localhost -p 5432
```

2. Create test database:
```bash
createdb corporate_intel_test
```

3. Enable TimescaleDB:
```bash
psql -d corporate_intel_test -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
```

### Tests Timeout

Increase timeout in `jest.config.js`:
```javascript
testTimeout: 60000  // 60 seconds
```

### Permission Errors

Grant necessary permissions:
```bash
psql -d corporate_intel_test -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;"
```

## Best Practices

1. **Always test migrations locally before committing**
2. **Run full test suite, not just unit tests**
3. **Verify rollback procedures work**
4. **Check test coverage remains above 80%**
5. **Review test output for warnings**

## Related Documentation

- [Migration Testing Guide](../../docs/MIGRATION_TESTING.md)
- [Database Schema](../../docs/database/)
- [CI/CD Workflows](../../.github/workflows/)
