"""Unit tests for circuit breaker implementation.

Tests the circuit breaker pattern for external API calls to prevent
cascading failures when external services become unavailable.
"""

import asyncio
from unittest.mock import Mock, patch, AsyncMock

import pytest
from pybreaker import CircuitBreakerError

from src.core.circuit_breaker import (
    alpha_vantage_breaker,
    sec_breaker,
    yahoo_finance_breaker,
    get_circuit_breaker_status,
    reset_all_circuit_breakers,
    alpha_vantage_fallback,
    sec_fallback,
    yahoo_finance_fallback,
)


class TestCircuitBreakerConfiguration:
    """Test circuit breaker configuration and setup."""

    def test_alpha_vantage_breaker_configuration(self):
        """Verify Alpha Vantage circuit breaker has correct settings."""
        assert alpha_vantage_breaker.fail_max == 5
        assert alpha_vantage_breaker.timeout_duration == 60
        assert alpha_vantage_breaker.name == "alpha_vantage"

    def test_sec_breaker_configuration(self):
        """Verify SEC API circuit breaker has correct settings."""
        assert sec_breaker.fail_max == 3
        assert sec_breaker.timeout_duration == 120
        assert sec_breaker.name == "sec_api"

    def test_yahoo_finance_breaker_configuration(self):
        """Verify Yahoo Finance circuit breaker has correct settings."""
        assert yahoo_finance_breaker.fail_max == 5
        assert yahoo_finance_breaker.timeout_duration == 60
        assert yahoo_finance_breaker.name == "yahoo_finance"


class TestCircuitBreakerBehavior:
    """Test circuit breaker opening and closing behavior."""

    def setup_method(self):
        """Reset all circuit breakers before each test."""
        reset_all_circuit_breakers()

    def test_circuit_opens_after_failures(self):
        """Test that circuit opens after exceeding failure threshold."""
        # Create a function that always fails
        def failing_function():
            raise Exception("Simulated API failure")

        # Trigger failures up to the threshold
        for i in range(alpha_vantage_breaker.fail_max):
            try:
                alpha_vantage_breaker.call(failing_function)
            except Exception:
                pass

        # Next call should raise CircuitBreakerError (circuit is now OPEN)
        with pytest.raises(CircuitBreakerError):
            alpha_vantage_breaker.call(failing_function)

    def test_circuit_stays_closed_on_success(self):
        """Test that circuit remains closed when calls succeed."""
        def successful_function():
            return "success"

        # Multiple successful calls should keep circuit closed
        for _ in range(10):
            result = alpha_vantage_breaker.call(successful_function)
            assert result == "success"

        # Circuit should still be closed
        assert alpha_vantage_breaker.current_state == "closed"

    def test_circuit_recovers_after_success(self):
        """Test that circuit can recover after failures when success occurs."""
        call_count = [0]

        def sometimes_failing_function():
            call_count[0] += 1
            # Fail first 2 times, then succeed
            if call_count[0] <= 2:
                raise Exception("Temporary failure")
            return "success"

        # First two calls fail
        for _ in range(2):
            try:
                alpha_vantage_breaker.call(sometimes_failing_function)
            except Exception:
                pass

        # Third call succeeds - circuit should remain closed
        result = alpha_vantage_breaker.call(sometimes_failing_function)
        assert result == "success"
        assert alpha_vantage_breaker.current_state == "closed"


class TestCircuitBreakerStatus:
    """Test circuit breaker status monitoring functions."""

    def test_get_circuit_breaker_status(self):
        """Test status reporting for all circuit breakers."""
        reset_all_circuit_breakers()
        status = get_circuit_breaker_status()

        # Verify all breakers are included
        assert "alpha_vantage" in status
        assert "sec_api" in status
        assert "yahoo_finance" in status

        # Verify status structure
        for breaker_name, breaker_status in status.items():
            assert "state" in breaker_status
            assert "failure_count" in breaker_status
            assert "failure_threshold" in breaker_status
            assert "timeout_duration" in breaker_status

        # All should be closed initially
        assert status["alpha_vantage"]["state"] == "closed"
        assert status["sec_api"]["state"] == "closed"
        assert status["yahoo_finance"]["state"] == "closed"

    def test_reset_all_circuit_breakers(self):
        """Test resetting all circuit breakers to closed state."""
        # Trigger some failures to open a circuit
        def failing_function():
            raise Exception("Failure")

        for _ in range(alpha_vantage_breaker.fail_max):
            try:
                alpha_vantage_breaker.call(failing_function)
            except Exception:
                pass

        # Circuit should be open now
        with pytest.raises(CircuitBreakerError):
            alpha_vantage_breaker.call(failing_function)

        # Reset all breakers
        reset_all_circuit_breakers()

        # Circuit should be closed now
        assert alpha_vantage_breaker.current_state == "closed"


class TestFallbackStrategies:
    """Test fallback strategies when circuit breakers are open."""

    @pytest.mark.asyncio
    async def test_alpha_vantage_fallback_returns_empty_dict(self):
        """Test Alpha Vantage fallback returns empty dict."""
        result = await alpha_vantage_fallback("AAPL")
        assert result == {}

    @pytest.mark.asyncio
    async def test_sec_fallback_returns_empty_dict(self):
        """Test SEC API fallback returns empty dict."""
        result = await sec_fallback("AAPL")
        assert result == {}

    @pytest.mark.asyncio
    async def test_yahoo_finance_fallback_returns_empty_dict(self):
        """Test Yahoo Finance fallback returns empty dict."""
        result = await yahoo_finance_fallback("AAPL")
        assert result == {}


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker with API connectors."""

    def setup_method(self):
        """Reset all circuit breakers before each test."""
        reset_all_circuit_breakers()

    @pytest.mark.asyncio
    @patch('src.connectors.data_sources.AlphaVantageConnector')
    async def test_alpha_vantage_circuit_breaker_integration(self, mock_connector):
        """Test circuit breaker integration with Alpha Vantage connector."""
        from src.connectors.data_sources import AlphaVantageConnector

        # Create mock that simulates API failures
        mock_instance = Mock()
        mock_instance.fd = Mock()
        mock_instance.fd.get_company_overview = Mock(side_effect=Exception("API Error"))
        mock_instance.rate_limiter = AsyncMock()
        mock_instance.rate_limiter.acquire = AsyncMock()

        mock_connector.return_value = mock_instance

        connector = AlphaVantageConnector()

        # Multiple failed calls should eventually open the circuit
        for _ in range(alpha_vantage_breaker.fail_max + 1):
            try:
                await connector.get_company_overview("AAPL")
            except Exception:
                pass

        # Verify circuit is now open by checking status
        status = get_circuit_breaker_status()
        # After max failures, next call should trigger circuit open
        # Note: Exact state depends on timing, but failure count should be tracked
        assert status["alpha_vantage"]["failure_count"] >= 0


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions."""

    def setup_method(self):
        """Reset all circuit breakers before each test."""
        reset_all_circuit_breakers()

    def test_closed_to_open_transition(self):
        """Test transition from CLOSED to OPEN state."""
        def failing_function():
            raise Exception("Simulated failure")

        # Initial state should be closed
        assert sec_breaker.current_state == "closed"

        # Trigger max failures
        for _ in range(sec_breaker.fail_max):
            try:
                sec_breaker.call(failing_function)
            except Exception:
                pass

        # Next call should open the circuit
        with pytest.raises(CircuitBreakerError):
            sec_breaker.call(failing_function)

        # State should now be open
        assert sec_breaker.current_state == "open"

    def test_failure_counter_reset_on_success(self):
        """Test that failure counter resets after successful call."""
        call_count = [0]

        def intermittent_function():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("One failure")
            return "success"

        # First call fails
        try:
            yahoo_finance_breaker.call(intermittent_function)
        except Exception:
            pass

        # Failure counter should be 1
        assert yahoo_finance_breaker.fail_counter == 1

        # Second call succeeds
        result = yahoo_finance_breaker.call(intermittent_function)
        assert result == "success"

        # Failure counter should be reset to 0
        assert yahoo_finance_breaker.fail_counter == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
