/**
 * Database Migration Test Suite
 *
 * Comprehensive tests for database migrations including:
 * - Forward/rollback testing
 * - Idempotency validation
 * - Data integrity checks
 * - TimescaleDB feature validation
 */

const { execSync } = require('child_process');
const pg = require('pg');
const path = require('path');
const fs = require('fs');

// Test database configuration
const TEST_DB_CONFIG = {
  host: process.env.TEST_DB_HOST || 'localhost',
  port: process.env.TEST_DB_PORT || 5432,
  database: process.env.TEST_DB_NAME || 'corporate_intel_test',
  user: process.env.TEST_DB_USER || 'postgres',
  password: process.env.TEST_DB_PASSWORD || 'postgres'
};

describe('Database Migration Tests', () => {
  let client;
  let pool;

  beforeAll(async () => {
    // Create test database if it doesn't exist
    const adminPool = new pg.Pool({
      ...TEST_DB_CONFIG,
      database: 'postgres'
    });

    try {
      await adminPool.query(`DROP DATABASE IF EXISTS ${TEST_DB_CONFIG.database}`);
      await adminPool.query(`CREATE DATABASE ${TEST_DB_CONFIG.database}`);
    } catch (error) {
      console.error('Database setup error:', error);
    } finally {
      await adminPool.end();
    }

    // Connect to test database
    pool = new pg.Pool(TEST_DB_CONFIG);
    client = await pool.connect();

    // Enable TimescaleDB extension
    await client.query('CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE');
  });

  afterAll(async () => {
    if (client) {
      client.release();
    }
    if (pool) {
      await pool.end();
    }
  });

  describe('Migration Up/Down Tests', () => {
    const migrations = getMigrationFiles();

    migrations.forEach((migration) => {
      describe(`Migration: ${migration.name}`, () => {
        let schemaBeforeMigration;
        let dataBeforeMigration;

        beforeEach(async () => {
          // Snapshot schema and data before migration
          schemaBeforeMigration = await captureSchema(client);
          dataBeforeMigration = await captureData(client);
        });

        it('should apply migration successfully (UP)', async () => {
          const upSql = fs.readFileSync(migration.upPath, 'utf8');

          await expect(
            client.query(upSql)
          ).resolves.toBeDefined();

          // Verify migration was recorded
          const result = await client.query(
            `SELECT * FROM schema_migrations WHERE version = $1`,
            [migration.version]
          );
          expect(result.rows.length).toBe(1);
        });

        it('should rollback migration successfully (DOWN)', async () => {
          const downSql = fs.readFileSync(migration.downPath, 'utf8');

          await expect(
            client.query(downSql)
          ).resolves.toBeDefined();

          // Verify schema matches pre-migration state
          const schemaAfterRollback = await captureSchema(client);
          expect(schemaAfterRollback).toEqual(schemaBeforeMigration);
        });

        it('should be idempotent (running twice produces same result)', async () => {
          const upSql = fs.readFileSync(migration.upPath, 'utf8');

          // Run migration first time
          await client.query(upSql);
          const schemaAfterFirst = await captureSchema(client);

          // Run migration second time
          await client.query(upSql);
          const schemaAfterSecond = await captureSchema(client);

          expect(schemaAfterSecond).toEqual(schemaAfterFirst);
        });
      });
    });
  });

  describe('Data Integrity Tests', () => {
    beforeEach(async () => {
      // Setup test data
      await setupTestData(client);
    });

    it('should preserve existing data during migration', async () => {
      const dataBefore = await captureData(client);

      // Run all migrations
      await runAllMigrations(client);

      const dataAfter = await captureData(client);

      // Verify critical data is preserved
      expect(dataAfter.rowCounts).toMatchObject(dataBefore.rowCounts);
    });

    it('should maintain referential integrity', async () => {
      await runAllMigrations(client);

      const integrityCheck = await client.query(`
        SELECT conname, conrelid::regclass, confrelid::regclass
        FROM pg_constraint
        WHERE contype = 'f'
      `);

      expect(integrityCheck.rows.length).toBeGreaterThan(0);

      // Verify no orphaned records
      const orphanCheck = await checkOrphanedRecords(client);
      expect(orphanCheck.hasOrphans).toBe(false);
    });

    it('should validate data types and constraints', async () => {
      await runAllMigrations(client);

      const constraints = await client.query(`
        SELECT
          tc.table_name,
          tc.constraint_name,
          tc.constraint_type,
          kcu.column_name
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = 'public'
      `);

      // Verify primary keys exist on all tables
      const tables = await client.query(`
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
      `);

      tables.rows.forEach(table => {
        const hasPrimaryKey = constraints.rows.some(
          c => c.table_name === table.tablename && c.constraint_type === 'PRIMARY KEY'
        );
        expect(hasPrimaryKey).toBe(true);
      });
    });
  });

  describe('TimescaleDB Features Tests', () => {
    it('should create hypertables correctly', async () => {
      await runAllMigrations(client);

      const hypertables = await client.query(`
        SELECT hypertable_name
        FROM timescaledb_information.hypertables
      `);

      expect(hypertables.rows.length).toBeGreaterThan(0);

      // Verify expected hypertables exist
      const expectedHypertables = ['web_analytics_events', 'research_events'];
      expectedHypertables.forEach(tableName => {
        const exists = hypertables.rows.some(
          h => h.hypertable_name === tableName
        );
        expect(exists).toBe(true);
      });
    });

    it('should configure compression policies', async () => {
      await runAllMigrations(client);

      const compressionPolicies = await client.query(`
        SELECT hypertable_name, compress_after
        FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_compression'
      `);

      expect(compressionPolicies.rows.length).toBeGreaterThan(0);
    });

    it('should configure retention policies', async () => {
      await runAllMigrations(client);

      const retentionPolicies = await client.query(`
        SELECT hypertable_name, drop_after
        FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_retention'
      `);

      expect(retentionPolicies.rows.length).toBeGreaterThan(0);
    });

    it('should create continuous aggregates', async () => {
      await runAllMigrations(client);

      const caggs = await client.query(`
        SELECT view_name, materialization_hypertable_name
        FROM timescaledb_information.continuous_aggregates
      `);

      // Verify continuous aggregates are created
      expect(caggs.rows.length).toBeGreaterThan(0);
    });

    it('should validate chunk intervals', async () => {
      await runAllMigrations(client);

      const chunks = await client.query(`
        SELECT
          hypertable_name,
          chunk_interval
        FROM timescaledb_information.dimensions
      `);

      chunks.rows.forEach(chunk => {
        expect(chunk.chunk_interval).toBeDefined();
        expect(chunk.chunk_interval).not.toBe('0');
      });
    });
  });

  describe('Migration Conflict Detection', () => {
    it('should detect conflicting migrations', async () => {
      const conflicts = await detectMigrationConflicts();
      expect(conflicts.length).toBe(0);
    });

    it('should prevent duplicate migration versions', async () => {
      const migrations = getMigrationFiles();
      const versions = migrations.map(m => m.version);
      const uniqueVersions = new Set(versions);

      expect(versions.length).toBe(uniqueVersions.size);
    });

    it('should validate migration order', async () => {
      const migrations = getMigrationFiles();
      const versions = migrations.map(m => parseInt(m.version));

      for (let i = 1; i < versions.length; i++) {
        expect(versions[i]).toBeGreaterThan(versions[i - 1]);
      }
    });
  });

  describe('Performance Tests', () => {
    it('should complete migrations within acceptable time', async () => {
      const startTime = Date.now();
      await runAllMigrations(client);
      const duration = Date.now() - startTime;

      // Migrations should complete within 30 seconds
      expect(duration).toBeLessThan(30000);
    });

    it('should create indexes efficiently', async () => {
      await runAllMigrations(client);

      const indexes = await client.query(`
        SELECT
          tablename,
          indexname,
          indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
      `);

      // Verify critical indexes exist
      const criticalIndexes = [
        'companies_domain_idx',
        'research_events_time_idx',
        'web_analytics_events_time_idx'
      ];

      criticalIndexes.forEach(indexName => {
        const exists = indexes.rows.some(i => i.indexname === indexName);
        expect(exists).toBe(true);
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid SQL gracefully', async () => {
      await expect(
        client.query('INVALID SQL STATEMENT')
      ).rejects.toThrow();
    });

    it('should rollback on migration failure', async () => {
      const schemaBeforeError = await captureSchema(client);

      try {
        await client.query('BEGIN');
        await client.query('CREATE TABLE test_table (id INT)');
        await client.query('INVALID SQL'); // This will fail
        await client.query('COMMIT');
      } catch (error) {
        await client.query('ROLLBACK');
      }

      const schemaAfterError = await captureSchema(client);
      expect(schemaAfterError).toEqual(schemaBeforeError);
    });
  });
});

// Helper Functions

function getMigrationFiles() {
  const migrationsDir = path.join(__dirname, '../../migrations');
  const files = fs.readdirSync(migrationsDir);

  const migrations = files
    .filter(f => f.endsWith('.up.sql'))
    .map(f => {
      const version = f.split('_')[0];
      const name = f.replace('.up.sql', '');
      return {
        version,
        name,
        upPath: path.join(migrationsDir, f),
        downPath: path.join(migrationsDir, f.replace('.up.sql', '.down.sql'))
      };
    })
    .sort((a, b) => parseInt(a.version) - parseInt(b.version));

  return migrations;
}

async function captureSchema(client) {
  const tables = await client.query(`
    SELECT table_name, column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
  `);

  const indexes = await client.query(`
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
  `);

  const constraints = await client.query(`
    SELECT constraint_name, table_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_schema = 'public'
  `);

  return {
    tables: tables.rows,
    indexes: indexes.rows,
    constraints: constraints.rows
  };
}

async function captureData(client) {
  const tables = await client.query(`
    SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  `);

  const rowCounts = {};
  for (const table of tables.rows) {
    const result = await client.query(`SELECT COUNT(*) FROM ${table.tablename}`);
    rowCounts[table.tablename] = parseInt(result.rows[0].count);
  }

  return { rowCounts };
}

async function setupTestData(client) {
  await client.query(`
    INSERT INTO companies (name, domain, industry)
    VALUES
      ('Test Company 1', 'test1.com', 'Technology'),
      ('Test Company 2', 'test2.com', 'Finance')
    ON CONFLICT (domain) DO NOTHING
  `);
}

async function runAllMigrations(client) {
  const migrations = getMigrationFiles();

  for (const migration of migrations) {
    const upSql = fs.readFileSync(migration.upPath, 'utf8');
    await client.query(upSql);
  }
}

async function checkOrphanedRecords(client) {
  // Check for orphaned records in common foreign key relationships
  const checks = [
    `SELECT COUNT(*) as count FROM research_events
     WHERE company_id NOT IN (SELECT id FROM companies)`,
    `SELECT COUNT(*) as count FROM web_analytics_events
     WHERE company_id NOT IN (SELECT id FROM companies)`
  ];

  for (const check of checks) {
    const result = await client.query(check);
    if (parseInt(result.rows[0].count) > 0) {
      return { hasOrphans: true };
    }
  }

  return { hasOrphans: false };
}

async function detectMigrationConflicts() {
  const migrations = getMigrationFiles();
  const conflicts = [];

  // Check for migrations that modify the same tables
  const tableModifications = new Map();

  for (const migration of migrations) {
    const upSql = fs.readFileSync(migration.upPath, 'utf8');
    const tables = extractTableNames(upSql);

    tables.forEach(table => {
      if (!tableModifications.has(table)) {
        tableModifications.set(table, []);
      }
      tableModifications.get(table).push(migration.version);
    });
  }

  // Report potential conflicts
  tableModifications.forEach((versions, table) => {
    if (versions.length > 1) {
      conflicts.push({
        table,
        migrations: versions,
        message: `Table ${table} is modified by multiple migrations`
      });
    }
  });

  return conflicts;
}

function extractTableNames(sql) {
  const tables = new Set();
  const patterns = [
    /CREATE TABLE (\w+)/gi,
    /ALTER TABLE (\w+)/gi,
    /DROP TABLE (\w+)/gi
  ];

  patterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(sql)) !== null) {
      tables.add(match[1]);
    }
  });

  return Array.from(tables);
}

module.exports = {
  getMigrationFiles,
  captureSchema,
  captureData,
  runAllMigrations,
  checkOrphanedRecords,
  detectMigrationConflicts
};
