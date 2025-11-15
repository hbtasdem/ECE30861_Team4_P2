"""Local file storage service for model URL metadata and caching.

This module manages a local storage system that keeps track of model URLs,
their metadata, and cached responses. It stores information on disk using
JSON files for persistence.

Key features:
- Save and retrieve model URL metadata
- Cache HTTP responses from model URLs
- Track storage statistics and usage
- Provide file-based audit trail of uploaded models
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class URLStorageService:
    """Service for managing locally stored model URL metadata and cache."""

    def __init__(self, storage_dir: str = "uploads/url_storage"):
        """Initialize URL storage service.

        Args:
            storage_dir: Directory to store URL metadata (default: uploads/url_storage)
        """
        self.storage_dir = storage_dir
        self.metadata_dir = os.path.join(storage_dir, "metadata")
        self.cache_dir = os.path.join(storage_dir, "cache")

        # Create directories
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        logger.info(f"URL Storage initialized at {storage_dir}")

    def _get_metadata_path(self, model_id: int) -> str:
        """Get metadata file path for a model.

        Args:
            model_id: Model ID

        Returns:
            Path to metadata file
        """
        return os.path.join(self.metadata_dir, f"model_{model_id}_metadata.json")

    def _get_cache_path(self, model_id: int) -> str:
        """Get cache file path for a model.

        Args:
            model_id: Model ID

        Returns:
            Path to cache file
        """
        return os.path.join(self.cache_dir, f"model_{model_id}_cache.json")

    def save_url_metadata(
        self,
        model_id: int,
        name: str,
        url: str,
        description: Optional[str] = None,
        version: str = "1.0.0",
        artifact_type: str = "model",
        is_sensitive: bool = False,
        uploader_id: Optional[int] = None,
    ) -> bool:
        """Save URL metadata for a model.

        Args:
            model_id: Model ID
            name: Model name
            url: Model URL
            description: Model description
            version: Model version
            artifact_type: Type of artifact
            is_sensitive: Whether model is sensitive
            uploader_id: ID of uploader

        Returns:
            True if successful, False otherwise
        """
        try:
            metadata: Dict[str, Any] = {
                "model_id": model_id,
                "name": name,
                "url": url,
                "description": description,
                "version": version,
                "artifact_type": artifact_type,
                "is_sensitive": is_sensitive,
                "uploader_id": uploader_id,
                "registered_at": datetime.utcnow().isoformat(),
                "last_accessed": None,
            }

            metadata_path = self._get_metadata_path(model_id)
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Saved metadata for model {model_id} at {metadata_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save metadata for model {model_id}: {e}")
            return False

    def get_url_metadata(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Get URL metadata for a model.

        Args:
            model_id: Model ID

        Returns:
            Metadata dictionary if found, None otherwise
        """
        try:
            metadata_path = self._get_metadata_path(model_id)
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    return json.load(f)  # type: ignore[no-any-return]
            return None
        except Exception as e:
            logger.error(f"Failed to read metadata for model {model_id}: {e}")
            return None

    def cache_url_response(self, model_id: int, response_data: Dict[str, Any]) -> bool:
        """Cache response data from accessing a model URL.

        Args:
            model_id: Model ID
            response_data: Response data to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            cache: Dict[str, Any] = {
                "model_id": model_id,
                "cached_at": datetime.utcnow().isoformat(),
                "data": response_data,
            }

            cache_path = self._get_cache_path(model_id)
            with open(cache_path, "w") as f:
                json.dump(cache, f, indent=2)

            logger.info(f"Cached response for model {model_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cache response for model {model_id}: {e}")
            return False

    def get_cached_response(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Get cached response data for a model.

        Args:
            model_id: Model ID

        Returns:
            Cached data if available, None otherwise
        """
        try:
            cache_path = self._get_cache_path(model_id)
            if os.path.exists(cache_path):
                with open(cache_path, "r") as f:
                    return json.load(f)  # type: ignore[no-any-return]
            return None
        except Exception as e:
            logger.error(f"Failed to read cache for model {model_id}: {e}")
            return None

    def delete_url_storage(self, model_id: int) -> bool:
        """Delete all storage for a model (metadata and cache).

        Args:
            model_id: Model ID

        Returns:
            True if successful, False otherwise
        """
        try:
            metadata_path = self._get_metadata_path(model_id)
            cache_path = self._get_cache_path(model_id)

            deleted = False
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
                deleted = True

            if os.path.exists(cache_path):
                os.remove(cache_path)
                deleted = True

            if deleted:
                logger.info(f"Deleted storage for model {model_id}")

            return deleted
        except Exception as e:
            logger.error(f"Failed to delete storage for model {model_id}: {e}")
            return False

    def list_stored_urls(self) -> List[int]:
        """List all model IDs with stored URLs.

        Returns:
            List of model IDs
        """
        try:
            model_ids = []
            for filename in os.listdir(self.metadata_dir):
                if filename.startswith("model_") and filename.endswith(
                    "_metadata.json"
                ):
                    model_id_str = filename.replace("model_", "").replace(
                        "_metadata.json", ""
                    )
                    try:
                        model_ids.append(int(model_id_str))
                    except ValueError:
                        continue
            return sorted(model_ids)
        except Exception as e:
            logger.error(f"Failed to list stored URLs: {e}")
            return []

    def get_storage_stats(self) -> Dict[str, int]:
        """Get statistics about URL storage.

        Returns:
            Dictionary with storage statistics
        """
        try:
            metadata_count = len(
                [
                    f
                    for f in os.listdir(self.metadata_dir)
                    if f.endswith("_metadata.json")
                ]
            )
            cache_count = len(
                [f for f in os.listdir(self.cache_dir) if f.endswith("_cache.json")]
            )

            metadata_size = sum(
                os.path.getsize(os.path.join(self.metadata_dir, f))
                for f in os.listdir(self.metadata_dir)
            )
            cache_size = sum(
                os.path.getsize(os.path.join(self.cache_dir, f))
                for f in os.listdir(self.cache_dir)
            )

            return {
                "metadata_files": metadata_count,
                "cache_files": cache_count,
                "metadata_size_bytes": metadata_size,
                "cache_size_bytes": cache_size,
                "total_size_bytes": metadata_size + cache_size,
            }
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}
