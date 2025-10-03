"""
Unit Tests for Data Processing Service

Tests document parsing, embedding generation, batch processing,
and error handling for the data processing service layer.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import numpy as np
from io import BytesIO

from app.services.data_processing import (
    DataProcessingService,
    DocumentParser,
    EmbeddingGenerator,
    BatchProcessor
)
from app.core.exceptions import (
    ProcessingError,
    ValidationError,
    EmbeddingError
)


class TestDocumentParser:
    """Test suite for document parsing logic"""

    @pytest.fixture
    def parser(self):
        """Create document parser instance"""
        return DocumentParser()

    def test_parse_pdf_document_success(self, parser):
        """Test successful PDF document parsing"""
        # Arrange
        mock_pdf_content = b"%PDF-1.4 test content"
        mock_file = BytesIO(mock_pdf_content)

        with patch('PyPDF2.PdfReader') as mock_reader:
            mock_page = Mock()
            mock_page.extract_text.return_value = "Sample text from PDF"
            mock_reader.return_value.pages = [mock_page, mock_page]

            # Act
            result = parser.parse_pdf(mock_file)

            # Assert
            assert result['type'] == 'pdf'
            assert result['content'] == "Sample text from PDF\nSample text from PDF"
            assert result['page_count'] == 2
            assert 'parsed_at' in result

    def test_parse_pdf_empty_document(self, parser):
        """Test parsing empty PDF raises error"""
        # Arrange
        mock_file = BytesIO(b"")

        # Act & Assert
        with pytest.raises(ValidationError, match="Empty document"):
            parser.parse_pdf(mock_file)

    def test_parse_pdf_corrupted_file(self, parser):
        """Test parsing corrupted PDF raises error"""
        # Arrange
        mock_file = BytesIO(b"corrupted data")

        with patch('PyPDF2.PdfReader', side_effect=Exception("Invalid PDF")):
            # Act & Assert
            with pytest.raises(ProcessingError, match="Failed to parse PDF"):
                parser.parse_pdf(mock_file)

    def test_parse_text_document_success(self, parser):
        """Test successful text document parsing"""
        # Arrange
        content = "Plain text document content\nMultiple lines\nOf text"
        mock_file = BytesIO(content.encode('utf-8'))

        # Act
        result = parser.parse_text(mock_file)

        # Assert
        assert result['type'] == 'text'
        assert result['content'] == content
        assert result['encoding'] == 'utf-8'
        assert 'parsed_at' in result

    def test_parse_text_different_encoding(self, parser):
        """Test parsing text with different encoding"""
        # Arrange
        content = "Text with special chars: café, naïve"
        mock_file = BytesIO(content.encode('latin-1'))

        # Act
        result = parser.parse_text(mock_file, encoding='latin-1')

        # Assert
        assert result['content'] == content
        assert result['encoding'] == 'latin-1'

    def test_parse_html_document_success(self, parser):
        """Test successful HTML document parsing"""
        # Arrange
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Heading</h1>
                <p>Paragraph text</p>
                <script>alert('remove this');</script>
            </body>
        </html>
        """
        mock_file = BytesIO(html_content.encode('utf-8'))

        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_soup.return_value.get_text.return_value = "Heading\nParagraph text"

            # Act
            result = parser.parse_html(mock_file)

            # Assert
            assert result['type'] == 'html'
            assert 'script' not in result['content'].lower()
            assert 'Heading' in result['content']

    def test_extract_metadata_from_document(self, parser):
        """Test metadata extraction from documents"""
        # Arrange
        content = {
            'type': 'pdf',
            'content': 'Document content',
            'page_count': 5
        }

        # Act
        metadata = parser.extract_metadata(content)

        # Assert
        assert metadata['word_count'] > 0
        assert metadata['char_count'] > 0
        assert metadata['document_type'] == 'pdf'
        assert 'extracted_at' in metadata

    def test_chunk_document_for_processing(self, parser):
        """Test document chunking for batch processing"""
        # Arrange
        content = " ".join([f"Sentence {i}." for i in range(100)])
        chunk_size = 500
        overlap = 50

        # Act
        chunks = parser.chunk_text(content, chunk_size=chunk_size, overlap=overlap)

        # Assert
        assert len(chunks) > 1
        assert all(len(chunk) <= chunk_size for chunk in chunks)
        # Verify overlap between consecutive chunks
        assert chunks[0][-overlap:] in chunks[1]


class TestEmbeddingGenerator:
    """Test suite for embedding generation"""

    @pytest.fixture
    def generator(self):
        """Create embedding generator instance"""
        return EmbeddingGenerator(model_name='all-MiniLM-L6-v2')

    def test_generate_embedding_single_text(self, generator):
        """Test generating embedding for single text"""
        # Arrange
        text = "Sample text for embedding generation"

        with patch.object(generator.model, 'encode') as mock_encode:
            mock_encode.return_value = np.random.rand(384)

            # Act
            embedding = generator.generate_embedding(text)

            # Assert
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape[0] == 384
            mock_encode.assert_called_once_with(text, convert_to_numpy=True)

    def test_generate_embeddings_batch(self, generator):
        """Test generating embeddings for batch of texts"""
        # Arrange
        texts = [f"Text sample {i}" for i in range(10)]

        with patch.object(generator.model, 'encode') as mock_encode:
            mock_encode.return_value = np.random.rand(10, 384)

            # Act
            embeddings = generator.generate_embeddings_batch(texts)

            # Assert
            assert embeddings.shape == (10, 384)
            mock_encode.assert_called_once()

    def test_generate_embedding_empty_text(self, generator):
        """Test generating embedding for empty text raises error"""
        # Arrange
        text = ""

        # Act & Assert
        with pytest.raises(ValidationError, match="Empty text"):
            generator.generate_embedding(text)

    def test_generate_embedding_with_normalization(self, generator):
        """Test embedding generation with L2 normalization"""
        # Arrange
        text = "Sample text"

        with patch.object(generator.model, 'encode') as mock_encode:
            mock_encode.return_value = np.array([3.0, 4.0, 0.0])

            # Act
            embedding = generator.generate_embedding(text, normalize=True)

            # Assert
            # L2 norm should be 1.0
            assert np.isclose(np.linalg.norm(embedding), 1.0)

    def test_generate_embedding_error_handling(self, generator):
        """Test error handling in embedding generation"""
        # Arrange
        text = "Sample text"

        with patch.object(generator.model, 'encode', side_effect=Exception("Model error")):
            # Act & Assert
            with pytest.raises(EmbeddingError, match="Failed to generate embedding"):
                generator.generate_embedding(text)

    def test_similarity_calculation(self, generator):
        """Test cosine similarity calculation between embeddings"""
        # Arrange
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([0.0, 1.0, 0.0])
        emb3 = np.array([1.0, 0.0, 0.0])

        # Act
        similarity_orthogonal = generator.calculate_similarity(emb1, emb2)
        similarity_identical = generator.calculate_similarity(emb1, emb3)

        # Assert
        assert np.isclose(similarity_orthogonal, 0.0)
        assert np.isclose(similarity_identical, 1.0)

    def test_find_similar_embeddings(self, generator):
        """Test finding similar embeddings from corpus"""
        # Arrange
        query_emb = np.array([1.0, 0.0, 0.0])
        corpus_embs = np.array([
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.0, 1.0, 0.0],
            [0.8, 0.2, 0.0]
        ])
        top_k = 2

        # Act
        indices, similarities = generator.find_similar(query_emb, corpus_embs, top_k=top_k)

        # Assert
        assert len(indices) == top_k
        assert len(similarities) == top_k
        assert similarities[0] >= similarities[1]  # Descending order


class TestBatchProcessor:
    """Test suite for batch processing operations"""

    @pytest.fixture
    def processor(self):
        """Create batch processor instance"""
        return BatchProcessor(batch_size=10, max_workers=4)

    def test_process_batch_success(self, processor):
        """Test successful batch processing"""
        # Arrange
        items = list(range(25))
        process_func = lambda x: x * 2

        # Act
        results = processor.process_batch(items, process_func)

        # Assert
        assert len(results) == 25
        assert results == [i * 2 for i in range(25)]

    def test_process_batch_with_errors(self, processor):
        """Test batch processing with partial failures"""
        # Arrange
        items = list(range(10))

        def process_func(x):
            if x == 5:
                raise ValueError("Processing error")
            return x * 2

        # Act
        results = processor.process_batch(
            items,
            process_func,
            skip_errors=True
        )

        # Assert
        assert len(results) == 9  # One item failed
        assert 10 not in results  # Failed item (5*2) not in results

    def test_process_batch_fail_fast(self, processor):
        """Test batch processing with fail-fast behavior"""
        # Arrange
        items = list(range(10))

        def process_func(x):
            if x == 5:
                raise ValueError("Processing error")
            return x * 2

        # Act & Assert
        with pytest.raises(ProcessingError, match="Batch processing failed"):
            processor.process_batch(items, process_func, skip_errors=False)

    def test_process_batch_parallel_execution(self, processor):
        """Test parallel batch processing"""
        # Arrange
        items = list(range(100))

        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_executor.return_value.__enter__.return_value.map.return_value = [
                i * 2 for i in items
            ]

            # Act
            results = processor.process_batch_parallel(items, lambda x: x * 2)

            # Assert
            assert len(results) == 100
            mock_executor.assert_called_once_with(max_workers=4)

    def test_process_batch_with_progress_callback(self, processor):
        """Test batch processing with progress tracking"""
        # Arrange
        items = list(range(20))
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        # Act
        processor.process_batch(
            items,
            lambda x: x * 2,
            progress_callback=progress_callback
        )

        # Assert
        assert len(progress_calls) > 0
        assert progress_calls[-1] == (20, 20)

    def test_batch_size_optimization(self, processor):
        """Test automatic batch size optimization"""
        # Arrange
        items = list(range(1000))

        # Act
        optimal_size = processor.calculate_optimal_batch_size(
            total_items=len(items),
            item_size_bytes=1024
        )

        # Assert
        assert optimal_size > 0
        assert optimal_size <= processor.batch_size


class TestDataProcessingService:
    """Integration tests for DataProcessingService"""

    @pytest.fixture
    def service(self):
        """Create data processing service instance"""
        return DataProcessingService()

    def test_process_document_end_to_end(self, service):
        """Test complete document processing pipeline"""
        # Arrange
        mock_file = BytesIO(b"Sample document content")

        with patch.object(service.parser, 'parse_text') as mock_parse:
            with patch.object(service.embedder, 'generate_embedding') as mock_embed:
                mock_parse.return_value = {
                    'type': 'text',
                    'content': 'Sample document content',
                    'parsed_at': datetime.utcnow()
                }
                mock_embed.return_value = np.random.rand(384)

                # Act
                result = service.process_document(mock_file, 'text')

                # Assert
                assert 'document_id' in result
                assert 'parsed_content' in result
                assert 'embedding' in result
                assert result['status'] == 'success'

    def test_batch_process_documents(self, service):
        """Test batch processing multiple documents"""
        # Arrange
        documents = [
            {'file': BytesIO(b"Doc 1"), 'type': 'text'},
            {'file': BytesIO(b"Doc 2"), 'type': 'text'},
            {'file': BytesIO(b"Doc 3"), 'type': 'text'}
        ]

        with patch.object(service, 'process_document') as mock_process:
            mock_process.side_effect = [
                {'document_id': i, 'status': 'success'}
                for i in range(3)
            ]

            # Act
            results = service.batch_process_documents(documents)

            # Assert
            assert len(results) == 3
            assert all(r['status'] == 'success' for r in results)

    def test_error_recovery_mechanism(self, service):
        """Test error recovery and retry mechanism"""
        # Arrange
        mock_file = BytesIO(b"Document content")

        with patch.object(service.parser, 'parse_text') as mock_parse:
            mock_parse.side_effect = [
                Exception("Temporary error"),
                Exception("Temporary error"),
                {'type': 'text', 'content': 'Success'}
            ]

            # Act
            result = service.process_document(
                mock_file,
                'text',
                max_retries=3
            )

            # Assert
            assert result['status'] == 'success'
            assert mock_parse.call_count == 3

    def test_process_document_with_validation(self, service):
        """Test document processing with validation"""
        # Arrange
        mock_file = BytesIO(b"x" * (10 * 1024 * 1024 + 1))  # > 10MB

        # Act & Assert
        with pytest.raises(ValidationError, match="Document too large"):
            service.process_document(mock_file, 'text')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
