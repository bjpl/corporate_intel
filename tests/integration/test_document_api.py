"""
Integration tests for Document API endpoints.
Tests document upload, vector search, processing status, and chunk retrieval.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict
import io
from datetime import datetime

from app.main import app
from app.models.company import Company, CompanyStatus
from app.models.document import Document, DocumentType, ProcessingStatus


class TestDocumentAPI:
    """Integration tests for document endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient, db: Session, auth_headers: Dict[str, str]):
        """Setup test fixtures."""
        self.client = client
        self.db = db
        self.headers = auth_headers

        # Create test company
        self.company = Company(
            name="DocTest Corp",
            ticker="DTST",
            industry="Technology",
            sector="Software",
            status=CompanyStatus.ACTIVE
        )
        self.db.add(self.company)
        self.db.commit()

        # Create test documents
        self.test_documents = [
            Document(
                company_id=self.company.id,
                title="Q1 2024 Earnings Report",
                document_type=DocumentType.EARNINGS_REPORT,
                file_path="/documents/earnings_q1_2024.pdf",
                file_size=1024000,
                mime_type="application/pdf",
                status=ProcessingStatus.COMPLETED,
                content="This is the Q1 2024 earnings report..."
            ),
            Document(
                company_id=self.company.id,
                title="Annual Report 2023",
                document_type=DocumentType.ANNUAL_REPORT,
                file_path="/documents/annual_2023.pdf",
                file_size=2048000,
                mime_type="application/pdf",
                status=ProcessingStatus.COMPLETED,
                content="Annual report for fiscal year 2023..."
            ),
            Document(
                company_id=self.company.id,
                title="Press Release - Product Launch",
                document_type=DocumentType.PRESS_RELEASE,
                file_path="/documents/press_release_2024.txt",
                file_size=50000,
                mime_type="text/plain",
                status=ProcessingStatus.PROCESSING
            )
        ]

        for doc in self.test_documents:
            self.db.add(doc)
        self.db.commit()

        yield

        # Cleanup
        self.db.query(Document).delete()
        self.db.query(Company).delete()
        self.db.commit()

    def test_upload_document_success(self):
        """Test POST /documents/upload - successful upload."""
        # Create test file
        file_content = b"Test document content for upload"
        file = io.BytesIO(file_content)

        files = {
            "file": ("test_document.pdf", file, "application/pdf")
        }
        data = {
            "company_id": self.company.id,
            "title": "Test Upload Document",
            "document_type": "sec_filing"
        }

        response = self.client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data,
            headers=self.headers
        )

        assert response.status_code == 201
        result = response.json()
        assert result["title"] == "Test Upload Document"
        assert result["document_type"] == "sec_filing"
        assert result["status"] == "pending"
        assert "id" in result

        # Verify in database
        doc = self.db.query(Document).filter(
            Document.title == "Test Upload Document"
        ).first()
        assert doc is not None
        assert doc.file_size > 0

    def test_upload_document_invalid_type(self):
        """Test POST /documents/upload with invalid file type."""
        file_content = b"Invalid file content"
        file = io.BytesIO(file_content)

        files = {
            "file": ("test.exe", file, "application/x-msdownload")
        }
        data = {
            "company_id": self.company.id,
            "title": "Invalid File"
        }

        response = self.client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data,
            headers=self.headers
        )
        assert response.status_code == 400

    def test_upload_document_too_large(self):
        """Test POST /documents/upload with file too large."""
        # Create large file (> max size)
        large_content = b"x" * (100 * 1024 * 1024)  # 100 MB
        file = io.BytesIO(large_content)

        files = {
            "file": ("large_file.pdf", file, "application/pdf")
        }
        data = {
            "company_id": self.company.id,
            "title": "Large File"
        }

        response = self.client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data,
            headers=self.headers
        )
        assert response.status_code == 413

    def test_upload_document_unauthorized(self):
        """Test POST /documents/upload without authentication."""
        file_content = b"Test content"
        file = io.BytesIO(file_content)

        files = {"file": ("test.pdf", file, "application/pdf")}
        data = {"company_id": self.company.id, "title": "Test"}

        response = self.client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data
        )
        assert response.status_code == 401

    def test_list_documents_success(self):
        """Test GET /documents - successful list retrieval."""
        response = self.client.get(
            f"/api/v1/documents?company_id={self.company.id}",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3

    def test_list_documents_filter_by_type(self):
        """Test GET /documents filtered by document type."""
        response = self.client.get(
            f"/api/v1/documents?company_id={self.company.id}"
            f"&document_type=earnings_report",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(
            item["document_type"] == "earnings_report"
            for item in data["items"]
        )

    def test_list_documents_filter_by_status(self):
        """Test GET /documents filtered by processing status."""
        response = self.client.get(
            f"/api/v1/documents?company_id={self.company.id}"
            f"&status=completed",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(
            item["status"] == "completed"
            for item in data["items"]
        )

    def test_get_document_success(self):
        """Test GET /documents/{id} - successful retrieval."""
        doc_id = self.test_documents[0].id
        response = self.client.get(
            f"/api/v1/documents/{doc_id}",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert data["title"] == "Q1 2024 Earnings Report"

    def test_get_document_not_found(self):
        """Test GET /documents/{id} - non-existent document."""
        response = self.client.get(
            "/api/v1/documents/99999",
            headers=self.headers
        )
        assert response.status_code == 404

    def test_get_document_processing_status(self):
        """Test GET /documents/{id}/status - processing status."""
        doc_id = self.test_documents[2].id  # Processing document
        response = self.client.get(
            f"/api/v1/documents/{doc_id}/status",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "progress" in data

    def test_vector_search_success(self):
        """Test POST /documents/search - vector search."""
        payload = {
            "query": "earnings revenue profit",
            "company_id": self.company.id,
            "limit": 10
        }

        response = self.client.post(
            "/api/v1/documents/search",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data

        # Verify result structure
        if data["results"]:
            result = data["results"][0]
            assert "document_id" in result
            assert "score" in result
            assert "chunks" in result

    def test_vector_search_with_filters(self):
        """Test POST /documents/search with filters."""
        payload = {
            "query": "financial report",
            "company_id": self.company.id,
            "document_types": ["earnings_report", "annual_report"],
            "min_score": 0.5,
            "limit": 5
        }

        response = self.client.post(
            "/api/v1/documents/search",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify filters applied
        for result in data["results"]:
            assert result["score"] >= 0.5

    def test_vector_search_semantic_query(self):
        """Test POST /documents/search with semantic query."""
        payload = {
            "query": "What were the company's financial results?",
            "company_id": self.company.id,
            "semantic": True
        }

        response = self.client.post(
            "/api/v1/documents/search",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_get_document_chunks_success(self):
        """Test GET /documents/{id}/chunks - chunk retrieval."""
        doc_id = self.test_documents[0].id
        response = self.client.get(
            f"/api/v1/documents/{doc_id}/chunks",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "chunks" in data
        assert "total" in data

        # Verify chunk structure
        if data["chunks"]:
            chunk = data["chunks"][0]
            assert "id" in chunk
            assert "content" in chunk
            assert "chunk_index" in chunk
            assert "embeddings" in chunk or "embedding_id" in chunk

    def test_get_document_chunks_pagination(self):
        """Test GET /documents/{id}/chunks with pagination."""
        doc_id = self.test_documents[0].id
        response = self.client.get(
            f"/api/v1/documents/{doc_id}/chunks?skip=0&limit=5",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["chunks"]) <= 5

    def test_get_specific_chunk(self):
        """Test GET /documents/{id}/chunks/{chunk_id}."""
        doc_id = self.test_documents[0].id
        chunk_id = 1

        response = self.client.get(
            f"/api/v1/documents/{doc_id}/chunks/{chunk_id}",
            headers=self.headers
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "content" in data
            assert "embeddings" in data

    def test_delete_document_success(self):
        """Test DELETE /documents/{id} - successful deletion."""
        doc_id = self.test_documents[0].id
        response = self.client.delete(
            f"/api/v1/documents/{doc_id}",
            headers=self.headers
        )

        assert response.status_code == 204

        # Verify deleted
        doc = self.db.query(Document).filter(
            Document.id == doc_id
        ).first()
        assert doc is None

    def test_reprocess_document(self):
        """Test POST /documents/{id}/reprocess."""
        doc_id = self.test_documents[0].id
        response = self.client.post(
            f"/api/v1/documents/{doc_id}/reprocess",
            headers=self.headers
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending" or data["status"] == "processing"

    def test_batch_upload_documents(self):
        """Test POST /documents/batch-upload."""
        files = [
            ("files", ("doc1.pdf", io.BytesIO(b"content1"), "application/pdf")),
            ("files", ("doc2.pdf", io.BytesIO(b"content2"), "application/pdf"))
        ]
        data = {
            "company_id": self.company.id,
            "document_type": "sec_filing"
        }

        response = self.client.post(
            "/api/v1/documents/batch-upload",
            files=files,
            data=data,
            headers=self.headers
        )

        assert response.status_code == 201
        result = response.json()
        assert "uploaded" in result
        assert result["uploaded"] == 2
