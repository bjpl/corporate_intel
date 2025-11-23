"""Comprehensive tests for AnalysisEngine - strategies, multi-strategy analysis."""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.analysis.engine import (
    AnalysisEngine,
    AnalysisResult,
    AnalysisStrategy,
    CompetitorAnalysisStrategy,
    SegmentOpportunityStrategy,
    CohortAnalysisStrategy
)


@pytest.fixture
def analysis_engine():
    """Create AnalysisEngine instance."""
    return AnalysisEngine()


@pytest.fixture
def sample_companies():
    """Create sample companies data."""
    return [
        {'ticker': 'DUOL', 'name': 'Duolingo', 'category': 'direct_to_consumer'},
        {'ticker': 'CHGG', 'name': 'Chegg', 'category': 'higher_education'},
        {'ticker': 'COUR', 'name': 'Coursera', 'category': 'higher_education'}
    ]


@pytest.fixture
def sample_metrics():
    """Create sample metrics data."""
    return {
        'DUOL': {
            'revenue': 484.2e6,
            'revenue_growth_yoy': 42.9,
            'cac': 15.0,
            'ltv': 85.0,
            'arpu': 4.9,
            'gross_margin': 0.75
        },
        'CHGG': {
            'revenue': 398.5e6,
            'revenue_growth_yoy': -5.2,
            'cac': 45.0,
            'ltv': 120.0,
            'arpu': 8.5,
            'gross_margin': 0.68
        },
        'COUR': {
            'revenue': 523.8e6,
            'revenue_growth_yoy': 15.8,
            'cac': 35.0,
            'ltv': 95.0,
            'arpu': 6.2,
            'gross_margin': 0.71
        }
    }


class TestAnalysisEngine:
    """Tests for main AnalysisEngine orchestration."""

    def test_engine_initialization(self, analysis_engine):
        """Test engine initializes with default strategies."""
        assert len(analysis_engine.strategies) == 3
        assert 'competitor_analysis' in analysis_engine.strategies
        assert 'segment_opportunity' in analysis_engine.strategies
        assert 'cohort_analysis' in analysis_engine.strategies

    def test_register_strategy(self, analysis_engine):
        """Test registering new strategy."""
        # Create mock strategy
        mock_strategy = MagicMock(spec=AnalysisStrategy)
        mock_strategy.name = 'custom_strategy'
        mock_strategy.description = 'Custom test strategy'

        analysis_engine.register_strategy(mock_strategy)

        assert 'custom_strategy' in analysis_engine.strategies
        assert len(analysis_engine.strategies) == 4

    def test_list_strategies(self, analysis_engine):
        """Test listing available strategies."""
        strategies = analysis_engine.list_strategies()

        assert len(strategies) == 3
        assert all('name' in s and 'description' in s for s in strategies)
        assert any(s['name'] == 'competitor_analysis' for s in strategies)

    def test_analyze_unknown_strategy(self, analysis_engine):
        """Test error when analyzing with unknown strategy."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            analysis_engine.analyze('nonexistent_strategy', {})

    def test_analyze_invalid_input(self, analysis_engine):
        """Test error when input data is invalid for strategy."""
        invalid_data = {'missing': 'required_fields'}

        with pytest.raises(ValueError, match="Invalid input data"):
            analysis_engine.analyze('competitor_analysis', invalid_data)

    def test_multi_strategy_analysis_all(self, analysis_engine, sample_companies, sample_metrics):
        """Test running multiple strategies in parallel."""
        # Create valid data for all strategies
        cohort_data = {
            '2024-Q1': {
                'users_by_month': [1000, 800, 650, 550],
                'revenue_by_month': [10000, 8500, 7000, 6000],
                'initial_users': 1000
            }
        }

        data = {
            'companies': sample_companies,
            'metrics': sample_metrics,
            'time_period': '2024',
            'segment': 'higher_education',
            'market_data': {'tam_historical': [1e9, 1.2e9, 1.5e9]},
            'trends': {'ai_personalization': {'adoption_rate': 25}},
            'cohort_data': cohort_data,
            'time_periods': ['2024-Q1', '2024-Q2'],
            'company_id': 'uuid-1',
            'ticker': 'DUOL'
        }

        results = analysis_engine.multi_strategy_analysis(data)

        assert len(results) == 3
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_multi_strategy_analysis_specific(self, analysis_engine, sample_companies, sample_metrics):
        """Test running specific strategies."""
        data = {
            'companies': sample_companies,
            'metrics': sample_metrics,
            'time_period': '2024'
        }

        results = analysis_engine.multi_strategy_analysis(
            data,
            strategies=['competitor_analysis']
        )

        assert len(results) == 1
        assert results[0].analysis_type == 'competitor_analysis'

    def test_multi_strategy_analysis_handles_failures(self, analysis_engine):
        """Test multi-strategy analysis handles individual strategy failures gracefully."""
        data = {
            'companies': [],
            'metrics': {},
            'time_period': '2024'
        }

        # This should not raise, but return empty or partial results
        results = analysis_engine.multi_strategy_analysis(data)

        # Some strategies may fail validation, so results could be empty
        assert isinstance(results, list)


class TestCompetitorAnalysisStrategy:
    """Tests for CompetitorAnalysisStrategy."""

    def test_strategy_properties(self):
        """Test strategy name and description."""
        strategy = CompetitorAnalysisStrategy()

        assert strategy.name == 'competitor_analysis'
        assert 'competitive positioning' in strategy.description.lower()

    def test_validate_input_valid(self):
        """Test input validation with valid data."""
        strategy = CompetitorAnalysisStrategy()
        data = {
            'companies': [{'ticker': 'DUOL'}],
            'metrics': {'DUOL': {'revenue': 100e6}},
            'time_period': '2024'
        }

        assert strategy.validate_input(data) is True

    def test_validate_input_missing_fields(self):
        """Test input validation fails with missing required fields."""
        strategy = CompetitorAnalysisStrategy()
        data = {'companies': []}

        assert strategy.validate_input(data) is False

    def test_analyze_market_shares(self, sample_companies, sample_metrics):
        """Test market share calculation."""
        strategy = CompetitorAnalysisStrategy()
        data = {
            'companies': sample_companies,
            'metrics': sample_metrics,
            'time_period': '2024'
        }

        result = strategy.analyze(data)

        assert 'market_shares' in result.results
        assert 'DUOL' in result.results['market_shares']
        assert 'CHGG' in result.results['market_shares']

        # Market shares should sum to ~100%
        total_share = sum(result.results['market_shares'].values())
        assert 99 < total_share < 101

    def test_analyze_growth_rates(self, sample_companies, sample_metrics):
        """Test growth rate comparison."""
        strategy = CompetitorAnalysisStrategy()
        data = {
            'companies': sample_companies,
            'metrics': sample_metrics,
            'time_period': '2024'
        }

        result = strategy.analyze(data)

        assert 'growth_rates' in result.results
        assert result.results['growth_rates']['DUOL'] == 42.9
        assert result.results['growth_rates']['CHGG'] == -5.2

    def test_analyze_efficiency_metrics(self, sample_companies, sample_metrics):
        """Test efficiency metrics analysis."""
        strategy = CompetitorAnalysisStrategy()
        data = {
            'companies': sample_companies,
            'metrics': sample_metrics,
            'time_period': '2024'
        }

        result = strategy.analyze(data)

        assert 'efficiency_metrics' in result.results
        assert 'DUOL' in result.results['efficiency_metrics']
        assert 'cac_to_ltv_ratio' in result.results['efficiency_metrics']['DUOL']
        assert 'arpu' in result.results['efficiency_metrics']['DUOL']

    def test_analyze_generates_insights(self, sample_companies, sample_metrics):
        """Test that analysis generates insights."""
        strategy = CompetitorAnalysisStrategy()
        data = {
            'companies': sample_companies,
            'metrics': sample_metrics,
            'time_period': '2024'
        }

        result = strategy.analyze(data)

        assert len(result.insights) > 0
        assert any('market share' in insight.lower() for insight in result.insights)

    def test_analyze_generates_recommendations(self, sample_companies, sample_metrics):
        """Test that analysis generates recommendations."""
        strategy = CompetitorAnalysisStrategy()
        data = {
            'companies': sample_companies,
            'metrics': sample_metrics,
            'time_period': '2024'
        }

        result = strategy.analyze(data)

        assert len(result.recommendations) > 0
        assert len(result.recommendations) == len(sample_companies)

    def test_analyze_confidence_score(self, sample_companies, sample_metrics):
        """Test confidence score is reasonable."""
        strategy = CompetitorAnalysisStrategy()
        data = {
            'companies': sample_companies,
            'metrics': sample_metrics,
            'time_period': '2024'
        }

        result = strategy.analyze(data)

        assert 0 <= result.confidence_score <= 1
        assert result.confidence_score == 0.85


class TestSegmentOpportunityStrategy:
    """Tests for SegmentOpportunityStrategy."""

    def test_strategy_properties(self):
        """Test strategy name and description."""
        strategy = SegmentOpportunityStrategy()

        assert strategy.name == 'segment_opportunity'
        assert 'opportunities' in strategy.description.lower()

    def test_validate_input_valid(self):
        """Test input validation with valid data."""
        strategy = SegmentOpportunityStrategy()
        data = {
            'segment': 'k12',
            'market_data': {'tam_historical': [1e9, 1.2e9]},
            'trends': {}
        }

        assert strategy.validate_input(data) is True

    def test_analyze_tam_expansion_high_growth(self):
        """Test TAM expansion analysis with high growth."""
        strategy = SegmentOpportunityStrategy()
        data = {
            'segment': 'k12',
            'market_data': {'tam_historical': [1e9, 1.5e9, 2.3e9]},  # High CAGR
            'trends': {}
        }

        result = strategy.analyze(data)

        assert 'tam_growth' in result.results
        assert result.results['tam_growth'] > 15
        assert any(opp['type'] == 'market_expansion' for opp in result.results['opportunities'])

    def test_analyze_identify_underserved_niches(self):
        """Test identification of underserved market areas."""
        strategy = SegmentOpportunityStrategy()
        data = {
            'segment': 'k12',
            'market_data': {},
            'trends': {}
        }

        result = strategy.analyze(data)

        assert 'opportunities' in result.results
        underserved_opps = [
            opp for opp in result.results['opportunities']
            if opp['type'] == 'underserved_niche'
        ]
        assert len(underserved_opps) > 0

    def test_analyze_tech_adoption_opportunities(self):
        """Test technology adoption opportunity analysis."""
        strategy = SegmentOpportunityStrategy()
        data = {
            'segment': 'higher_education',
            'market_data': {'tam_historical': [1e9, 1.1e9]},
            'trends': {
                'ai_personalization': {'adoption_rate': 20},  # Low adoption
                'vr_ar_learning': {'adoption_rate': 10}
            }
        }

        result = strategy.analyze(data)

        tech_opps = [
            opp for opp in result.results['opportunities']
            if opp['type'] == 'technology_adoption'
        ]
        assert len(tech_opps) >= 2

    def test_analyze_generates_prioritized_recommendations(self):
        """Test that recommendations are prioritized."""
        strategy = SegmentOpportunityStrategy()
        data = {
            'segment': 'corporate_learning',
            'market_data': {'tam_historical': [5e9, 7e9, 10e9]},  # High growth
            'trends': {}
        }

        result = strategy.analyze(data)

        assert len(result.recommendations) > 0
        assert any('Priority' in rec for rec in result.recommendations)


class TestCohortAnalysisStrategy:
    """Tests for CohortAnalysisStrategy."""

    def test_strategy_properties(self):
        """Test strategy name and description."""
        strategy = CohortAnalysisStrategy()

        assert strategy.name == 'cohort_analysis'
        assert 'cohort' in strategy.description.lower()
        assert 'retention' in strategy.description.lower()

    def test_validate_input_valid(self):
        """Test input validation with valid data."""
        strategy = CohortAnalysisStrategy()
        data = {
            'cohort_data': {'2024-Q1': {'users_by_month': [1000, 800]}},
            'time_periods': ['2024-Q1']
        }

        assert strategy.validate_input(data) is True

    def test_calculate_retention_rates(self):
        """Test retention rate calculation."""
        strategy = CohortAnalysisStrategy()
        cohort_data = {
            '2024-Q1': {'users_by_month': [1000, 800, 650, 550]},
            '2024-Q2': {'users_by_month': [1200, 900, 750]}
        }

        retention = strategy._calculate_retention(cohort_data)

        assert '2024-Q1' in retention
        assert retention['2024-Q1'][0] == 100.0  # Month 0 is 100%
        assert retention['2024-Q1'][1] == 80.0   # Month 1 is 80%
        assert retention['2024-Q1'][2] == 65.0   # Month 2 is 65%

    def test_calculate_ltv_by_cohort(self):
        """Test LTV calculation by cohort."""
        strategy = CohortAnalysisStrategy()
        cohort_data = {
            '2024-Q1': {
                'revenue_by_month': [10000, 8000, 6000],
                'initial_users': 1000
            }
        }

        ltv = strategy._calculate_ltv(cohort_data)

        assert '2024-Q1' in ltv
        assert ltv['2024-Q1'] == 24.0  # (10000 + 8000 + 6000) / 1000

    def test_analyze_retention_improving_trend(self):
        """Test detection of improving retention trend."""
        strategy = CohortAnalysisStrategy()
        cohort_data = {
            '2024-Q1': {'users_by_month': [1000, 600, 450]},
            '2024-Q2': {'users_by_month': [1000, 620, 470]},
            '2024-Q3': {'users_by_month': [1000, 650, 500]},
            '2024-Q4': {'users_by_month': [1000, 680, 530]},
            '2025-Q1': {'users_by_month': [1000, 700, 550]},
            '2025-Q2': {'users_by_month': [1000, 720, 570]}
        }

        data = {
            'cohort_data': cohort_data,
            'time_periods': list(cohort_data.keys())
        }

        result = strategy.analyze(data)

        assert result.results['trends']['retention_improving'] is True

    def test_analyze_ltv_trend_increasing(self):
        """Test detection of increasing LTV trend."""
        strategy = CohortAnalysisStrategy()
        cohort_data = {
            '2024-Q1': {'revenue_by_month': [5000, 4000], 'initial_users': 1000},
            '2024-Q2': {'revenue_by_month': [6000, 5000], 'initial_users': 1000},
            '2024-Q3': {'revenue_by_month': [7000, 6000], 'initial_users': 1000},
            '2024-Q4': {'revenue_by_month': [8000, 7000], 'initial_users': 1000}
        }

        data = {
            'cohort_data': cohort_data,
            'time_periods': list(cohort_data.keys()),
            'company_id': 'uuid-1',
            'ticker': 'DUOL'
        }

        result = strategy.analyze(data)

        assert result.results['trends']['ltv_trend'] == 'increasing'

    def test_analyze_low_retention_warning(self):
        """Test warning for low Month 1 retention."""
        strategy = CohortAnalysisStrategy()
        cohort_data = {
            '2024-Q1': {'users_by_month': [1000, 300, 200]},  # 30% M1 retention
            '2024-Q2': {'users_by_month': [1000, 350, 250]}
        }

        data = {
            'cohort_data': cohort_data,
            'time_periods': list(cohort_data.keys()),
            'company_id': 'uuid-1',
            'ticker': 'DUOL'
        }

        result = strategy.analyze(data)

        assert any('onboarding' in rec.lower() for rec in result.recommendations)


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""

    def test_result_creation(self):
        """Test creating AnalysisResult."""
        result = AnalysisResult(
            analysis_type='test_analysis',
            company_id='uuid-1',
            ticker='DUOL',
            results={'metric': 100},
            insights=['Insight 1'],
            recommendations=['Recommendation 1'],
            confidence_score=0.85,
            metadata={'test': True}
        )

        assert result.analysis_type == 'test_analysis'
        assert result.company_id == 'uuid-1'
        assert result.ticker == 'DUOL'
        assert result.confidence_score == 0.85

    def test_result_auto_timestamp(self):
        """Test automatic timestamp generation."""
        result = AnalysisResult(
            analysis_type='test',
            company_id=None,
            ticker=None,
            results={},
            insights=[],
            recommendations=[],
            confidence_score=0.8,
            metadata={}
        )

        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)

    def test_result_custom_timestamp(self):
        """Test custom timestamp."""
        custom_time = datetime(2025, 1, 1, 12, 0, 0)
        result = AnalysisResult(
            analysis_type='test',
            company_id=None,
            ticker=None,
            results={},
            insights=[],
            recommendations=[],
            confidence_score=0.8,
            metadata={},
            timestamp=custom_time
        )

        assert result.timestamp == custom_time
