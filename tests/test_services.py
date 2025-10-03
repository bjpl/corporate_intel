"""Service layer unit tests."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.analysis.engine import (
    AnalysisEngine, CompetitorAnalysisStrategy,
    SegmentOpportunityStrategy, CohortAnalysisStrategy
)
from src.processing.embeddings import EmbeddingService
from src.validation.data_quality import DataQualityValidator, AnomalyDetector
from src.connectors.data_sources import DataAggregator


class TestAnalysisEngine:
    """Test analysis engine and strategies."""
    
    def test_competitor_analysis_strategy(self):
        """Test competitor analysis strategy."""
        strategy = CompetitorAnalysisStrategy()
        
        # Mock data
        company_data = {
            "id": "comp1",
            "name": "Test Corp",
            "metrics": {
                "revenue": 100000000,
                "growth": 0.25,
                "market_cap": 1000000000
            }
        }
        
        competitor_data = [
            {
                "id": "comp2",
                "name": "Competitor 1",
                "metrics": {
                    "revenue": 150000000,
                    "growth": 0.20,
                    "market_cap": 1500000000
                }
            },
            {
                "id": "comp3",
                "name": "Competitor 2",
                "metrics": {
                    "revenue": 80000000,
                    "growth": 0.30,
                    "market_cap": 800000000
                }
            }
        ]
        
        result = strategy.analyze({
            "company": company_data,
            "competitors": competitor_data
        })
        
        assert "competitive_position" in result
        assert "market_share" in result
        assert "growth_comparison" in result
        assert "recommendations" in result
        assert result["market_share"] > 0
        assert result["market_share"] < 1
    
    def test_segment_opportunity_strategy(self):
        """Test segment opportunity analysis."""
        strategy = SegmentOpportunityStrategy()
        
        segment_data = {
            "segments": [
                {
                    "name": "K-12",
                    "size": 50000000000,
                    "growth_rate": 0.08,
                    "competition": "high"
                },
                {
                    "name": "Higher Ed",
                    "size": 30000000000,
                    "growth_rate": 0.12,
                    "competition": "medium"
                },
                {
                    "name": "Corporate",
                    "size": 20000000000,
                    "growth_rate": 0.15,
                    "competition": "low"
                }
            ]
        }
        
        result = strategy.analyze(segment_data)
        
        assert "tam" in result
        assert "sam" in result
        assert "som" in result
        assert "opportunities" in result
        assert result["tam"] == 100000000000  # Sum of all segments
        assert len(result["opportunities"]) > 0
    
    def test_cohort_analysis_strategy(self):
        """Test cohort analysis strategy."""
        strategy = CohortAnalysisStrategy()
        
        # Create sample cohort data
        cohort_data = pd.DataFrame({
            "cohort": ["2023-Q1", "2023-Q1", "2023-Q2", "2023-Q2"],
            "period": [0, 1, 0, 1],
            "users": [1000, 850, 1200, 1080],
            "revenue": [100000, 95000, 120000, 118000]
        })
        
        result = strategy.analyze({"data": cohort_data})
        
        assert "retention" in result
        assert "cohort_metrics" in result
        assert "trends" in result
        assert result["retention"]["2023-Q1"] == 0.85  # 850/1000
    
    def test_analysis_engine_with_strategy(self):
        """Test analysis engine with different strategies."""
        engine = AnalysisEngine()
        
        # Set competitor strategy
        engine.set_strategy(CompetitorAnalysisStrategy())
        
        result = engine.execute_analysis({
            "company": {"metrics": {"revenue": 100000000}},
            "competitors": []
        })
        
        assert result is not None
        assert "competitive_position" in result


class TestEmbeddingService:
    """Test embedding generation service."""
    
    @patch('sentence_transformers.SentenceTransformer')
    def test_generate_embeddings(self, mock_model):
        """Test generating embeddings for text."""
        # Mock the model
        mock_instance = Mock()
        mock_instance.encode.return_value = np.random.rand(5, 384)
        mock_model.return_value = mock_instance
        
        service = EmbeddingService()
        
        texts = [
            "EdTech company with strong growth",
            "Online learning platform",
            "Language education software",
            "Corporate training solutions",
            "K-12 digital curriculum"
        ]
        
        embeddings = service.generate_embeddings(texts)
        
        assert embeddings.shape == (5, 384)
        mock_instance.encode.assert_called_once()
    
    @patch('sentence_transformers.SentenceTransformer')
    def test_semantic_search(self, mock_model):
        """Test semantic search functionality."""
        # Mock embeddings
        mock_instance = Mock()
        query_embedding = np.random.rand(1, 384)
        doc_embeddings = np.random.rand(10, 384)
        
        mock_instance.encode.side_effect = [query_embedding, doc_embeddings]
        mock_model.return_value = mock_instance
        
        service = EmbeddingService()
        
        # Mock documents
        documents = [f"Document {i}" for i in range(10)]
        
        results = service.semantic_search(
            query="Find EdTech companies",
            documents=documents,
            top_k=3
        )
        
        assert len(results) == 3
        assert all("score" in r for r in results)
        assert all("document" in r for r in results)
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        service = EmbeddingService()
        
        vec1 = np.array([1, 0, 0])
        vec2 = np.array([0, 1, 0])
        vec3 = np.array([1, 0, 0])
        
        # Orthogonal vectors
        sim1 = service.cosine_similarity(vec1, vec2)
        assert abs(sim1) < 0.01
        
        # Identical vectors
        sim2 = service.cosine_similarity(vec1, vec3)
        assert abs(sim2 - 1.0) < 0.01


class TestDataQualityValidator:
    """Test data quality validation."""
    
    def test_validate_financial_metrics(self):
        """Test financial metrics validation."""
        validator = DataQualityValidator()
        
        valid_metrics = pd.DataFrame({
            "revenue": [100000, 150000, 200000],
            "gross_margin": [0.7, 0.72, 0.68],
            "pe_ratio": [25, 30, 28]
        })
        
        is_valid, report = validator.validate_financial_metrics(valid_metrics)
        
        assert is_valid
        assert "errors" in report
        assert len(report["errors"]) == 0
    
    def test_detect_invalid_metrics(self):
        """Test detection of invalid metrics."""
        validator = DataQualityValidator()
        
        invalid_metrics = pd.DataFrame({
            "revenue": [-100000, 150000, 200000],  # Negative revenue
            "gross_margin": [0.7, 1.5, 0.68],  # Margin > 1
            "pe_ratio": [25, 30, -10]  # Negative P/E
        })
        
        is_valid, report = validator.validate_financial_metrics(invalid_metrics)
        
        assert not is_valid
        assert len(report["errors"]) > 0
        assert any("revenue" in str(e) for e in report["errors"])
        assert any("gross_margin" in str(e) for e in report["errors"])
    
    def test_anomaly_detection(self):
        """Test anomaly detection in metrics."""
        detector = AnomalyDetector()
        
        # Create data with outlier
        normal_data = np.random.normal(100, 10, 100)
        outlier = [1000]  # Clear outlier
        data = np.concatenate([normal_data, outlier])
        
        anomalies = detector.detect_outliers(pd.Series(data))
        
        assert len(anomalies) > 0
        assert 100 in anomalies  # Index of outlier
    
    def test_data_freshness_check(self):
        """Test data freshness validation."""
        validator = DataQualityValidator()
        
        # Fresh data
        fresh_date = datetime.utcnow() - timedelta(hours=1)
        is_fresh = validator.check_data_freshness(fresh_date, max_age_hours=24)
        assert is_fresh
        
        # Stale data
        stale_date = datetime.utcnow() - timedelta(days=7)
        is_fresh = validator.check_data_freshness(stale_date, max_age_hours=24)
        assert not is_fresh


class TestDataAggregator:
    """Test data aggregation from multiple sources."""
    
    @patch('src.connectors.data_sources.SECConnector')
    @patch('src.connectors.data_sources.YahooFinanceConnector')
    @patch('src.connectors.data_sources.AlphaVantageConnector')
    def test_aggregate_company_data(self, mock_alpha, mock_yahoo, mock_sec):
        """Test aggregating data from multiple sources."""
        # Mock responses
        mock_sec.return_value.get_filings.return_value = [
            {"filing_type": "10-K", "date": "2024-01-01"}
        ]
        
        mock_yahoo.return_value.get_stock_data.return_value = {
            "price": 150.00,
            "market_cap": 5000000000
        }
        
        mock_alpha.return_value.get_company_overview.return_value = {
            "revenue": 500000000,
            "employees": 1000
        }
        
        aggregator = DataAggregator()
        result = aggregator.aggregate_company_data("DUOL")
        
        assert "sec_filings" in result
        assert "stock_data" in result
        assert "fundamentals" in result
        assert result["stock_data"]["price"] == 150.00
    
    def test_calculate_composite_score(self):
        """Test composite scoring algorithm."""
        aggregator = DataAggregator()
        
        company_data = {
            "metrics": {
                "revenue_growth": 0.30,  # 30% growth
                "gross_margin": 0.70,    # 70% margin
                "market_share": 0.15,    # 15% share
                "sentiment_score": 0.8   # Positive sentiment
            }
        }
        
        score = aggregator.calculate_composite_score(company_data)
        
        assert score > 0
        assert score <= 100
        # With these strong metrics, score should be high
        assert score > 70
    
    @patch('requests.get')
    def test_rate_limiting(self, mock_get):
        """Test rate limiting for API calls."""
        aggregator = DataAggregator()
        
        # Make multiple rapid calls
        mock_get.return_value.json.return_value = {"data": "test"}
        
        start_time = datetime.utcnow()
        for _ in range(5):
            aggregator._rate_limited_request("http://api.test.com")
        end_time = datetime.utcnow()
        
        # Should have delays between calls
        duration = (end_time - start_time).total_seconds()
        assert duration > 0  # Some delay occurred


class TestDocumentProcessor:
    """Test document processing with Ray."""
    
    @patch('ray.init')
    @patch('ray.remote')
    def test_process_documents(self, mock_remote, mock_init):
        """Test distributed document processing."""
        from src.processing.document_processor import DocumentProcessor
        
        # Mock Ray
        mock_init.return_value = None
        mock_remote.return_value = lambda x: x
        
        processor = DocumentProcessor()
        
        documents = [
            {"id": "doc1", "content": "Annual report content"},
            {"id": "doc2", "content": "Quarterly earnings"},
            {"id": "doc3", "content": "Press release"}
        ]
        
        # Mock processing
        with patch.object(processor, 'process_batch') as mock_process:
            mock_process.return_value = [
                {"id": d["id"], "processed": True} for d in documents
            ]
            
            results = processor.process_documents(documents)
            
            assert len(results) == 3
            assert all(r["processed"] for r in results)
    
    def test_extract_metrics_from_text(self):
        """Test extracting financial metrics from text."""
        from src.processing.document_processor import MetricsExtractor
        
        extractor = MetricsExtractor()
        
        text = """
        The company reported revenue of $500 million for the quarter,
        representing a 25% year-over-year growth. Gross margin improved
        to 72%, while operating expenses were $100 million.
        """
        
        metrics = extractor.extract_metrics(text)
        
        assert "revenue" in metrics
        assert metrics["revenue"] == 500000000
        assert "growth_rate" in metrics
        assert metrics["growth_rate"] == 0.25
        assert "gross_margin" in metrics
        assert metrics["gross_margin"] == 0.72


class TestCacheManager:
    """Test caching functionality."""
    
    def test_cache_operations(self, mock_cache_manager):
        """Test basic cache operations."""
        cache = mock_cache_manager
        
        # Test set
        cache.set("test_key", {"data": "value"}, ttl=3600)
        cache.set.assert_called_with("test_key", '{"data": "value"}', ex=3600)
        
        # Test get
        cache.get.return_value = '{"data": "value"}'
        result = cache.get("test_key")
        assert result == '{"data": "value"}'
        
        # Test delete
        cache.delete("test_key")
        cache.delete.assert_called_with("test_key")
    
    def test_cache_decorator(self, mock_cache_manager):
        """Test cache decorator functionality."""
        from src.cache.redis_cache import cache_result
        
        @cache_result(ttl=60)
        def expensive_function(x):
            return x * 2
        
        # First call - cache miss
        result1 = expensive_function(5)
        assert result1 == 10
        
        # Second call - should use cache
        mock_cache_manager.get.return_value = "10"
        result2 = expensive_function(5)
        
        # Verify cache was checked
        assert mock_cache_manager.get.called


class TestPrefectFlows:
    """Test Prefect workflow orchestration."""
    
    @patch('prefect.flow')
    @patch('prefect.task')
    def test_sec_ingestion_flow(self, mock_task, mock_flow):
        """Test SEC filing ingestion flow."""
        from src.pipeline.sec_ingestion import SECIngestionFlow
        
        # Mock decorators
        mock_flow.side_effect = lambda fn: fn
        mock_task.side_effect = lambda fn: fn
        
        flow = SECIngestionFlow()
        
        with patch.object(flow, 'fetch_filings') as mock_fetch:
            mock_fetch.return_value = [
                {"filing_type": "10-K", "url": "http://sec.gov/test"}
            ]
            
            results = flow.run_ingestion("DUOL", ["10-K"])
            
            assert len(results) > 0
            mock_fetch.assert_called_once()
    
    @patch('prefect.task')
    def test_retry_logic(self, mock_task):
        """Test retry logic for failed tasks."""
        from src.pipeline.sec_ingestion import process_filing_with_retry
        
        mock_task.side_effect = lambda **kwargs: lambda fn: fn
        
        # Simulate failure then success
        call_count = 0
        def mock_process():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"success": True}
        
        with patch('src.pipeline.sec_ingestion.process_filing', mock_process):
            result = process_filing_with_retry({"id": "test"})
            
            assert result["success"]
            assert call_count == 3  # Failed twice, succeeded on third