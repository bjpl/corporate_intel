# Circuit Breaker Pattern Implementation

## Overview

This document describes the implementation of the Circuit Breaker pattern for external API calls in the Corporate Intelligence Platform. The circuit breaker pattern prevents cascading failures when external APIs (SEC EDGAR, Alpha Vantage, Yahoo Finance) become unavailable or slow.

## Problem Statement

External APIs have no inherent protection against cascading failures. When an API experiences an outage:
- Requests continue to be sent, consuming resources
- Timeouts and retries compound the problem
- System resources are exhausted waiting for failed requests
- User experience degrades significantly
- Difficult to recover from failures gracefully

## Solution: Circuit Breaker Pattern

The circuit breaker acts like an electrical circuit breaker, automatically "opening" when too many failures occur, preventing further requests until the service recovers.

### Circuit States

1. **CLOSED** (Normal Operation)
   - All requests pass through to the external API
   - Failures are counted
   - Circuit opens when failure threshold is reached

2. **OPEN** (Service Unavailable)
   - All requests fail immediately with `CircuitBreakerError`
   - No requests are sent to the external API
   - Prevents cascading failures and resource exhaustion
   - After timeout period, circuit transitions to HALF_OPEN

3. **HALF_OPEN** (Testing Recovery)
   - Limited requests are allowed through to test if service recovered
   - If requests succeed, circuit closes
   - If requests fail, circuit opens again

## Implementation Details

### Configuration

Located in `/home/user/corporate_intel/src/core/circuit_breaker.py`

#### Alpha Vantage Circuit Breaker
```python
alpha_vantage_breaker = CircuitBreaker(
    fail_max=5,              # Open after 5 consecutive failures
    timeout_duration=60,     # Wait 60 seconds before retry
    name="alpha_vantage"
)
```

**Rationale:**
- Free tier has strict rate limits (5 calls/min)
- Failures often indicate rate limiting or API key issues
- 60-second timeout aligns with rate limit reset

#### SEC EDGAR Circuit Breaker
```python
sec_breaker = CircuitBreaker(
    fail_max=3,              # Open after 3 consecutive failures
    timeout_duration=120,    # Wait 120 seconds before retry
    name="sec_api"
)
```

**Rationale:**
- SEC has strict rate limits (10 requests/second)
- More conservative threshold (3 failures) for compliance
- Longer timeout (120s) respects SEC infrastructure
- Critical for regulatory compliance - be conservative

#### Yahoo Finance Circuit Breaker
```python
yahoo_finance_breaker = CircuitBreaker(
    fail_max=5,              # Open after 5 consecutive failures
    timeout_duration=60,     # Wait 60 seconds before retry
    name="yahoo_finance"
)
```

**Rationale:**
- Generally reliable but can have occasional outages
- Standard threshold of 5 failures
- 60-second timeout for quick recovery

### Integration Points

#### 1. Alpha Vantage Connector
**File:** `/home/user/corporate_intel/src/connectors/data_sources.py`

```python
async def get_company_overview(self, ticker: str) -> Dict[str, Any]:
    """Get company overview with fundamental data.

    Protected by circuit breaker to prevent cascading failures.
    """
    await self.rate_limiter.acquire()

    try:
        # Wrap API call with circuit breaker
        data, _ = alpha_vantage_breaker.call(self.fd.get_company_overview, ticker)
        # Process data...
    except Exception as e:
        logger.error(f"Error fetching Alpha Vantage data for {ticker}: {e}")
        return await alpha_vantage_fallback(ticker)
```

#### 2. SEC EDGAR API Client
**File:** `/home/user/corporate_intel/src/pipeline/sec_ingestion.py`

Protected methods:
- `get_ticker_to_cik_mapping()` - Ticker to CIK mapping
- `get_company_info()` - Company submission data
- `get_filings()` - Filing retrieval
- `download_filing_content()` - Filing content download

```python
async def get_company_info(self, ticker: str) -> Dict[str, Any]:
    """Fetch company information from SEC.

    Protected by circuit breaker to prevent cascading failures.
    """
    await self.rate_limiter.acquire()

    try:
        async with httpx.AsyncClient() as client:
            response = sec_breaker.call(client.get, submissions_url, headers=self.headers)
            if asyncio.iscoroutine(response):
                response = await response
            # Process response...
    except Exception as e:
        logger.error(f"Error fetching company info for {ticker}: {e}")
        return await sec_fallback(ticker)
```

#### 3. Yahoo Finance Ingestion
**File:** `/home/user/corporate_intel/src/pipeline/yahoo_finance_ingestion.py`

Protected methods:
- `_fetch_yahoo_finance_data()` - Fetch stock data
- `_ingest_quarterly_financials()` - Fetch quarterly financials

```python
async def _fetch_yahoo_finance_data(self, ticker: str, max_retries: int = 3):
    """Fetch data from Yahoo Finance with circuit breaker protection."""
    for attempt in range(max_retries):
        try:
            # Wrap API call with circuit breaker
            stock = yahoo_finance_breaker.call(yf.Ticker, ticker)
            stock_obj = await loop.run_in_executor(None, lambda: stock) if asyncio.iscoroutine(stock) else stock
            # Process data...
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return await yahoo_finance_fallback(ticker)
```

### Fallback Strategies

All fallback strategies return empty dictionaries with warning logs, allowing graceful degradation:

```python
async def alpha_vantage_fallback(*args, **kwargs) -> dict:
    """Fallback when Alpha Vantage API is unavailable."""
    logger.warning("Alpha Vantage API unavailable - returning empty data")
    return {}
```

**Design Rationale:**
- Caller code already handles empty responses gracefully
- Prevents exception propagation when circuit is open
- Maintains system stability during outages
- Logs warnings for monitoring and alerting

### Monitoring and Logging

#### State Change Events
```python
def log_circuit_state_change(breaker: CircuitBreaker, old_state: str, new_state: str):
    """Log circuit breaker state changes."""
    logger.warning(
        f"Circuit breaker '{breaker.name}' state changed: {old_state} -> {new_state} "
        f"(failures: {breaker.fail_counter}/{breaker.fail_max})"
    )
```

#### Failure Events
```python
def log_circuit_failure(breaker: CircuitBreaker, exception: Exception):
    """Log circuit breaker failure events."""
    logger.warning(
        f"Circuit breaker '{breaker.name}' recorded failure: {type(exception).__name__}: {exception} "
        f"(failures: {breaker.fail_counter}/{breaker.fail_max})"
    )
```

#### Success Events
```python
def log_circuit_success(breaker: CircuitBreaker):
    """Log circuit breaker success events (only when recovering)."""
    if breaker.fail_counter > 0:
        logger.info(
            f"Circuit breaker '{breaker.name}' recorded success "
            f"(failures reset from {breaker.fail_counter})"
        )
```

#### Status Monitoring
```python
def get_circuit_breaker_status() -> dict:
    """Get status of all circuit breakers for health checks."""
    return {
        "alpha_vantage": {
            "state": alpha_vantage_breaker.current_state,
            "failure_count": alpha_vantage_breaker.fail_counter,
            "failure_threshold": alpha_vantage_breaker.fail_max,
            "timeout_duration": alpha_vantage_breaker.timeout_duration,
        },
        # ... other breakers
    }
```

**Integration with Observability:**
- Logs can be exported to centralized logging (ELK, Splunk)
- Ready for Prometheus metrics integration
- State changes trigger alerts in monitoring systems
- Health check endpoints can expose circuit breaker status

## Testing

### Unit Tests
Location: `/home/user/corporate_intel/tests/unit/test_circuit_breaker.py`

Test coverage includes:
- Configuration validation
- State transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Failure counting and reset
- Fallback strategy invocation
- Status monitoring functions
- Integration with API connectors

### Running Tests
```bash
# Install dependencies
pip install -r requirements.txt

# Run circuit breaker tests
pytest tests/unit/test_circuit_breaker.py -v

# Run all tests
pytest tests/ -v
```

## Deployment Checklist

- [x] Add pybreaker dependency to requirements.txt
- [x] Create circuit breaker configuration module
- [x] Wrap Alpha Vantage API calls
- [x] Wrap SEC API calls
- [x] Wrap Yahoo Finance API calls
- [x] Implement fallback strategies
- [x] Add monitoring and logging
- [x] Create unit tests
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run tests to verify implementation
- [ ] Monitor circuit breaker state changes in production
- [ ] Set up alerts for circuit open events

## Usage Examples

### Checking Circuit Breaker Status
```python
from src.core.circuit_breaker import get_circuit_breaker_status

status = get_circuit_breaker_status()
print(f"Alpha Vantage: {status['alpha_vantage']['state']}")
print(f"SEC API: {status['sec_api']['state']}")
print(f"Yahoo Finance: {status['yahoo_finance']['state']}")
```

### Manual Circuit Reset
```python
from src.core.circuit_breaker import reset_all_circuit_breakers

# Reset all circuit breakers (e.g., after maintenance)
reset_all_circuit_breakers()
```

### Handling Circuit Open State
```python
from pybreaker import CircuitBreakerError

try:
    data = await connector.get_company_overview("AAPL")
except CircuitBreakerError:
    logger.error("Circuit breaker is OPEN - Alpha Vantage unavailable")
    # Use cached data or skip this operation
```

## Benefits

1. **Prevents Cascading Failures**
   - Failed API calls don't consume resources indefinitely
   - System remains responsive even when external APIs are down

2. **Faster Failure Detection**
   - Immediate failure when circuit is open (no waiting for timeouts)
   - Reduces latency during outages

3. **Automatic Recovery**
   - Circuits automatically attempt recovery after timeout
   - No manual intervention required for transient failures

4. **Resource Protection**
   - Thread/connection pools aren't exhausted by failed requests
   - Database connections remain available for other operations

5. **Observable System Behavior**
   - State changes logged for monitoring
   - Clear visibility into external API health
   - Easier troubleshooting and debugging

## Future Enhancements

1. **Prometheus Metrics**
   - Export circuit breaker state as metrics
   - Track failure rates, open duration, recovery time

2. **Dynamic Configuration**
   - Adjust thresholds based on observed behavior
   - Environment-specific settings (dev, staging, prod)

3. **Advanced Fallback Strategies**
   - Return cached data when circuit is open
   - Implement data staleness tracking
   - Progressive degradation based on data age

4. **Dashboard Integration**
   - Real-time circuit breaker status visualization
   - Historical trends and pattern analysis
   - Alert configuration and management

## References

- [Circuit Breaker Pattern - Martin Fowler](https://martinfowler.com/bliki/CircuitBreaker.html)
- [pybreaker Documentation](https://github.com/danielfm/pybreaker)
- [Release It! - Michael Nygard](https://pragprog.com/titles/mnee2/release-it-second-edition/)
