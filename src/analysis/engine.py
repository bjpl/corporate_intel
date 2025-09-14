"""Pluggable analysis engine using Strategy pattern for EdTech intelligence."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

import numpy as np
from loguru import logger

from src.core.config import get_settings


@dataclass
class AnalysisResult:
    """Standardized result from any analysis strategy."""
    
    analysis_type: str
    company_id: Optional[str]
    ticker: Optional[str]
    results: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]
    confidence_score: float
    metadata: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class AnalysisStrategy(ABC):
    """Abstract base class for analysis strategies."""
    
    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Perform analysis on provided data."""
        pass
    
    @abstractmethod
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data for this strategy."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return strategy name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return strategy description."""
        pass


class CompetitorAnalysisStrategy(AnalysisStrategy):
    """Analyze competitive positioning in EdTech market."""
    
    @property
    def name(self) -> str:
        return "competitor_analysis"
    
    @property
    def description(self) -> str:
        return "Analyze competitive positioning and market share in EdTech segments"
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        required_fields = ["companies", "metrics", "time_period"]
        return all(field in data for field in required_fields)
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        companies = data["companies"]
        metrics = data["metrics"]
        
        # Perform competitive analysis
        insights = []
        recommendations = []
        
        # Market share analysis
        market_shares = self._calculate_market_shares(companies, metrics)
        
        # Growth rate comparison
        growth_rates = self._compare_growth_rates(companies, metrics)
        
        # Efficiency metrics comparison
        efficiency = self._analyze_efficiency(companies, metrics)
        
        # Generate insights
        leader = max(market_shares.items(), key=lambda x: x[1])[0]
        insights.append(f"{leader} leads the segment with {market_shares[leader]:.1f}% market share")
        
        fastest_growing = max(growth_rates.items(), key=lambda x: x[1])[0]
        insights.append(f"{fastest_growing} shows highest growth at {growth_rates[fastest_growing]:.1f}% YoY")
        
        # Generate recommendations
        for company, share in market_shares.items():
            if share < 10:
                recommendations.append(f"{company}: Focus on niche differentiation")
            elif share < 30:
                recommendations.append(f"{company}: Expand through strategic partnerships")
            else:
                recommendations.append(f"{company}: Defend market position through innovation")
        
        return AnalysisResult(
            analysis_type=self.name,
            company_id=None,
            ticker=None,
            results={
                "market_shares": market_shares,
                "growth_rates": growth_rates,
                "efficiency_metrics": efficiency,
            },
            insights=insights,
            recommendations=recommendations,
            confidence_score=0.85,
            metadata={"companies_analyzed": len(companies)}
        )
    
    def _calculate_market_shares(self, companies: List[Dict], metrics: Dict) -> Dict[str, float]:
        """Calculate relative market shares."""
        revenues = {}
        for company in companies:
            ticker = company["ticker"]
            if ticker in metrics and "revenue" in metrics[ticker]:
                revenues[ticker] = metrics[ticker]["revenue"]
        
        total_revenue = sum(revenues.values())
        if total_revenue == 0:
            return {}
        
        return {
            ticker: (revenue / total_revenue) * 100
            for ticker, revenue in revenues.items()
        }
    
    def _compare_growth_rates(self, companies: List[Dict], metrics: Dict) -> Dict[str, float]:
        """Compare YoY growth rates."""
        growth_rates = {}
        for company in companies:
            ticker = company["ticker"]
            if ticker in metrics and "revenue_growth_yoy" in metrics[ticker]:
                growth_rates[ticker] = metrics[ticker]["revenue_growth_yoy"]
        
        return growth_rates
    
    def _analyze_efficiency(self, companies: List[Dict], metrics: Dict) -> Dict[str, Dict]:
        """Analyze operational efficiency metrics."""
        efficiency = {}
        for company in companies:
            ticker = company["ticker"]
            if ticker in metrics:
                company_metrics = metrics[ticker]
                efficiency[ticker] = {
                    "cac_to_ltv_ratio": company_metrics.get("cac", 0) / max(company_metrics.get("ltv", 1), 1),
                    "arpu": company_metrics.get("arpu", 0),
                    "gross_margin": company_metrics.get("gross_margin", 0),
                }
        
        return efficiency


class SegmentOpportunityStrategy(AnalysisStrategy):
    """Identify growth opportunities in EdTech segments."""
    
    @property
    def name(self) -> str:
        return "segment_opportunity"
    
    @property
    def description(self) -> str:
        return "Identify untapped opportunities and growth potential in EdTech segments"
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        required_fields = ["segment", "market_data", "trends"]
        return all(field in data for field in required_fields)
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        segment = data["segment"]
        market_data = data["market_data"]
        trends = data["trends"]
        
        opportunities = []
        insights = []
        recommendations = []
        
        # Analyze TAM expansion
        tam_growth = self._analyze_tam_expansion(market_data)
        if tam_growth > 15:
            opportunities.append({
                "type": "market_expansion",
                "description": f"{segment} TAM growing at {tam_growth:.1f}% annually",
                "potential": "high"
            })
        
        # Identify underserved niches
        underserved = self._identify_underserved_areas(market_data, segment)
        for niche in underserved:
            opportunities.append({
                "type": "underserved_niche",
                "description": niche["description"],
                "potential": niche["potential"]
            })
        
        # Technology adoption opportunities
        tech_opportunities = self._analyze_tech_adoption(trends)
        opportunities.extend(tech_opportunities)
        
        # Generate insights
        insights.append(f"{segment} segment shows {len(opportunities)} key growth opportunities")
        
        if tam_growth > 20:
            insights.append(f"Rapid TAM expansion indicates early-stage market with high growth potential")
        
        # Generate recommendations
        for opp in opportunities[:3]:  # Top 3 opportunities
            if opp["potential"] == "high":
                recommendations.append(f"Priority: {opp['description']}")
            else:
                recommendations.append(f"Consider: {opp['description']}")
        
        return AnalysisResult(
            analysis_type=self.name,
            company_id=None,
            ticker=None,
            results={
                "opportunities": opportunities,
                "tam_growth": tam_growth,
                "segment": segment
            },
            insights=insights,
            recommendations=recommendations,
            confidence_score=0.78,
            metadata={"segment": segment, "opportunities_found": len(opportunities)}
        )
    
    def _analyze_tam_expansion(self, market_data: Dict) -> float:
        """Calculate TAM growth rate."""
        if "tam_historical" in market_data and len(market_data["tam_historical"]) > 1:
            tam_values = market_data["tam_historical"]
            # Simple CAGR calculation
            years = len(tam_values) - 1
            if years > 0 and tam_values[0] > 0:
                cagr = ((tam_values[-1] / tam_values[0]) ** (1/years) - 1) * 100
                return cagr
        return 10.0  # Default assumption
    
    def _identify_underserved_areas(self, market_data: Dict, segment: str) -> List[Dict]:
        """Identify underserved market areas."""
        underserved = []
        
        segment_specific = {
            "k12": ["special_education", "rural_schools", "vocational_training"],
            "higher_education": ["community_colleges", "continuing_education", "micro_credentials"],
            "corporate_learning": ["frontline_workers", "soft_skills", "compliance_automation"],
            "direct_to_consumer": ["senior_learning", "family_education", "hobby_learning"],
        }
        
        if segment in segment_specific:
            for area in segment_specific[segment]:
                # Check if area is mentioned in market data
                if area not in str(market_data).lower():
                    underserved.append({
                        "description": f"Underserved: {area.replace('_', ' ').title()}",
                        "potential": "medium"
                    })
        
        return underserved
    
    def _analyze_tech_adoption(self, trends: Dict) -> List[Dict]:
        """Analyze technology adoption opportunities."""
        opportunities = []
        
        tech_trends = {
            "ai_personalization": ("AI-powered personalized learning", 0.9),
            "vr_ar_learning": ("Immersive VR/AR educational experiences", 0.7),
            "blockchain_credentials": ("Blockchain-verified credentials", 0.6),
            "adaptive_assessment": ("Adaptive assessment technologies", 0.8),
            "social_learning": ("Social and collaborative learning platforms", 0.75),
        }
        
        for tech, (description, potential_score) in tech_trends.items():
            if tech in trends and trends[tech].get("adoption_rate", 0) < 30:
                opportunities.append({
                    "type": "technology_adoption",
                    "description": description,
                    "potential": "high" if potential_score > 0.8 else "medium"
                })
        
        return opportunities


class CohortAnalysisStrategy(AnalysisStrategy):
    """Analyze user cohorts and retention patterns."""
    
    @property
    def name(self) -> str:
        return "cohort_analysis"
    
    @property
    def description(self) -> str:
        return "Analyze user cohorts, retention patterns, and LTV trends"
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        required_fields = ["cohort_data", "time_periods"]
        return all(field in data for field in required_fields)
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        cohort_data = data["cohort_data"]
        
        # Calculate retention curves
        retention_rates = self._calculate_retention(cohort_data)
        
        # Calculate LTV by cohort
        ltv_by_cohort = self._calculate_ltv(cohort_data)
        
        # Identify trends
        trends = self._identify_cohort_trends(retention_rates, ltv_by_cohort)
        
        insights = []
        recommendations = []
        
        # Generate insights
        avg_retention_m1 = np.mean([r[1] for r in retention_rates.values() if len(r) > 1])
        insights.append(f"Average Month 1 retention: {avg_retention_m1:.1f}%")
        
        if trends["retention_improving"]:
            insights.append("Retention rates improving across recent cohorts")
        else:
            insights.append("Warning: Retention rates declining in recent cohorts")
        
        # Generate recommendations
        if avg_retention_m1 < 40:
            recommendations.append("Critical: Improve onboarding to boost M1 retention")
        
        if trends["ltv_trend"] == "increasing":
            recommendations.append("Opportunity: Increase CAC budget given rising LTV")
        elif trends["ltv_trend"] == "decreasing":
            recommendations.append("Caution: Reduce CAC to maintain unit economics")
        
        return AnalysisResult(
            analysis_type=self.name,
            company_id=data.get("company_id"),
            ticker=data.get("ticker"),
            results={
                "retention_rates": retention_rates,
                "ltv_by_cohort": ltv_by_cohort,
                "trends": trends,
            },
            insights=insights,
            recommendations=recommendations,
            confidence_score=0.82,
            metadata={"cohorts_analyzed": len(cohort_data)}
        )
    
    def _calculate_retention(self, cohort_data: Dict) -> Dict[str, List[float]]:
        """Calculate retention rates by cohort."""
        retention = {}
        
        for cohort_name, cohort in cohort_data.items():
            if "users_by_month" in cohort:
                initial_users = cohort["users_by_month"][0]
                if initial_users > 0:
                    retention[cohort_name] = [
                        (users / initial_users) * 100
                        for users in cohort["users_by_month"]
                    ]
        
        return retention
    
    def _calculate_ltv(self, cohort_data: Dict) -> Dict[str, float]:
        """Calculate LTV by cohort."""
        ltv = {}
        
        for cohort_name, cohort in cohort_data.items():
            if "revenue_by_month" in cohort and "initial_users" in cohort:
                total_revenue = sum(cohort["revenue_by_month"])
                ltv[cohort_name] = total_revenue / max(cohort["initial_users"], 1)
        
        return ltv
    
    def _identify_cohort_trends(self, retention: Dict, ltv: Dict) -> Dict[str, Any]:
        """Identify trends across cohorts."""
        trends = {
            "retention_improving": False,
            "ltv_trend": "stable",
        }
        
        # Check retention trend (compare last 3 cohorts to previous 3)
        if len(retention) >= 6:
            sorted_cohorts = sorted(retention.keys())
            recent_avg = np.mean([retention[c][1] for c in sorted_cohorts[-3:] if len(retention[c]) > 1])
            older_avg = np.mean([retention[c][1] for c in sorted_cohorts[-6:-3] if len(retention[c]) > 1])
            
            trends["retention_improving"] = recent_avg > older_avg
        
        # Check LTV trend
        if len(ltv) >= 4:
            sorted_cohorts = sorted(ltv.keys())
            recent_ltv = [ltv[c] for c in sorted_cohorts[-2:]]
            older_ltv = [ltv[c] for c in sorted_cohorts[-4:-2]]
            
            if np.mean(recent_ltv) > np.mean(older_ltv) * 1.1:
                trends["ltv_trend"] = "increasing"
            elif np.mean(recent_ltv) < np.mean(older_ltv) * 0.9:
                trends["ltv_trend"] = "decreasing"
        
        return trends


class AnalysisEngine:
    """Main analysis engine that orchestrates different strategies."""
    
    def __init__(self):
        self.strategies: Dict[str, AnalysisStrategy] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register built-in analysis strategies."""
        default_strategies = [
            CompetitorAnalysisStrategy(),
            SegmentOpportunityStrategy(),
            CohortAnalysisStrategy(),
        ]
        
        for strategy in default_strategies:
            self.register_strategy(strategy)
    
    def register_strategy(self, strategy: AnalysisStrategy):
        """Register a new analysis strategy."""
        self.strategies[strategy.name] = strategy
        logger.info(f"Registered analysis strategy: {strategy.name}")
    
    def list_strategies(self) -> List[Dict[str, str]]:
        """List all available strategies."""
        return [
            {
                "name": strategy.name,
                "description": strategy.description
            }
            for strategy in self.strategies.values()
        ]
    
    def analyze(
        self,
        strategy_name: str,
        data: Dict[str, Any]
    ) -> AnalysisResult:
        """Execute analysis using specified strategy."""
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        strategy = self.strategies[strategy_name]
        
        # Validate input
        if not strategy.validate_input(data):
            raise ValueError(f"Invalid input data for strategy: {strategy_name}")
        
        # Execute analysis
        logger.info(f"Executing {strategy_name} analysis")
        result = strategy.analyze(data)
        
        return result
    
    def multi_strategy_analysis(
        self,
        data: Dict[str, Any],
        strategies: Optional[List[str]] = None
    ) -> List[AnalysisResult]:
        """Run multiple analysis strategies in parallel."""
        if strategies is None:
            strategies = list(self.strategies.keys())
        
        results = []
        
        for strategy_name in strategies:
            try:
                result = self.analyze(strategy_name, data)
                results.append(result)
            except Exception as e:
                logger.warning(f"Strategy {strategy_name} failed: {e}")
        
        return results