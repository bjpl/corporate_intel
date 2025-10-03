"""Text chunking utilities for document processing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

import tiktoken
from loguru import logger


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    
    text: str
    start_index: int
    end_index: int
    chunk_index: int
    token_count: int
    metadata: Optional[dict] = None


class TextChunker:
    """
    Intelligent text chunking for embedding and processing.
    
    Key features:
    - Overlapping chunks for context preservation
    - Respects sentence boundaries
    - Token-aware chunking for model compatibility
    - Preserves document structure metadata
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        tokenizer: str = "cl100k_base",
        respect_sentences: bool = True
    ):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Target size of each chunk in tokens
            chunk_overlap: Number of overlapping tokens between chunks
            tokenizer: Tokenizer to use (cl100k_base for GPT-4, p50k_base for GPT-3)
            respect_sentences: Whether to respect sentence boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_sentences = respect_sentences
        
        try:
            self.tokenizer = tiktoken.get_encoding(tokenizer)
        except Exception as e:
            logger.warning(f"Failed to load tokenizer {tokenizer}: {e}, using simple splitter")
            self.tokenizer = None
    
    def chunk_text(self, text: str) -> List[TextChunk]:
        """Chunk text into overlapping segments."""
        if not text:
            return []
        
        if self.tokenizer:
            return self._chunk_with_tokens(text)
        else:
            return self._chunk_simple(text)
    
    def _chunk_with_tokens(self, text: str) -> List[TextChunk]:
        """Chunk using token counting."""
        chunks = []
        
        # Split into sentences if requested
        if self.respect_sentences:
            sentences = self._split_sentences(text)
        else:
            # Split by paragraphs as fallback
            sentences = text.split('\n\n')
        
        current_chunk = []
        current_tokens = 0
        chunk_start_idx = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = len(self.tokenizer.encode(sentence))
            
            # If single sentence exceeds chunk size, split it
            if sentence_tokens > self.chunk_size:
                # Save current chunk if it exists
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(TextChunk(
                        text=chunk_text,
                        start_index=chunk_start_idx,
                        end_index=chunk_start_idx + len(chunk_text),
                        chunk_index=chunk_index,
                        token_count=current_tokens
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_tokens = 0
                
                # Split large sentence
                sub_chunks = self._split_large_text(sentence)
                for sub_chunk in sub_chunks:
                    chunks.append(TextChunk(
                        text=sub_chunk,
                        start_index=chunk_start_idx,
                        end_index=chunk_start_idx + len(sub_chunk),
                        chunk_index=chunk_index,
                        token_count=len(self.tokenizer.encode(sub_chunk))
                    ))
                    chunk_index += 1
                    chunk_start_idx += len(sub_chunk) + 1
                
                continue
            
            # Check if adding sentence exceeds chunk size
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(TextChunk(
                    text=chunk_text,
                    start_index=chunk_start_idx,
                    end_index=chunk_start_idx + len(chunk_text),
                    chunk_index=chunk_index,
                    token_count=current_tokens
                ))
                chunk_index += 1
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0 and len(current_chunk) > 0:
                    # Calculate overlap
                    overlap_sentences = []
                    overlap_tokens = 0
                    
                    for sent in reversed(current_chunk):
                        sent_tokens = len(self.tokenizer.encode(sent))
                        if overlap_tokens + sent_tokens <= self.chunk_overlap:
                            overlap_sentences.insert(0, sent)
                            overlap_tokens += sent_tokens
                        else:
                            break
                    
                    current_chunk = overlap_sentences
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0
                    chunk_start_idx = chunk_start_idx + len(chunk_text) + 1
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Add final chunk if exists
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(TextChunk(
                text=chunk_text,
                start_index=chunk_start_idx,
                end_index=chunk_start_idx + len(chunk_text),
                chunk_index=chunk_index,
                token_count=current_tokens
            ))
        
        return chunks
    
    def _chunk_simple(self, text: str) -> List[TextChunk]:
        """Simple character-based chunking when tokenizer unavailable."""
        chunks = []
        chunk_index = 0
        
        # Approximate tokens as words * 1.3
        words_per_chunk = int(self.chunk_size / 1.3)
        words_overlap = int(self.chunk_overlap / 1.3)
        
        words = text.split()
        
        for i in range(0, len(words), words_per_chunk - words_overlap):
            chunk_words = words[i:i + words_per_chunk]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append(TextChunk(
                text=chunk_text,
                start_index=i,
                end_index=min(i + words_per_chunk, len(words)),
                chunk_index=chunk_index,
                token_count=len(chunk_words)  # Approximate
            ))
            chunk_index += 1
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Enhanced sentence splitting pattern
        sentence_endings = r'[.!?]+'
        abbreviations = {'Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Sr.', 'Jr.', 'Inc.', 'Corp.', 'Ltd.'}
        
        # Basic split
        potential_sentences = re.split(f'({sentence_endings})', text)
        
        sentences = []
        current = ""
        
        for i, part in enumerate(potential_sentences):
            current += part
            
            # Check if this is a real sentence ending
            if re.match(sentence_endings, part):
                # Look ahead to see if next part starts with capital
                if i + 1 < len(potential_sentences):
                    next_part = potential_sentences[i + 1].strip()
                    
                    # Check for abbreviations
                    last_word = current.split()[-1] if current.split() else ""
                    if last_word in abbreviations:
                        continue
                    
                    # Check for capital letter or end of text
                    if next_part and next_part[0].isupper():
                        sentences.append(current.strip())
                        current = ""
                else:
                    sentences.append(current.strip())
                    current = ""
        
        # Add remaining text
        if current.strip():
            sentences.append(current.strip())
        
        return [s for s in sentences if s]
    
    def _split_large_text(self, text: str) -> List[str]:
        """Split text that exceeds chunk size."""
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            chunks = []
            
            for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
                chunk_tokens = tokens[i:i + self.chunk_size]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append(chunk_text)
            
            return chunks
        else:
            # Fallback to character splitting
            chars_per_chunk = self.chunk_size * 4  # Approximate
            chunks = []
            
            for i in range(0, len(text), chars_per_chunk):
                chunks.append(text[i:i + chars_per_chunk])
            
            return chunks


class DocumentStructureChunker(TextChunker):
    """
    Advanced chunker that preserves document structure.
    Useful for financial documents with sections.
    """
    
    def chunk_structured_document(
        self,
        text: str,
        section_headers: Optional[List[str]] = None
    ) -> List[TextChunk]:
        """
        Chunk document while preserving structure.
        
        Args:
            text: Document text
            section_headers: List of section headers to detect
        """
        if not section_headers:
            section_headers = [
                "Executive Summary",
                "Management Discussion",
                "Financial Results",
                "Risk Factors",
                "Forward-Looking Statements",
                "Business Overview",
                "Quarterly Results",
            ]
        
        # Detect sections
        sections = self._detect_sections(text, section_headers)
        
        all_chunks = []
        
        for section_name, section_text in sections.items():
            # Chunk each section independently
            section_chunks = self.chunk_text(section_text)
            
            # Add section metadata
            for chunk in section_chunks:
                chunk.metadata = {"section": section_name}
                all_chunks.append(chunk)
        
        return all_chunks
    
    def _detect_sections(
        self,
        text: str,
        headers: List[str]
    ) -> dict[str, str]:
        """Detect document sections based on headers."""
        sections = {}
        
        # Create regex pattern for headers
        header_pattern = '|'.join(re.escape(h) for h in headers)
        pattern = re.compile(f'(?i)({header_pattern})', re.MULTILINE)
        
        matches = list(pattern.finditer(text))
        
        if not matches:
            # No sections found, treat as single section
            sections["Full Document"] = text
            return sections
        
        # Extract sections
        for i, match in enumerate(matches):
            section_name = match.group(1)
            start = match.end()
            
            # Find end of section (start of next section or end of document)
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)
            
            section_text = text[start:end].strip()
            if section_text:
                sections[section_name] = section_text
        
        # Add content before first section if exists
        if matches[0].start() > 0:
            sections["Introduction"] = text[:matches[0].start()].strip()
        
        return sections