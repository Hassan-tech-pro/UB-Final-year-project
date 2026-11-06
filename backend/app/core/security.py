import os
import re
from pathlib import Path
from fastapi import HTTPException
from .config import settings

class SecurityError(Exception):
    """Raised when an operation violates security policies."""
    pass

class SecurityManager:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitizes filename by stripping directory separators and illegal characters."""
        clean_name = os.path.basename(filename)
        # Strip illegal characters but allow dots and dashes
        clean_name = re.sub(r'[^\w\s\.-]', '_', clean_name).strip()
        if not clean_name:
            clean_name = "unnamed_file"
        return clean_name

    @staticmethod
    def validate_file_extension(filename: str) -> str:
        """Validates that file has an allowed extension."""
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise SecurityError(
                f"File extension '{ext}' is not permitted. Allowed: {sorted(list(settings.ALLOWED_EXTENSIONS))}"
            )
        return ext

    @staticmethod
    def resolve_safe_path(target_path: str | Path, allow_create_parent: bool = True) -> Path:
        """
        Resolves a given path and ensures it stays strictly within the permitted workspace,
        upload, artifact, or sample_data directories.
        Prevents directory traversal attacks.
        """
        raw_path = Path(target_path)

        # If it's a relative path, assume it belongs in the WORKSPACE_DIR
        if not raw_path.is_absolute():
            resolved = (settings.WORKSPACE_DIR / raw_path).resolve()
        else:
            resolved = raw_path.resolve()

        # Check against allowed root directories
        allowed_roots = [
            settings.WORKSPACE_DIR.resolve(),
            settings.UPLOAD_DIR.resolve(),
            settings.ARTIFACT_DIR.resolve(),
            settings.SAMPLE_DATA_DIR.resolve(),
        ]

        is_safe = False
        for root in allowed_roots:
            try:
                resolved.relative_to(root)
                is_safe = True
                break
            except ValueError:
                continue

        if not is_safe:
            raise SecurityError(
                f"Access denied: Path '{resolved}' escapes the designated workspace sandbox."
            )

        if allow_create_parent and not resolved.parent.exists():
            resolved.parent.mkdir(parents=True, exist_ok=True)

        return resolved

    @staticmethod
    def check_file_size(size_bytes: int):
        """Validates file size limit."""
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise SecurityError(
                f"File size exceeds maximum permitted limit of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )
