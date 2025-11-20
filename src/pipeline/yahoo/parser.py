"""Yahoo Finance data parsing and extraction."""

from typing import Any, Dict, List

import pandas as pd
from loguru import logger


def extract_financial_metrics(
    quarterly_income_data: pd.DataFrame,
    quarterly_balance_data: pd.DataFrame,
    info_data: Dict[str, Any],
    quarter_date: Any
) -> List[Dict[str, Any]]:
    """Extract financial metrics for a specific quarter.

    Args:
        quarterly_income_data: Quarterly income statement DataFrame
        quarterly_balance_data: Quarterly balance sheet DataFrame
        info_data: Stock info dictionary
        quarter_date: Date of the quarter to extract metrics for

    Returns:
        List of metric dictionaries ready for insertion
    """
    metrics_to_insert = []

    # Revenue (Total Revenue)
    if "Total Revenue" in quarterly_income_data.index:
        revenue = quarterly_income_data.loc["Total Revenue", quarter_date]
        if revenue and not pd.isna(revenue):
            metrics_to_insert.append({
                "metric_type": "revenue",
                "value": float(revenue),
                "unit": "USD",
                "metric_category": "financial",
            })

    # Gross Profit for margin calculation
    if "Gross Profit" in quarterly_income_data.index and "Total Revenue" in quarterly_income_data.index:
        gross_profit = quarterly_income_data.loc["Gross Profit", quarter_date]
        total_revenue = quarterly_income_data.loc["Total Revenue", quarter_date]
        if gross_profit and total_revenue and not pd.isna(gross_profit) and not pd.isna(total_revenue):
            gross_margin = (float(gross_profit) / float(total_revenue)) * 100
            metrics_to_insert.append({
                "metric_type": "gross_margin",
                "value": gross_margin,
                "unit": "percent",
                "metric_category": "financial",
            })

    # Operating Income for operating margin
    if "Operating Income" in quarterly_income_data.index and "Total Revenue" in quarterly_income_data.index:
        operating_income = quarterly_income_data.loc["Operating Income", quarter_date]
        total_revenue = quarterly_income_data.loc["Total Revenue", quarter_date]
        if operating_income and total_revenue and not pd.isna(operating_income) and not pd.isna(total_revenue):
            operating_margin = (float(operating_income) / float(total_revenue)) * 100
            metrics_to_insert.append({
                "metric_type": "operating_margin",
                "value": operating_margin,
                "unit": "percent",
                "metric_category": "financial",
            })

    # Earnings growth (from info if available)
    if "earningsGrowth" in info_data and info_data["earningsGrowth"]:
        earnings_growth = info_data["earningsGrowth"] * 100  # Convert to percentage
        metrics_to_insert.append({
            "metric_type": "earnings_growth",
            "value": float(earnings_growth),
            "unit": "percent",
            "metric_category": "financial",
        })

    return metrics_to_insert


def parse_company_data(company_data: Dict[str, Any], yf_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and combine company metadata with Yahoo Finance data.

    Args:
        company_data: Company metadata from EDTECH_COMPANIES
        yf_data: Yahoo Finance stock info

    Returns:
        Dictionary with parsed company information
    """
    return {
        "ticker": company_data["ticker"],
        "name": company_data["name"],
        "sector": company_data["sector"],
        "category": company_data["category"],
        "subcategory": company_data["subcategory"],
        "website": yf_data.get("website", ""),
        "employee_count": yf_data.get("fullTimeEmployees", 0),
        "headquarters": f"{yf_data.get('city', '')}, {yf_data.get('country', '')}".strip(", "),
    }
