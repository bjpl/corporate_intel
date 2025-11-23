-- Update proper companies to include their CIK values
-- This ensures future SEC ingestion will find them by CIK

BEGIN;

\echo '=== Updating companies with CIK values ==='

-- Update CIK values for companies that now have SEC filings
UPDATE companies SET cik = '0000730464' WHERE ticker = 'LRN';
UPDATE companies SET cik = '0001013934' WHERE ticker = 'STRA';
UPDATE companies SET cik = '0001364954' WHERE ticker = 'CHGG';
UPDATE companies SET cik = '0001434588' WHERE ticker = 'PRDO';
UPDATE companies SET cik = '0001562088' WHERE ticker = 'DUOL';
UPDATE companies SET cik = '0001651562' WHERE ticker = 'COUR';

\echo ''
\echo '=== Verification: Companies with SEC filings now have CIKs ==='
SELECT ticker, name, cik,
       (SELECT COUNT(*) FROM sec_filings WHERE company_id = companies.id) as filing_count
FROM companies
WHERE ticker IN ('LRN', 'STRA', 'CHGG', 'PRDO', 'DUOL', 'COUR')
ORDER BY ticker;

COMMIT;

\echo ''
\echo '=== CIK values updated successfully ==='
