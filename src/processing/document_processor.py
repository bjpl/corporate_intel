"""Distributed document processing using Ray."""

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import ray
from loguru import logger
from pdfplumber import PDF
from pypdf import PdfReader

from src.core.config import get_settings
from src.processing.text_chunker import TextChunker
from src.processing.metrics_extractor import EdTechMetricsExtractor


@ray.remote
class DocumentProcessor:
    """Ray actor for distributed document processing."""
    
    def __init__(self):
        self.settings = get_settings()
        self.text_chunker = TextChunker(
            chunk_size=1000,
            chunk_overlap=200,
            tokenizer="cl100k_base"  # OpenAI tokenizer
        )
        self.metrics_extractor = EdTechMetricsExtractor()
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Process a PDF document."""
        try:
            # Extract text
            text = self._extract_pdf_text(pdf_path)
            
            # Extract metadata
            metadata = self._extract_pdf_metadata(pdf_path)
            
            # Chunk text for embedding
            chunks = self.text_chunker.chunk_text(text)
            
            # Extract financial metrics
            metrics = self.metrics_extractor.extract_metrics(text)
            
            # Calculate document hash
            doc_hash = hashlib.sha256(text.encode()).hexdigest()
            
            return {
                "status": "success",
                "text": text,
                "metadata": metadata,
                "chunks": chunks,
                "metrics": metrics,
                "doc_hash": doc_hash,
                "total_pages": metadata.get("num_pages", 0),
                "total_chunks": len(chunks),
                "metrics_found": len(metrics),
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pdf_path": pdf_path,
            }
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF using multiple methods for robustness."""
        text = ""
        
        # Try pdfplumber first (better for tables)
        try:
            with PDF.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}, trying pypdf")
            
            # Fallback to pypdf
            try:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            except Exception as e:
                logger.error(f"Both PDF extraction methods failed: {e}")
                raise
        
        return text
    
    def _extract_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract PDF metadata."""
        try:
            reader = PdfReader(pdf_path)
            metadata = reader.metadata
            
            return {
                "title": str(metadata.title) if metadata.title else None,
                "author": str(metadata.author) if metadata.author else None,
                "subject": str(metadata.subject) if metadata.subject else None,
                "creator": str(metadata.creator) if metadata.creator else None,
                "producer": str(metadata.producer) if metadata.producer else None,
                "creation_date": str(metadata.creation_date) if metadata.creation_date else None,
                "modification_date": str(metadata.modification_date) if metadata.modification_date else None,
                "num_pages": len(reader.pages),
            }
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
            return {}
    
    def process_earnings_transcript(self, text: str, company_ticker: str) -> Dict[str, Any]:
        """Process earnings call transcript."""
        # Extract sections
        sections = self._extract_transcript_sections(text)
        
        # Extract metrics mentioned
        metrics = self.metrics_extractor.extract_metrics(text)
        
        # Extract guidance
        guidance = self._extract_guidance(text)
        
        # Sentiment analysis on Q&A
        qa_sentiment = self._analyze_qa_sentiment(sections.get("qa", ""))
        
        return {
            "company_ticker": company_ticker,
            "sections": sections,
            "metrics": metrics,
            "guidance": guidance,
            "qa_sentiment": qa_sentiment,
            "word_count": len(text.split()),
        }
    
    def _extract_transcript_sections(self, text: str) -> Dict[str, str]:
        """Extract standard sections from earnings transcript."""
        sections = {}
        
        # Common section patterns
        patterns = {
            "prepared_remarks": r"(?i)(prepared remarks?|opening remarks?|management discussion)",
            "qa": r"(?i)(question[- ]and[- ]answer|q\s*&\s*a|analyst questions)",
            "financial_results": r"(?i)(financial results?|financial performance|quarterly results?)",
            "guidance": r"(?i)(guidance|outlook|forward[- ]looking)",
        }
        
        for section_name, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                start = match.start()
                # Find next section or end of document
                next_section_start = len(text)
                for other_pattern in patterns.values():
                    if other_pattern != pattern:
                        other_match = re.search(other_pattern, text[start + 100:])
                        if other_match:
                            next_section_start = min(next_section_start, start + 100 + other_match.start())
                
                sections[section_name] = text[start:next_section_start].strip()
        
        return sections
    
    def _extract_guidance(self, text: str) -> Dict[str, Any]:
        """Extract forward-looking guidance from text."""
        guidance = {
            "revenue": None,
            "earnings": None,
            "users": None,
            "other_metrics": [],
        }
        
        # Revenue guidance patterns
        revenue_patterns = [
            r"(?i)revenue guidance[:\s]+\$?([\d,]+\.?\d*)\s*(million|billion)",
            r"(?i)expect revenue[:\s]+\$?([\d,]+\.?\d*)\s*(million|billion)",
            r"(?i)revenue outlook[:\s]+\$?([\d,]+\.?\d*)\s*(million|billion)",
        ]
        
        for pattern in revenue_patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1).replace(",", ""))
                multiplier = 1e6 if "million" in match.group(2).lower() else 1e9
                guidance["revenue"] = value * multiplier
                break
        
        # User growth guidance
        user_patterns = [
            r"(?i)expect[:\s]+([\d,]+)\s*(?:monthly |)active users",
            r"(?i)user growth[:\s]+([\d,]+)%",
        ]
        
        for pattern in user_patterns:
            match = re.search(pattern, text)
            if match:
                guidance["users"] = match.group(1).replace(",", "")
                break
        
        return guidance
    
    def _analyze_qa_sentiment(self, qa_text: str) -> Dict[str, float]:
        """Analyze sentiment of Q&A section."""
        if not qa_text:
            return {"positive": 0, "negative": 0, "neutral": 1.0}
        
        # Simple keyword-based sentiment (would use NLP model in production)
        positive_words = ["strong", "growth", "exceed", "positive", "improvement", "success", "opportunity"]
        negative_words = ["challenge", "decline", "difficult", "concern", "risk", "weakness", "pressure"]
        
        text_lower = qa_text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return {"positive": 0, "negative": 0, "neutral": 1.0}
        
        return {
            "positive": positive_count / total,
            "negative": negative_count / total,
            "neutral": 1 - (positive_count + negative_count) / (total + 10),  # Bias toward neutral
        }


@ray.remote
class DocumentBatchProcessor:
    """Ray actor for batch document processing."""
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.processors = [DocumentProcessor.remote() for _ in range(num_workers)]
    
    async def process_batch(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of documents in parallel."""
        logger.info(f"Processing batch of {len(documents)} documents with {self.num_workers} workers")
        
        # Distribute documents across workers
        futures = []
        for i, doc in enumerate(documents):
            worker_idx = i % self.num_workers
            processor = self.processors[worker_idx]
            
            if doc["type"] == "pdf":
                future = processor.process_pdf.remote(doc["path"])
            elif doc["type"] == "transcript":
                future = processor.process_earnings_transcript.remote(
                    doc["text"],
                    doc["company_ticker"]
                )
            else:
                logger.warning(f"Unknown document type: {doc['type']}")
                continue
            
            futures.append(future)
        
        # Gather results
        results = await ray.get(futures)
        
        # Summary statistics
        successful = sum(1 for r in results if r.get("status") == "success")
        failed = len(results) - successful
        
        logger.info(f"Batch processing complete: {successful} successful, {failed} failed")
        
        return results


def init_ray_cluster():
    """Initialize Ray cluster for distributed processing."""
    settings = get_settings()
    
    if not ray.is_initialized():
        if settings.RAY_HEAD_ADDRESS:
            # Connect to existing cluster
            ray.init(address=settings.RAY_HEAD_ADDRESS)
            logger.info(f"Connected to Ray cluster at {settings.RAY_HEAD_ADDRESS}")
        else:
            # Start local cluster
            ray.init(
                num_cpus=settings.RAY_NUM_CPUS,
                num_gpus=settings.RAY_NUM_GPUS,
                dashboard_host="0.0.0.0",
            )
            logger.info("Started local Ray cluster")
    
    # Print cluster resources
    resources = ray.cluster_resources()
    logger.info(f"Ray cluster resources: {resources}")


def shutdown_ray_cluster():
    """Shutdown Ray cluster."""
    if ray.is_initialized():
        ray.shutdown()
        logger.info("Ray cluster shutdown complete")