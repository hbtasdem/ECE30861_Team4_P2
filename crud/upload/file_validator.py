"""File validation service for Phase 4 upload enhancements.

Provides comprehensive file validation including:
- MIME type validation
- Size validation
- Metadata extraction
- Malware scan integration
"""

import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional

from crud.upload.file_schemas import (
    FileValidationRequest,
    FileValidationResult,
    FileValidationResponse,
)


class FileValidator:
    """Service for validating uploaded files."""

    # Allowed MIME types for models
    ALLOWED_MIME_TYPES = {
        "application/octet-stream",
        "application/zip",
        "application/gzip",
        "application/x-tar",
        "text/plain",
        "application/json",
        "application/x-python",
        "application/x-hdf",  # HDF5 for PyTorch models
        "application/octet-stream",  # Generic binary
        "image/png",
        "image/jpeg",
        "text/csv",
    }

    # Maximum file size by type (in bytes)
    MAX_SIZES_BY_TYPE = {
        "model": 10 * 1024 * 1024 * 1024,  # 10GB
        "dataset": 50 * 1024 * 1024 * 1024,  # 50GB
        "code": 1 * 1024 * 1024 * 1024,  # 1GB
        "default": 1 * 1024 * 1024 * 1024,  # 1GB default
    }

    def __init__(self):
        """Initialize file validator."""
        self.validation_results: dict[str, list[FileValidationResult]] = {}

    async def validate_mime_type(
        self,
        filename: str,
        content_type: Optional[str] = None,
        strict: bool = False
    ) -> FileValidationResult:
        """
        Validate MIME type of file.

        Args:
            filename: Original filename
            content_type: Provided content type
            strict: If True, only allow known types

        Returns:
            Validation result
        """
        # Guess MIME type from filename
        guessed_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        # Use provided content type if available, otherwise guessed
        actual_type = content_type or guessed_type

        # In strict mode, check against allowed list
        is_valid = True
        message = f"MIME type {actual_type} is acceptable"

        if strict and actual_type not in self.ALLOWED_MIME_TYPES:
            is_valid = False
            message = f"MIME type {actual_type} not in allowed list"

        return FileValidationResult(
            file_id="",  # Will be set by caller
            validation_type="mime_type",
            is_valid=is_valid,
            message=message,
            details={
                "guessed_type": guessed_type,
                "provided_type": content_type,
                "actual_type": actual_type,
            },
            checked_at=datetime.utcnow()
        )

    async def validate_size(
        self,
        file_size_bytes: int,
        filename: str = "",
        artifact_type: str = "default",
        max_size: Optional[int] = None
    ) -> FileValidationResult:
        """
        Validate file size.

        Args:
            file_size_bytes: Size of file in bytes
            filename: Original filename
            artifact_type: Type of artifact (model, dataset, code)
            max_size: Optional override for max size

        Returns:
            Validation result
        """
        limit = max_size or self.MAX_SIZES_BY_TYPE.get(artifact_type, 1 * 1024 * 1024 * 1024)
        is_valid = file_size_bytes <= limit

        if is_valid:
            message = f"File size {file_size_bytes} bytes is within limit"
        else:
            message = f"File size {file_size_bytes} bytes exceeds limit of {limit} bytes"

        return FileValidationResult(
            file_id="",  # Will be set by caller
            validation_type="size",
            is_valid=is_valid,
            message=message,
            details={
                "file_size_bytes": file_size_bytes,
                "limit_bytes": limit,
                "size_mb": round(file_size_bytes / (1024 * 1024), 2),
                "limit_mb": round(limit / (1024 * 1024), 2),
            },
            checked_at=datetime.utcnow()
        )

    async def validate_filename(
        self,
        filename: str
    ) -> FileValidationResult:
        """
        Validate filename for safety.

        Args:
            filename: Original filename

        Returns:
            Validation result
        """
        is_valid = True
        issues: list[str] = []

        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            is_valid = False
            issues.append("Filename contains path traversal")

        # Check for null bytes
        if "\x00" in filename:
            is_valid = False
            issues.append("Filename contains null bytes")

        # Check length
        if len(filename) > 255:
            is_valid = False
            issues.append("Filename exceeds 255 characters")

        # Check for special characters
        path = Path(filename)
        if not all(c.isprintable() for c in path.name):
            is_valid = False
            issues.append("Filename contains non-printable characters")

        message = "Filename is valid" if is_valid else f"Filename issues: {', '.join(issues)}"

        return FileValidationResult(
            file_id="",
            validation_type="filename",
            is_valid=is_valid,
            message=message,
            details={
                "filename": filename,
                "length": len(filename),
                "issues": issues,
            },
            checked_at=datetime.utcnow()
        )

    async def validate_metadata_extraction(
        self,
        file_content: bytes,
        filename: str
    ) -> FileValidationResult:
        """
        Extract and validate file metadata.

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Validation result with metadata
        """
        metadata = {
            "filename": filename,
            "size_bytes": len(file_content),
            "extension": Path(filename).suffix.lower(),
        }

        # Extract magic bytes for file type detection
        magic_bytes = file_content[:4].hex() if len(file_content) >= 4 else ""
        metadata["magic_bytes"] = magic_bytes

        # Detect file type from magic bytes
        file_type = self._detect_file_type(file_content)
        metadata["detected_type"] = file_type

        return FileValidationResult(
            file_id="",
            validation_type="metadata",
            is_valid=True,
            message="Metadata extracted successfully",
            details=metadata,
            checked_at=datetime.utcnow()
        )

    async def validate_malware_scan(
        self,
        file_content: bytes,
        filename: str,
        scan_enabled: bool = True
    ) -> FileValidationResult:
        """
        Check file for malware (integration point for external scanners).

        In production, this would integrate with:
        - VirusTotal API
        - ClamAV
        - AWS Macie
        - Custom ML-based detector

        Args:
            file_content: File content as bytes
            filename: Original filename
            scan_enabled: Whether to perform scan

        Returns:
            Validation result
        """
        if not scan_enabled:
            return FileValidationResult(
                file_id="",
                validation_type="malware",
                is_valid=True,
                message="Malware scan disabled",
                details={"scan_enabled": False},
                checked_at=datetime.utcnow()
            )

        # TODO: Integrate with actual malware scanner
        # For now, do basic heuristic checks
        is_valid = await self._heuristic_malware_check(file_content, filename)

        message = "File passed malware scan" if is_valid else "File flagged by malware scan"

        return FileValidationResult(
            file_id="",
            validation_type="malware",
            is_valid=is_valid,
            message=message,
            details={
                "scan_type": "heuristic",
                "engine": "integrated_scanner",
            },
            checked_at=datetime.utcnow()
        )

    async def _heuristic_malware_check(self, file_content: bytes, filename: str) -> bool:
        """
        Basic heuristic checks for malware.

        Args:
            file_content: File content
            filename: Filename

        Returns:
            True if file passes checks, False otherwise
        """
        # Check for executable signatures
        suspicious_signatures = [
            b"MZ\x90\x00",  # PE executable
            b"#!\x2fbin\x2fbash",  # Bash script with shebang
            b"#!\x2fbin\x2fsh",  # Shell script
        ]

        for sig in suspicious_signatures:
            if sig in file_content[:512]:  # Check first 512 bytes
                # Allow if it's explicitly a script/executable
                if filename.endswith((".sh", ".exe", ".dll")):
                    continue
                return False

        # Check for suspicious strings
        try:
            text = file_content[:10000].decode("utf-8", errors="ignore")
            suspicious_patterns = [
                "eval(",
                "exec(",
                "system(",
                "subprocess",
                "/bin/bash",
                "cmd.exe",
            ]
            for pattern in suspicious_patterns:
                if pattern in text and not filename.endswith((".py", ".sh", ".js")):
                    return False
        except Exception:
            pass

        return True

    def _detect_file_type(self, file_content: bytes) -> str:
        """
        Detect file type from magic bytes.

        Args:
            file_content: File content

        Returns:
            Detected file type
        """
        # Check common file signatures
        signatures = {
            b"\x89PNG": "PNG image",
            b"\xff\xd8\xff": "JPEG image",
            b"PK\x03\x04": "ZIP archive",
            b"\x1f\x8b\x08": "GZIP archive",
            b"BM": "BMP image",
            b"%PDF": "PDF document",
            b"\x50\x4b": "Office document",
            b"\xfd7zXZ": "7z archive",
            b"Rar!": "RAR archive",
        }

        for sig, file_type in signatures.items():
            if file_content.startswith(sig):
                return file_type

        return "Unknown/Binary"

    async def validate_file(
        self,
        file_id: str,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        artifact_type: str = "default",
        options: Optional[dict] = None
    ) -> FileValidationResponse:
        """
        Perform comprehensive file validation.

        Args:
            file_id: File ID for tracking
            file_content: File content as bytes
            filename: Original filename
            content_type: Provided content type
            artifact_type: Type of artifact
            options: Validation options

        Returns:
            Complete validation response
        """
        if options is None:
            options = {}

        results: list[FileValidationResult] = []

        # Filename validation
        filename_result = await self.validate_filename(filename)
        filename_result.file_id = file_id
        results.append(filename_result)

        # Size validation
        size_result = await self.validate_size(
            len(file_content),
            filename,
            artifact_type,
            options.get("max_size")
        )
        size_result.file_id = file_id
        results.append(size_result)

        # MIME type validation
        mime_result = await self.validate_mime_type(
            filename,
            content_type,
            options.get("strict_mime_type", False)
        )
        mime_result.file_id = file_id
        results.append(mime_result)

        # Metadata extraction
        metadata_result = await self.validate_metadata_extraction(file_content, filename)
        metadata_result.file_id = file_id
        results.append(metadata_result)

        # Malware scan (optional)
        if options.get("scan_malware", True):
            malware_result = await self.validate_malware_scan(
                file_content,
                filename,
                options.get("malware_scan_enabled", True)
            )
            malware_result.file_id = file_id
            results.append(malware_result)

        # Determine overall status
        all_passed = all(r.is_valid for r in results)
        has_warnings = any(
            r.validation_type == "malware" and not r.is_valid for r in results
        )

        overall_status = "valid"
        if has_warnings:
            overall_status = "warnings"
        elif not all_passed:
            overall_status = "invalid"

        return FileValidationResponse(
            file_id=file_id,
            overall_status=overall_status,
            validations=results,
            all_passed=all_passed
        )
