"""
Unit Tests for Analysis Service

Tests competitor analysis calculations, HHI computation,
BCG matrix positioning, and cohort analysis logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np

from app.services.analysis_service import (
    AnalysisService,
    CompetitorAnalyzer,
    MarketConcentrationCalculator,
    BCGMatrixAnalyzer,
    CohortAnalyzer
)
from app.core.exceptions import (
    AnalysisError,
    ValidationError,
    InsufficientDataError
)


class TestCompetitorAnalyzer:
    """Test suite for competitor analysis calculations"""

    @pytest.fixture
    def analyzer(self):
        """Create competitor analyzer instance"""
        return CompetitorAnalyzer()

    def test_calculate_market_share(self, analyzer):
        """Test market share calculation"""
        # Arrange
        company_revenue = Decimal('1000000')
        total_market_revenue = Decimal('5000000')

        # Act
        market_share = analyzer.calculate_market_share(
            company_revenue,
            total_market_revenue
        )

        # Assert
        assert market_share == Decimal('20.0')  # 20%

    def test_calculate_market_share_zero_market(self, analyzer):
        """Test market share calculation with zero market size"""
        # Arrange
        company_revenue = Decimal('1000000')
        total_market_revenue = Decimal('0')

        # Act & Assert
        with pytest.raises(ValidationError, match="Total market revenue must be positive"):
            analyzer.calculate_market_share(company_revenue, total_market_revenue)

    def test_analyze_competitive_position(self, analyzer):
        """Test competitive position analysis"""
        # Arrange
        company_data = {
            'revenue': Decimal('1000000'),
            'growth_rate': Decimal('15.5'),
            'market_share': Decimal('20.0'),
            'profit_margin': Decimal('12.5')
        }

        competitors_data = [
            {
                'revenue': Decimal('1500000'),
                'growth_rate': Decimal('10.0'),
                'market_share': Decimal('30.0'),
                'profit_margin': Decimal('10.0')
            },
            {
                'revenue': Decimal('800000'),
                'growth_rate': Decimal('8.0'),
                'market_share': Decimal('16.0'),
                'profit_margin': Decimal('9.0')
            }
        ]

        # Act
        position = analyzer.analyze_competitive_position(
            company_data,
            competitors_data
        )

        # Assert
        assert position['rank_by_revenue'] == 2  # Second largest
        assert position['rank_by_growth'] == 1  # Fastest growing
        assert position['rank_by_margin'] == 1  # Most profitable
        assert position['competitive_strength'] == 'strong'

    def test_calculate_growth_rate(self, analyzer):
        """Test growth rate calculation"""
        # Arrange
        current_revenue = Decimal('1200000')
        previous_revenue = Decimal('1000000')

        # Act
        growth_rate = analyzer.calculate_growth_rate(
            current_revenue,
            previous_revenue
        )

        # Assert
        assert growth_rate == Decimal('20.0')  # 20% growth

    def test_calculate_negative_growth_rate(self, analyzer):
        """Test negative growth rate calculation"""
        # Arrange
        current_revenue = Decimal('800000')
        previous_revenue = Decimal('1000000')

        # Act
        growth_rate = analyzer.calculate_growth_rate(
            current_revenue,
            previous_revenue
        )

        # Assert
        assert growth_rate == Decimal('-20.0')  # -20% decline

    def test_identify_competitive_advantages(self, analyzer):
        """Test identification of competitive advantages"""
        # Arrange
        company_metrics = {
            'profit_margin': Decimal('25.0'),
            'growth_rate': Decimal('30.0'),
            'customer_retention': Decimal('95.0'),
            'innovation_index': Decimal('8.5')
        }

        industry_averages = {
            'profit_margin': Decimal('15.0'),
            'growth_rate': Decimal('10.0'),
            'customer_retention': Decimal('80.0'),
            'innovation_index': Decimal('6.0')
        }

        # Act
        advantages = analyzer.identify_competitive_advantages(
            company_metrics,
            industry_averages
        )

        # Assert
        assert len(advantages) == 4
        assert 'profit_margin' in advantages
        assert advantages['profit_margin']['advantage_percentage'] > 0

    def test_calculate_competitive_intensity(self, analyzer):
        """Test competitive intensity calculation"""
        # Arrange
        market_data = {
            'number_of_competitors': 15,
            'market_concentration': Decimal('0.35'),
            'entry_barriers': 'medium',
            'product_differentiation': 'low'
        }

        # Act
        intensity = analyzer.calculate_competitive_intensity(market_data)

        # Assert
        assert intensity in ['low', 'medium', 'high', 'very_high']
        assert isinstance(intensity, str)


class TestMarketConcentrationCalculator:
    """Test suite for HHI and market concentration calculations"""

    @pytest.fixture
    def calculator(self):
        """Create market concentration calculator instance"""
        return MarketConcentrationCalculator()

    def test_calculate_hhi_basic(self, calculator):
        """Test basic HHI calculation"""
        # Arrange
        market_shares = [
            Decimal('30.0'),
            Decimal('25.0'),
            Decimal('20.0'),
            Decimal('15.0'),
            Decimal('10.0')
        ]

        # Act
        hhi = calculator.calculate_hhi(market_shares)

        # Assert
        # HHI = 30^2 + 25^2 + 20^2 + 15^2 + 10^2 = 2350
        assert hhi == Decimal('2350')

    def test_calculate_hhi_monopoly(self, calculator):
        """Test HHI calculation for monopoly market"""
        # Arrange
        market_shares = [Decimal('100.0')]

        # Act
        hhi = calculator.calculate_hhi(market_shares)

        # Assert
        assert hhi == Decimal('10000')  # Maximum HHI

    def test_calculate_hhi_perfect_competition(self, calculator):
        """Test HHI calculation for highly competitive market"""
        # Arrange
        market_shares = [Decimal('1.0')] * 100

        # Act
        hhi = calculator.calculate_hhi(market_shares)

        # Assert
        assert hhi == Decimal('100')  # Very low HHI

    def test_classify_market_concentration(self, calculator):
        """Test market concentration classification"""
        # Arrange & Act
        unconcentrated = calculator.classify_concentration(Decimal('1200'))
        moderate = calculator.classify_concentration(Decimal('2000'))
        concentrated = calculator.classify_concentration(Decimal('2800'))

        # Assert
        assert unconcentrated == 'unconcentrated'
        assert moderate == 'moderately_concentrated'
        assert concentrated == 'highly_concentrated'

    def test_calculate_concentration_ratio_cr4(self, calculator):
        """Test CR4 (4-firm concentration ratio) calculation"""
        # Arrange
        market_shares = [
            Decimal('25.0'),
            Decimal('20.0'),
            Decimal('15.0'),
            Decimal('12.0'),
            Decimal('10.0'),
            Decimal('8.0'),
            Decimal('5.0'),
            Decimal('5.0')
        ]

        # Act
        cr4 = calculator.calculate_concentration_ratio(market_shares, n=4)

        # Assert
        assert cr4 == Decimal('72.0')  # Sum of top 4

    def test_analyze_market_power(self, calculator):
        """Test market power analysis"""
        # Arrange
        company_market_share = Decimal('35.0')
        hhi = Decimal('2500')

        # Act
        power_analysis = calculator.analyze_market_power(
            company_market_share,
            hhi
        )

        # Assert
        assert 'market_power_level' in power_analysis
        assert 'antitrust_concern' in power_analysis
        assert power_analysis['antitrust_concern'] == True  # HHI > 2500


class TestBCGMatrixAnalyzer:
    """Test suite for BCG matrix positioning"""

    @pytest.fixture
    def analyzer(self):
        """Create BCG matrix analyzer instance"""
        return BCGMatrixAnalyzer()

    def test_position_star_quadrant(self, analyzer):
        """Test positioning product in Star quadrant"""
        # Arrange
        product_data = {
            'market_share': Decimal('30.0'),
            'market_growth_rate': Decimal('25.0')
        }

        industry_data = {
            'average_market_share': Decimal('10.0'),
            'growth_threshold': Decimal('10.0')
        }

        # Act
        position = analyzer.calculate_position(product_data, industry_data)

        # Assert
        assert position['quadrant'] == 'star'
        assert position['relative_market_share'] > 1.0
        assert position['market_growth_rate'] > Decimal('10.0')

    def test_position_cash_cow_quadrant(self, analyzer):
        """Test positioning product in Cash Cow quadrant"""
        # Arrange
        product_data = {
            'market_share': Decimal('35.0'),
            'market_growth_rate': Decimal('3.0')
        }

        industry_data = {
            'average_market_share': Decimal('10.0'),
            'growth_threshold': Decimal('10.0')
        }

        # Act
        position = analyzer.calculate_position(product_data, industry_data)

        # Assert
        assert position['quadrant'] == 'cash_cow'
        assert position['relative_market_share'] > 1.0
        assert position['market_growth_rate'] < Decimal('10.0')

    def test_position_question_mark_quadrant(self, analyzer):
        """Test positioning product in Question Mark quadrant"""
        # Arrange
        product_data = {
            'market_share': Decimal('5.0'),
            'market_growth_rate': Decimal('20.0')
        }

        industry_data = {
            'average_market_share': Decimal('10.0'),
            'growth_threshold': Decimal('10.0')
        }

        # Act
        position = analyzer.calculate_position(product_data, industry_data)

        # Assert
        assert position['quadrant'] == 'question_mark'
        assert position['relative_market_share'] < 1.0
        assert position['market_growth_rate'] > Decimal('10.0')

    def test_position_dog_quadrant(self, analyzer):
        """Test positioning product in Dog quadrant"""
        # Arrange
        product_data = {
            'market_share': Decimal('3.0'),
            'market_growth_rate': Decimal('2.0')
        }

        industry_data = {
            'average_market_share': Decimal('10.0'),
            'growth_threshold': Decimal('10.0')
        }

        # Act
        position = analyzer.calculate_position(product_data, industry_data)

        # Assert
        assert position['quadrant'] == 'dog'
        assert position['relative_market_share'] < 1.0
        assert position['market_growth_rate'] < Decimal('10.0')

    def test_generate_strategic_recommendations(self, analyzer):
        """Test strategic recommendations based on BCG position"""
        # Arrange
        star_position = {'quadrant': 'star'}
        cow_position = {'quadrant': 'cash_cow'}
        qm_position = {'quadrant': 'question_mark'}
        dog_position = {'quadrant': 'dog'}

        # Act
        star_rec = analyzer.get_recommendations(star_position)
        cow_rec = analyzer.get_recommendations(cow_position)
        qm_rec = analyzer.get_recommendations(qm_position)
        dog_rec = analyzer.get_recommendations(dog_position)

        # Assert
        assert 'invest' in star_rec['strategy'].lower()
        assert 'harvest' in cow_rec['strategy'].lower()
        assert 'evaluate' in qm_rec['strategy'].lower()
        assert 'divest' in dog_rec['strategy'].lower()


class TestCohortAnalyzer:
    """Test suite for cohort analysis logic"""

    @pytest.fixture
    def analyzer(self):
        """Create cohort analyzer instance"""
        return CohortAnalyzer()

    def test_create_cohorts_by_acquisition_date(self, analyzer):
        """Test creating cohorts based on customer acquisition date"""
        # Arrange
        customers = [
            {'id': 1, 'acquired_date': datetime(2024, 1, 15)},
            {'id': 2, 'acquired_date': datetime(2024, 1, 20)},
            {'id': 3, 'acquired_date': datetime(2024, 2, 10)},
            {'id': 4, 'acquired_date': datetime(2024, 2, 25)},
            {'id': 5, 'acquired_date': datetime(2024, 3, 5)}
        ]

        # Act
        cohorts = analyzer.create_cohorts(
            customers,
            cohort_type='monthly',
            date_field='acquired_date'
        )

        # Assert
        assert len(cohorts) == 3  # Jan, Feb, Mar
        assert '2024-01' in cohorts
        assert len(cohorts['2024-01']) == 2

    def test_calculate_retention_rate(self, analyzer):
        """Test cohort retention rate calculation"""
        # Arrange
        cohort_data = {
            'cohort_size': 100,
            'active_users': {
                'month_0': 100,
                'month_1': 85,
                'month_2': 72,
                'month_3': 65
            }
        }

        # Act
        retention = analyzer.calculate_retention_rate(cohort_data)

        # Assert
        assert retention['month_0'] == Decimal('100.0')
        assert retention['month_1'] == Decimal('85.0')
        assert retention['month_2'] == Decimal('72.0')
        assert retention['month_3'] == Decimal('65.0')

    def test_calculate_ltv_by_cohort(self, analyzer):
        """Test lifetime value calculation by cohort"""
        # Arrange
        cohort_revenue = {
            'month_0': Decimal('5000'),
            'month_1': Decimal('4500'),
            'month_2': Decimal('4000'),
            'month_3': Decimal('3800')
        }
        cohort_size = 100

        # Act
        ltv = analyzer.calculate_cohort_ltv(cohort_revenue, cohort_size)

        # Assert
        assert ltv['total_ltv'] == Decimal('173.00')  # Total revenue / cohort size
        assert ltv['average_monthly_value'] > 0

    def test_analyze_cohort_behavior_patterns(self, analyzer):
        """Test cohort behavior pattern analysis"""
        # Arrange
        cohorts = {
            '2024-01': {'size': 100, 'active_month_3': 65},
            '2024-02': {'size': 120, 'active_month_3': 80},
            '2024-03': {'size': 150, 'active_month_3': 110}
        }

        # Act
        patterns = analyzer.analyze_behavior_patterns(cohorts)

        # Assert
        assert 'retention_trend' in patterns
        assert patterns['retention_trend'] in ['improving', 'stable', 'declining']

    def test_compare_cohorts(self, analyzer):
        """Test comparison between different cohorts"""
        # Arrange
        cohort_a = {
            'size': 100,
            'retention_rate': Decimal('65.0'),
            'ltv': Decimal('150.00')
        }

        cohort_b = {
            'size': 120,
            'retention_rate': Decimal('72.0'),
            'ltv': Decimal('180.00')
        }

        # Act
        comparison = analyzer.compare_cohorts(cohort_a, cohort_b)

        # Assert
        assert comparison['retention_difference'] > 0
        assert comparison['ltv_difference'] > 0
        assert comparison['better_performer'] == 'cohort_b'


class TestAnalysisService:
    """Integration tests for AnalysisService"""

    @pytest.fixture
    def service(self):
        """Create analysis service instance"""
        return AnalysisService()

    def test_comprehensive_market_analysis(self, service):
        """Test comprehensive market analysis workflow"""
        # Arrange
        market_data = {
            'companies': [
                {'name': 'Company A', 'revenue': Decimal('2000000'), 'growth': Decimal('15.0')},
                {'name': 'Company B', 'revenue': Decimal('1500000'), 'growth': Decimal('10.0')},
                {'name': 'Company C', 'revenue': Decimal('1000000'), 'growth': Decimal('8.0')}
            ],
            'total_market_size': Decimal('5000000'),
            'growth_threshold': Decimal('10.0')
        }

        # Act
        analysis = service.analyze_market(market_data)

        # Assert
        assert 'market_concentration' in analysis
        assert 'hhi' in analysis
        assert 'competitive_landscape' in analysis
        assert 'bcg_positions' in analysis

    def test_insufficient_data_handling(self, service):
        """Test handling of insufficient data scenarios"""
        # Arrange
        incomplete_data = {
            'companies': [
                {'name': 'Company A'}  # Missing required fields
            ]
        }

        # Act & Assert
        with pytest.raises(InsufficientDataError):
            service.analyze_market(incomplete_data)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
