"""Extract EdTech-specific metrics from text documents."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class ExtractedMetric:
    """Represents an extracted metric."""
    
    metric_type: str
    value: float
    unit: str
    context: str
    confidence: float
    period: Optional[str] = None


class EdTechMetricsExtractor:
    """Extract EdTech-specific metrics from text."""
    
    def __init__(self):
        self.metric_patterns = self._build_metric_patterns()
    
    def _build_metric_patterns(self) -> Dict[str, List[Tuple[re.Pattern, str]]]:
        """Build regex patterns for metric extraction."""
        return {
            "monthly_active_users": [
                (re.compile(r"(?i)(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)?\s*(?:monthly active users|MAUs)", re.IGNORECASE), "count"),
                (re.compile(r"(?i)MAUs?\s*(?:of|:)\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)?", re.IGNORECASE), "count"),
            ],
            "average_revenue_per_user": [
                (re.compile(r"(?i)ARPU\s*(?:of|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)", re.IGNORECASE), "USD"),
                (re.compile(r"(?i)average revenue per user\s*(?:of|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)", re.IGNORECASE), "USD"),
            ],
            "customer_acquisition_cost": [
                (re.compile(r"(?i)CAC\s*(?:of|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)", re.IGNORECASE), "USD"),
                (re.compile(r"(?i)customer acquisition cost\s*(?:of|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)", re.IGNORECASE), "USD"),
            ],
            "net_revenue_retention": [
                (re.compile(r"(?i)NRR\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE), "percent"),
                (re.compile(r"(?i)net revenue retention\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE), "percent"),
            ],
            "course_completion_rate": [
                (re.compile(r"(?i)completion rate\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE), "percent"),
                (re.compile(r"(?i)(\d+(?:\.\d+)?)\s*%\s*completion rate", re.IGNORECASE), "percent"),
            ],
            "subscriber_count": [
                (re.compile(r"(?i)(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)?\s*subscribers?", re.IGNORECASE), "count"),
                (re.compile(r"(?i)subscriber base\s*(?:of|:)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)?", re.IGNORECASE), "count"),
            ],
            "revenue": [
                (re.compile(r"(?i)revenue\s*(?:of|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|billion|M|B)", re.IGNORECASE), "USD"),
                (re.compile(r"(?i)\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|billion|M|B)\s*in revenue", re.IGNORECASE), "USD"),
            ],
            "gross_margin": [
                (re.compile(r"(?i)gross margin\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE), "percent"),
                (re.compile(r"(?i)(\d+(?:\.\d+)?)\s*%\s*gross margin", re.IGNORECASE), "percent"),
            ],
            "churn_rate": [
                (re.compile(r"(?i)churn rate\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE), "percent"),
                (re.compile(r"(?i)(\d+(?:\.\d+)?)\s*%\s*churn", re.IGNORECASE), "percent"),
            ],
            "lifetime_value": [
                (re.compile(r"(?i)LTV\s*(?:of|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)", re.IGNORECASE), "USD"),
                (re.compile(r"(?i)lifetime value\s*(?:of|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)", re.IGNORECASE), "USD"),
            ],
        }
    
    def extract_metrics(self, text: str) -> List[ExtractedMetric]:
        """Extract all metrics from text."""
        metrics = []
        
        for metric_type, patterns in self.metric_patterns.items():
            for pattern, unit in patterns:
                matches = pattern.finditer(text)
                
                for match in matches:
                    # Extract value
                    value_str = match.group(1).replace(",", "")
                    
                    try:
                        value = float(value_str)
                        
                        # Handle millions/billions notation
                        if "million" in match.group(0).lower() or " M" in match.group(0):
                            value *= 1e6
                        elif "billion" in match.group(0).lower() or " B" in match.group(0):
                            value *= 1e9
                        
                        # Extract context (surrounding text)
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        context = text[start:end].strip()
                        
                        # Extract period if mentioned
                        period = self._extract_period(context)
                        
                        # Calculate confidence based on context clarity
                        confidence = self._calculate_confidence(metric_type, context)
                        
                        metrics.append(ExtractedMetric(
                            metric_type=metric_type,
                            value=value,
                            unit=unit,
                            context=context,
                            confidence=confidence,
                            period=period,
                        ))
                        
                    except ValueError:
                        logger.warning(f"Could not parse value: {value_str}")
                        continue
        
        # Deduplicate metrics
        metrics = self._deduplicate_metrics(metrics)
        
        return metrics
    
    def _extract_period(self, context: str) -> Optional[str]:
        """Extract time period from context."""
        # Quarter patterns
        quarter_pattern = re.compile(r"(?i)(Q[1-4]\s*20\d{2}|[1-4]Q\s*20\d{2})")
        quarter_match = quarter_pattern.search(context)
        if quarter_match:
            return quarter_match.group(1)
        
        # Year patterns
        year_pattern = re.compile(r"(?i)(fiscal year|FY|calendar year|CY)?\s*(20\d{2})")
        year_match = year_pattern.search(context)
        if year_match:
            return year_match.group(2)
        
        # Month patterns
        month_pattern = re.compile(r"(?i)(January|February|March|April|May|June|July|August|September|October|November|December)\s*(20\d{2})")
        month_match = month_pattern.search(context)
        if month_match:
            return f"{month_match.group(1)} {month_match.group(2)}"
        
        return None
    
    def _calculate_confidence(self, metric_type: str, context: str) -> float:
        """Calculate confidence score for extracted metric."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence if metric name is explicitly mentioned
        if metric_type.replace("_", " ") in context.lower():
            confidence += 0.2
        
        # Boost if common abbreviations are used
        abbreviations = {
            "monthly_active_users": ["MAU", "MAUs"],
            "average_revenue_per_user": ["ARPU"],
            "customer_acquisition_cost": ["CAC"],
            "net_revenue_retention": ["NRR"],
            "lifetime_value": ["LTV"],
        }
        
        if metric_type in abbreviations:
            for abbr in abbreviations[metric_type]:
                if abbr in context:
                    confidence += 0.15
                    break
        
        # Boost if period is mentioned
        if self._extract_period(context):
            confidence += 0.1
        
        # Reduce if negative context
        negative_words = ["not", "excluding", "without", "except", "decline", "decrease"]
        if any(word in context.lower() for word in negative_words):
            confidence *= 0.7
        
        return min(confidence, 1.0)
    
    def _deduplicate_metrics(self, metrics: List[ExtractedMetric]) -> List[ExtractedMetric]:
        """Remove duplicate metrics, keeping highest confidence."""
        unique_metrics = {}
        
        for metric in metrics:
            key = (metric.metric_type, metric.value, metric.period)
            
            if key not in unique_metrics or metric.confidence > unique_metrics[key].confidence:
                unique_metrics[key] = metric
        
        return list(unique_metrics.values())
    
    def extract_edtech_specific_metrics(self, text: str) -> Dict[str, Any]:
        """Extract EdTech-specific metrics not covered by standard patterns."""
        metrics = {}
        
        # Engagement metrics
        engagement_patterns = {
            "daily_active_users": r"(?i)(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)?\s*(?:daily active users|DAUs)",
            "weekly_active_users": r"(?i)(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)?\s*(?:weekly active users|WAUs)",
            "session_duration": r"(?i)average session\s*(?:duration|time|length)\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\s*(?:minutes|mins)",
            "lessons_completed": r"(?i)(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)?\s*lessons? completed",
            "certificates_issued": r"(?i)(\d+(?:,\d{3})*(?:\.\d+)?)\s*certificates? issued",
        }
        
        for metric_name, pattern in engagement_patterns.items():
            match = re.search(pattern, text)
            if match:
                value_str = match.group(1).replace(",", "")
                try:
                    value = float(value_str)
                    if "million" in match.group(0).lower() or " M" in match.group(0):
                        value *= 1e6
                    metrics[metric_name] = value
                except ValueError:
                    pass
        
        # Platform metrics
        platform_patterns = {
            "schools_served": r"(?i)(\d+(?:,\d{3})*)\s*schools?",
            "teachers_using": r"(?i)(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)?\s*teachers?",
            "students_enrolled": r"(?i)(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)?\s*students? enrolled",
            "courses_available": r"(?i)(\d+(?:,\d{3})*)\s*courses? available",
            "languages_supported": r"(?i)(\d+)\s*languages? supported",
        }
        
        for metric_name, pattern in platform_patterns.items():
            match = re.search(pattern, text)
            if match:
                value_str = match.group(1).replace(",", "")
                try:
                    value = float(value_str)
                    if "million" in match.group(0).lower() or " M" in match.group(0):
                        value *= 1e6
                    metrics[metric_name] = value
                except ValueError:
                    pass
        
        return metrics