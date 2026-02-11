"""
NLM Data Loaders - February 10, 2026

Data loading utilities for the Nature Learning Model.

Provides:
1. Dataset loading from JSONL files
2. Text preprocessing and cleaning
3. MINDEX API connector for data fetching
4. Data augmentation for training variety
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Generator, List, Optional, Union
import re

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Text preprocessing and augmentation for NLM training data.
    
    Handles:
    - Text cleaning and normalization
    - Scientific term standardization
    - Data augmentation for training variety
    """
    
    def __init__(
        self,
        min_length: int = 50,
        max_length: int = 4096,
        remove_urls: bool = True,
        normalize_whitespace: bool = True,
    ):
        """
        Initialize the data processor.
        
        Args:
            min_length: Minimum text length to keep
            max_length: Maximum text length (truncate beyond)
            remove_urls: Whether to remove URLs from text
            normalize_whitespace: Normalize whitespace characters
        """
        self.min_length = min_length
        self.max_length = max_length
        self.remove_urls = remove_urls
        self.normalize_whitespace = normalize_whitespace
        
        # Patterns for cleaning
        self._url_pattern = re.compile(
            r'https?://\S+|www\.\S+'
        )
        self._whitespace_pattern = re.compile(r'\s+')
    
    def process(self, text: str) -> Optional[str]:
        """
        Process a single text string.
        
        Args:
            text: Raw text to process
            
        Returns:
            Processed text or None if it doesn't meet criteria
        """
        if not text:
            return None
        
        # Remove URLs
        if self.remove_urls:
            text = self._url_pattern.sub('', text)
        
        # Normalize whitespace
        if self.normalize_whitespace:
            text = self._whitespace_pattern.sub(' ', text).strip()
        
        # Check length
        if len(text) < self.min_length:
            return None
        
        # Truncate if too long
        if len(text) > self.max_length:
            # Truncate at sentence boundary if possible
            text = text[:self.max_length]
            last_period = text.rfind('.')
            if last_period > self.max_length * 0.8:
                text = text[:last_period + 1]
        
        return text
    
    def augment(
        self,
        example: Dict[str, str],
        augmentation_factor: int = 1,
    ) -> List[Dict[str, str]]:
        """
        Augment a training example with variations.
        
        Creates multiple versions of the same content with
        different phrasings to increase training variety.
        
        Args:
            example: Training example with 'instruction', 'input', 'output'
            augmentation_factor: Number of variations to create
            
        Returns:
            List of augmented examples
        """
        if augmentation_factor <= 1:
            return [example]
        
        augmented = [example]
        
        # Instruction paraphrases
        instruction_variants = [
            "As an expert in mycology and natural sciences, please respond to the following.",
            "Using your knowledge of fungi and environmental science, analyze this query.",
            "Drawing on mycological expertise, provide a detailed response.",
            "As NLM, the Nature Learning Model, address the following question.",
        ]
        
        for i in range(1, min(augmentation_factor, len(instruction_variants))):
            variant = example.copy()
            variant["instruction"] = instruction_variants[i % len(instruction_variants)]
            augmented.append(variant)
        
        return augmented
    
    def standardize_scientific_names(self, text: str) -> str:
        """
        Standardize scientific names in text.
        
        Ensures proper italicization hints and formatting.
        
        Args:
            text: Text potentially containing scientific names
            
        Returns:
            Text with standardized scientific names
        """
        # Pattern for binomial nomenclature (e.g., "Agaricus bisporus")
        # This is a simplified pattern - production would use NER
        return text  # Placeholder for actual implementation


class NLMDataLoader:
    """
    Data loader for NLM training datasets.
    
    Loads training data from JSONL files and provides
    iteration interfaces for training pipelines.
    
    Attributes:
        data_dir: Directory containing training data
        processor: Data processor for cleaning
    """
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        processor: Optional[DataProcessor] = None,
    ):
        """
        Initialize the data loader.
        
        Args:
            data_dir: Path to training data directory
            processor: DataProcessor instance for text cleaning
        """
        from ..config import get_nlm_config
        
        config = get_nlm_config()
        self.data_dir = Path(data_dir or config.data.training_data_dir)
        self.processor = processor or DataProcessor(
            min_length=config.data.min_text_length,
            max_length=config.data.max_text_length,
        )
        
        self._file_cache: Dict[str, List[Dict]] = {}
    
    def load_category(
        self,
        category: str,
        split: str = "train",
    ) -> List[Dict[str, Any]]:
        """
        Load data for a specific category.
        
        Args:
            category: Data category (e.g., 'species_taxonomy')
            split: Dataset split ('train', 'validation', 'test')
            
        Returns:
            List of training examples
        """
        cache_key = f"{category}_{split}"
        
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]
        
        file_path = self.data_dir / category / f"{category}_{split}.jsonl"
        
        if not file_path.exists():
            logger.warning(f"Data file not found: {file_path}")
            return []
        
        examples = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        example = json.loads(line)
                        
                        # Process text fields
                        if 'input' in example:
                            processed = self.processor.process(example['input'])
                            if processed:
                                example['input'] = processed
                                examples.append(example)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse line in {file_path}: {e}")
        
        self._file_cache[cache_key] = examples
        logger.info(f"Loaded {len(examples)} examples from {category}/{split}")
        
        return examples
    
    def load_all(
        self,
        categories: Optional[List[str]] = None,
        split: str = "train",
    ) -> List[Dict[str, Any]]:
        """
        Load data from all categories.
        
        Args:
            categories: Specific categories to load (None = all)
            split: Dataset split
            
        Returns:
            Combined list of all examples
        """
        from ..config import get_nlm_config
        
        config = get_nlm_config()
        categories_to_load = categories or config.data.categories
        
        all_examples = []
        for category in categories_to_load:
            examples = self.load_category(category, split)
            all_examples.extend(examples)
        
        logger.info(f"Loaded {len(all_examples)} total examples from {len(categories_to_load)} categories")
        return all_examples
    
    def iterate(
        self,
        categories: Optional[List[str]] = None,
        split: str = "train",
        shuffle: bool = True,
        batch_size: int = 1,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Iterate over training data in batches.
        
        Args:
            categories: Categories to iterate
            split: Dataset split
            shuffle: Whether to shuffle data
            batch_size: Number of examples per batch
            
        Yields:
            Batches of training examples
        """
        import random
        
        examples = self.load_all(categories, split)
        
        if shuffle:
            random.shuffle(examples)
        
        for i in range(0, len(examples), batch_size):
            yield examples[i:i + batch_size]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about loaded data.
        
        Returns:
            Statistics dictionary
        """
        from ..config import get_nlm_config
        
        config = get_nlm_config()
        stats = {
            "data_dir": str(self.data_dir),
            "categories": {},
            "total_examples": 0,
        }
        
        for category in config.data.categories:
            category_path = self.data_dir / category
            if category_path.exists():
                train_file = category_path / f"{category}_train.jsonl"
                if train_file.exists():
                    with open(train_file, 'r') as f:
                        count = sum(1 for line in f if line.strip())
                    stats["categories"][category] = count
                    stats["total_examples"] += count
        
        return stats


class MINDEXConnector:
    """
    Connector for fetching data from MINDEX knowledge base.
    
    Provides async methods to query MINDEX for:
    - Species data and taxonomy
    - Research papers and findings
    - Ecological relationships
    - Genetic sequences
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the MINDEX connector.
        
        Args:
            base_url: MINDEX API base URL
            timeout: Request timeout in seconds
        """
        from ..config import get_nlm_config
        
        config = get_nlm_config()
        self.base_url = (base_url or config.data.mindex_url).rstrip('/')
        self.timeout = timeout
        self._client = None
    
    async def _get_client(self):
        """Get or create HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def fetch_species(
        self,
        limit: int = 100,
        offset: int = 0,
        kingdom: Optional[str] = "Fungi",
    ) -> List[Dict[str, Any]]:
        """
        Fetch species data from MINDEX.
        
        Args:
            limit: Maximum records to fetch
            offset: Pagination offset
            kingdom: Filter by kingdom (default: Fungi)
            
        Returns:
            List of species records
        """
        try:
            client = await self._get_client()
            
            params = {"limit": limit, "offset": offset}
            if kingdom:
                params["kingdom"] = kingdom
            
            response = await client.get(
                f"{self.base_url}/api/species",
                params=params,
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("species", [])
            
        except Exception as e:
            logger.error(f"Failed to fetch species from MINDEX: {e}")
            return []
    
    async def fetch_taxonomy(
        self,
        species_id: Optional[str] = None,
        genus: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch taxonomy data from MINDEX.
        
        Args:
            species_id: Specific species ID
            genus: Filter by genus
            
        Returns:
            List of taxonomy records
        """
        try:
            client = await self._get_client()
            
            params = {}
            if species_id:
                params["species_id"] = species_id
            if genus:
                params["genus"] = genus
            
            response = await client.get(
                f"{self.base_url}/api/taxonomy",
                params=params,
            )
            response.raise_for_status()
            
            return response.json().get("taxonomy", [])
            
        except Exception as e:
            logger.error(f"Failed to fetch taxonomy from MINDEX: {e}")
            return []
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search MINDEX for relevant data.
        
        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results
            
        Returns:
            List of matching records
        """
        try:
            client = await self._get_client()
            
            params = {"q": query, "limit": limit}
            if category:
                params["category"] = category
            
            response = await client.get(
                f"{self.base_url}/api/search",
                params=params,
            )
            response.raise_for_status()
            
            return response.json().get("results", [])
            
        except Exception as e:
            logger.error(f"MINDEX search failed: {e}")
            return []
    
    async def fetch_for_training(
        self,
        categories: Optional[List[str]] = None,
        limit_per_category: int = 1000,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Fetch data suitable for NLM training.
        
        Iterates through categories and yields formatted records.
        
        Args:
            categories: Categories to fetch
            limit_per_category: Max records per category
            
        Yields:
            Training-formatted records
        """
        from ..config import get_nlm_config
        
        config = get_nlm_config()
        categories_to_fetch = categories or ["species_taxonomy", "mycology_research"]
        
        for category in categories_to_fetch:
            logger.info(f"Fetching {category} data from MINDEX...")
            
            if category == "species_taxonomy":
                records = await self.fetch_species(limit=limit_per_category)
                for record in records:
                    yield {
                        "id": record.get("id"),
                        "category": category,
                        "content": self._format_species_record(record),
                        "metadata": {"source": "mindex", "type": "species"},
                    }
            
            elif category == "mycology_research":
                records = await self.search("mycology research", limit=limit_per_category)
                for record in records:
                    yield {
                        "id": record.get("id"),
                        "category": category,
                        "content": record.get("content", ""),
                        "metadata": {"source": "mindex", "type": "research"},
                    }
    
    def _format_species_record(self, record: Dict[str, Any]) -> str:
        """Format a species record as training text."""
        parts = [f"Species: {record.get('scientific_name', 'Unknown')}"]
        
        if 'common_name' in record:
            parts.append(f"Common name: {record['common_name']}")
        
        if 'taxonomy' in record:
            tax = record['taxonomy']
            parts.append(
                f"Taxonomy: {tax.get('kingdom', '')} > {tax.get('phylum', '')} > "
                f"{tax.get('class', '')} > {tax.get('order', '')} > "
                f"{tax.get('family', '')} > {tax.get('genus', '')}"
            )
        
        if 'description' in record:
            parts.append(f"Description: {record['description']}")
        
        if 'habitat' in record:
            parts.append(f"Habitat: {record['habitat']}")
        
        return "\n".join(parts)
