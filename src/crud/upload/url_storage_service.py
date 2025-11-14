"""Local file storage service for model URL metadata and caching.

Per OpenAPI v3.4.4 - URL Storage and Metadata Management

FILE PURPOSE:
Manages local filesystem storage of model URL metadata and HTTP response cache.
Maintains JSON-based audit trail of uploaded models and their URLs.
Provides statistics and management functions for stored metadata.

STORAGE STRUCTURE:
uploads/url_storage/
  ├── metadata/
  │   ├── model_1_metadata.json
  │   ├── model_2_metadata.json
  │   └── ...
  └── cache/
      ├── model_1_cache.json
      ├── model_2_cache.json
      └── ...

METADATA FILES:
Format: JSON
Path: {storage_dir}/metadata/model_{model_id}_metadata.json
Contents:
{
  "model_id": 123,
  "name": "bert-base-uncased",
  "url": "https://huggingface.co/models/bert-base-uncased",
  "description": "BERT model for text classification",
  "version": "1.0.0",
  "artifact_type": "model",
  "is_sensitive": false,
  "uploader_id": 456,
  "registered_at": "2024-01-15T10:30:00Z",
  "last_accessed": "2024-01-15T10:35:00Z"
}

CACHE FILES:
Format: JSON
Path: {storage_dir}/cache/model_{model_id}_cache.json
Contents:
{
  "model_id": 123,
  "cached_at": "2024-01-15T10:30:00Z",
  "data": {
    "http_status": 200,
    "headers": {...},
    "response_size": 12345,
    "response_time_ms": 156
  }
}

CORE METHODS:

1. save_url_metadata(model_id, name, url, ...) → bool
   Purpose: Persist model metadata to filesystem
   Returns: True if successful, False on error
   Called: After artifact registration (POST /api/models/upload)

2. get_url_metadata(model_id) → Optional[Dict]
   Purpose: Load model metadata from filesystem
   Returns: Dict with metadata or None if not found
   Called: For audit trail and model information retrieval

3. cache_url_response(model_id, response_data) → bool
   Purpose: Cache HTTP response from model URL access
   Returns: True if successful, False on error
   Called: After successful URL validation/fetch

4. get_cached_response(model_id) → Optional[Dict]
   Purpose: Retrieve cached URL response
   Returns: Dict with cached data or None if not found
   Called: To avoid repeated HTTP requests to same URL

5. delete_url_storage(model_id) → bool
   Purpose: Remove metadata and cache for a model
   Returns: True if deleted, False if not found
   Called: When artifact is deleted

6. list_stored_urls() → List[int]
   Purpose: Get all model IDs with stored metadata
   Returns: List of model IDs (sorted)
   Called: For audit reports and statistics

7. get_storage_stats() → Dict[str, int]
   Purpose: Get statistics about stored data
   Returns: Dict with counts and sizes
   Example: {
     "metadata_files": 42,
     "cache_files": 38,
     "metadata_size_bytes": 125440,
     "cache_size_bytes": 234560,
     "total_size_bytes": 360000
   }

ERROR HANDLING:
- FileNotFoundError: Returns None or False depending on method
- JSONDecodeError: Logs error and returns None
- PermissionError: Logs error and returns False
- DiskSpace: Raises RuntimeError with message

LOGGING:
- INFO: Successful operations (save, load, delete)
- ERROR: Failed operations (file I/O errors, JSON parsing)
- All operations logged with model_id for audit trail

DATABASE RELATIONSHIP:
- Complements database storage of artifact metadata
- Serves as backup/audit trail for URLs
- Used by URL validation system before registration
- Tracks: registration_time, uploader_id, version history

Persistence:
- Data survives server restarts
- Manual deletion required to remove metadata
- Backup-friendly (flat JSON files)
- Easy to analyze with standard tools

Specification Alignment:
- Per Section 3.4: URL metadata persistence
- Per Section 3.2.1: Artifact source URL tracking
- Per Section 3.3: Audit trail requirements
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
        uploader_id: Optional[int] = None
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
                'model_id': model_id,
                'name': name,
                'url': url,
                'description': description,
                'version': version,
                'artifact_type': artifact_type,
                'is_sensitive': is_sensitive,
                'uploader_id': uploader_id,
                'registered_at': datetime.utcnow().isoformat(),
                'last_accessed': None
            }

            metadata_path = self._get_metadata_path(model_id)
            with open(metadata_path, 'w') as f:
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
                with open(metadata_path, 'r') as f:
                    return json.load(f)  # type: ignore[no-any-return]
            return None
        except Exception as e:
            logger.error(f"Failed to read metadata for model {model_id}: {e}")
            return None

    def cache_url_response(
        self,
        model_id: int,
        response_data: Dict[str, Any]
    ) -> bool:
        """Cache response data from accessing a model URL.

        Args:
            model_id: Model ID
            response_data: Response data to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            cache: Dict[str, Any] = {
                'model_id': model_id,
                'cached_at': datetime.utcnow().isoformat(),
                'data': response_data
            }

            cache_path = self._get_cache_path(model_id)
            with open(cache_path, 'w') as f:
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
                with open(cache_path, 'r') as f:
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
                if filename.startswith('model_') and filename.endswith('_metadata.json'):
                    model_id_str = filename.replace('model_', '').replace('_metadata.json', '')
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
                [f for f in os.listdir(self.metadata_dir) if f.endswith('_metadata.json')]
            )
            cache_count = len(
                [f for f in os.listdir(self.cache_dir) if f.endswith('_cache.json')]
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
                'metadata_files': metadata_count,
                'cache_files': cache_count,
                'metadata_size_bytes': metadata_size,
                'cache_size_bytes': cache_size,
                'total_size_bytes': metadata_size + cache_size
            }
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}
