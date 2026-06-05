"""
NLM Trainer - Training pipeline for Nature Learning Model

This module handles:
1. Data preparation from Mycosoft knowledge bases
2. Preparing grounded sensory-world training data for NLM
3. Continuous learning from new data streams
4. Model evaluation and validation
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _default_nlm_home() -> Path:
    """Return a writable default NLM runtime directory."""
    return Path(os.getenv("NLM_HOME", Path.home() / ".mycosoft" / "nlm"))


class NLMTrainer:
    """
    Nature Learning Model Trainer

    Trains and fine-tunes language models on:
    - Species data (taxonomy, descriptions, characteristics)
    - Mycology research (papers, experiments, findings)
    - Environmental data (sensor readings, weather, climate)
    - Genetic data (DNA sequences, phenotypes, markers)
    - Ecological interactions (symbiosis, parasitism, etc.)
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        base_model: str = "nlm-sensory-world-model",
        training_data_path: Optional[str] = None,
        training_config: Optional[Dict[str, Any]] = None,
    ):
        nlm_home = _default_nlm_home()
        self.model_path = Path(model_path or os.getenv("NLM_MODEL_DIR", nlm_home / "models"))
        self.base_model = base_model
        self.training_data_path = Path(
            training_data_path or os.getenv("NLM_TRAINING_DATA_DIR", nlm_home / "training")
        )
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.training_data_path.mkdir(parents=True, exist_ok=True)

        # Training configuration
        self.config = {
            "base_model": base_model,
            "learning_rate": 2e-5,
            "batch_size": 4,
            "epochs": 3,
            "max_length": 2048,
            "warmup_steps": 100,
            "weight_decay": 0.01,
            "gradient_accumulation_steps": 4,
        }
        if training_config:
            self.config.update({k: v for k, v in training_config.items() if v is not None})

        # Data categories for NLM
        self.data_categories = [
            "acoustic_library",
            "species_taxonomy",
            "mycology_research",
            "environmental_sensors",
            "genetic_sequences",
            "ecological_interactions",
            "geographic_distribution",
            "cultivation_protocols",
            "compound_chemistry",
            "medical_applications",
            "conservation_status",
        ]

    async def prepare_training_data(self, categories: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Prepare training data from various Mycosoft knowledge sources.

        Returns:
            Dictionary with counts of prepared data per category
        """
        stats = {}

        selected_categories = categories or self.data_categories

        for category in selected_categories:
            category_path = self.training_data_path / category
            category_path.mkdir(exist_ok=True)

            # Fetch data from knowledge sources
            data = await self._fetch_category_data(category)

            # Format as training examples
            examples = self._format_training_examples(data, category)

            # Save to JSONL format
            output_file = category_path / f"{category}_train.jsonl"
            with open(output_file, "w") as f:
                for example in examples:
                    f.write(json.dumps(example) + "\n")

            stats[category] = len(examples)
            logger.info(f"Prepared {len(examples)} examples for {category}")

        return stats

    async def _fetch_category_data(self, category: str) -> List[Dict[str, Any]]:
        """Fetch data for a specific category from knowledge sources."""
        if category == "acoustic_library":
            return await self._fetch_acoustic_library_data()
        logger.info("No MINDEX/MAS fetch wired for category %s — skipping", category)
        return []

    async def _fetch_acoustic_library_data(self) -> List[Dict[str, Any]]:
        """Pull acoustic library blobs + human tags from MINDEX for NLM training."""
        from mycosoft_mas.integrations.mindex_library_client import MindexLibraryClient

        client = MindexLibraryClient()
        records: List[Dict[str, Any]] = []
        try:
            blobs = await client.iter_acoustic_blobs(page_size=100)
        except Exception as exc:
            logger.error("acoustic_library blob fetch failed: %s", exc)
            return []

        tags_by_blob: Dict[str, List[Dict[str, Any]]] = {}
        try:
            offset = 0
            while True:
                tag_page = await client.get_human_tags(
                    limit=200, offset=offset, training_eligible_only=True
                )
                for tag in tag_page.get("items") or []:
                    bid = str(tag.get("blob_id") or "")
                    if bid:
                        tags_by_blob.setdefault(bid, []).append(tag)
                total = int(tag_page.get("total") or 0)
                offset += len(tag_page.get("items") or [])
                if offset >= total or not tag_page.get("items"):
                    break
        except Exception as exc:
            logger.warning("human-tags fetch failed (blobs only): %s", exc)

        for blob in blobs:
            blob_id = str(blob.get("id") or "")
            human_tags = tags_by_blob.get(blob_id, [])
            labels = []
            for tag in human_tags:
                label = tag.get("human_label")
                if label:
                    labels.append(
                        {
                            "human_label": label,
                            "human_category": tag.get("human_category"),
                            "human_confidence": tag.get("human_confidence"),
                            "disputes_model": tag.get("disputes_model"),
                            "review_status": tag.get("review_status"),
                        }
                    )
            if not labels and blob.get("label_primary"):
                labels.append({"human_label": blob.get("label_primary"), "source": "library.blob"})

            wave_annotations: List[Dict[str, Any]] = []
            try:
                detail = await client.get_blob(blob_id)
                wave_annotations = detail.get("wave_annotations") or []
            except Exception:
                pass

            records.append(
                {
                    "blob_id": blob_id,
                    "labels": labels,
                    "metadata": {
                        "filename": blob.get("filename"),
                        "label_primary": blob.get("label_primary"),
                        "duration_sec": blob.get("duration_sec"),
                        "sample_rate_hz": blob.get("sample_rate_hz"),
                        "origin_dataset_id": blob.get("origin_dataset_id"),
                        "acoustic_environment": blob.get("acoustic_environment"),
                        "stream_url": client.stream_url(blob_id),
                        "wave_annotation_count": len(wave_annotations),
                    },
                    "wave_annotations": wave_annotations,
                }
            )
        logger.info("Fetched %d acoustic library training records from MINDEX", len(records))
        return records

    def _format_training_examples(self, data: List[Dict], category: str) -> List[Dict[str, Any]]:
        """
        Format raw data as instruction-following training examples.

        Uses various prompt templates for different data types.
        """
        examples: List[Dict[str, Any]] = []

        if category == "acoustic_library":
            for item in data:
                labels = item.get("labels") or []
                label_text = ", ".join(
                    str(l.get("human_label") or "") for l in labels if l.get("human_label")
                )
                meta = item.get("metadata") or {}
                examples.append(
                    {
                        "instruction": (
                            "You are NLM, the Nature Learning Model. "
                            "Classify and describe this acoustic library sample."
                        ),
                        "input": (
                            f"blob_id={item.get('blob_id')} "
                            f"file={meta.get('filename')} "
                            f"duration_sec={meta.get('duration_sec')} "
                            f"environment={meta.get('acoustic_environment')}"
                        ),
                        "output": label_text or meta.get("label_primary") or "",
                        "category": category,
                        "blob_id": item.get("blob_id"),
                        "labels": labels,
                        "metadata": meta,
                        "wave_annotations": item.get("wave_annotations") or [],
                    }
                )
            return examples

        for item in data:
            example = {
                "instruction": f"You are NLM, the Nature Learning Model by Mycosoft. "
                f"Provide expert information about {category}.",
                "input": item.get("content", ""),
                "output": item.get("content", ""),
                "category": category,
            }
            examples.append(example)

        return examples

    async def train(
        self,
        resume_from: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Train or fine-tune the NLM model.

        Args:
            resume_from: Path to checkpoint to resume from
            categories: Specific categories to train on (default: all)

        Returns:
            Training results and metrics
        """
        logger.info("Starting NLM training...")

        # Prepare data if needed. This MAS-side trainer is the control-plane
        # adapter; GPU execution is owned by the NLM engine worker.
        data_stats = await self.prepare_training_data(categories=categories)
        selected_categories = categories or self.data_categories
        sample_count = sum(data_stats.values())

        training_run = {
            "run_id": f"nlm_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "engine": "Nature Learning Model",
            "base_model": self.base_model,
            "config": self.config,
            "categories": selected_categories,
            "data_stats": data_stats,
            "sample_count": sample_count,
            "status": "data_prepared",
            "engine_status": "awaiting_nlm_engine_worker",
            "started_at": datetime.now().isoformat(),
        }

        # Save training run metadata
        run_file = self.model_path / "training_runs.json"
        runs = []
        if run_file.exists():
            runs = json.loads(run_file.read_text())
        runs.append(training_run)
        run_file.write_text(json.dumps(runs, indent=2))

        logger.info(f"Training run initialized: {training_run['run_id']}")

        return training_run

    async def evaluate(self, test_data_path: Optional[str] = None) -> Dict[str, float]:
        """
        Evaluate NLM model performance.

        Returns:
            Evaluation metrics (perplexity, accuracy, etc.)
        """
        return {
            "perplexity": 0.0,
            "accuracy": 0.0,
            "f1_score": 0.0,
            "bleu_score": 0.0,
        }

    def export_model(self, output_path: str, format: str = "gguf") -> str:
        """
        Export trained model for inference.

        Args:
            output_path: Where to save the exported model
            format: Export format (gguf, safetensors, etc.)

        Returns:
            Path to exported model
        """
        logger.info(f"Exporting NLM to {output_path} in {format} format")
        return output_path
