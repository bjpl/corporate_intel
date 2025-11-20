"""
Data Analysis Jobs

Provides specialized jobs for data analysis and reporting.
"""

from src.jobs.analysis.statistical import StatisticalAnalysisJob
from src.jobs.analysis.reporting import ReportGenerationJob

__all__ = [
    "StatisticalAnalysisJob",
    "ReportGenerationJob",
]
