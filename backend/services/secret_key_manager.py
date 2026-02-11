"""Secret key manager for Nebulus Gantry.

Generates, persists, loads, and rotates cryptographically secure secret
keys used for session signing.  Keys are stored on disk with restrictive
file permissions and are never logged or exposed via API responses.

Typical usage::

    from pathlib import Path
    from backend.services.secret_key_manager import get_secret_key, rotate_secret_key

    data_dir = Path("data")
    key = get_secret_key(data_dir)       # load or create
    new_key = rotate_secret_key(data_dir) # force rotation
"""

from __future__ import annotations

import os
import secrets
import stat
import tempfile
from pathlib import Path

_KEY_FILENAME = ".secret_key"
_KEY_BYTES = 32  # 32 bytes → 64-char hex string


def _key_path(data_dir: Path) -> Path:
    """Return the resolved path to the secret key file.

    Args:
        data_dir: Directory where application data is stored.

    Returns:
        Full path to the ``.secret_key`` file.
    """
    return data_dir / _KEY_FILENAME


def _generate_key() -> str:
    """Generate a cryptographically secure secret key.

    Returns:
        A 64-character hex-encoded string (32 random bytes).
    """
    return secrets.token_hex(_KEY_BYTES)


def _write_key(key_file: Path, key: str) -> None:
    """Atomically write *key* to *key_file* with 0600 permissions.

    Uses a temporary file + rename to avoid leaving a partial key on
    disk if the process is interrupted.

    Args:
        key_file: Destination path for the key.
        key: The hex-encoded secret key string.
    """
    key_file.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temp file in the same directory, then atomic rename.
    fd, tmp_path = tempfile.mkstemp(
        dir=str(key_file.parent), prefix=".secret_key_tmp_"
    )
    try:
        os.write(fd, key.encode("utf-8"))
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        os.close(fd)
        os.replace(tmp_path, str(key_file))
    except BaseException:
        os.close(fd) if not _fd_closed(fd) else None  # noqa: E501
        # Best-effort cleanup of the temp file.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _fd_closed(fd: int) -> bool:
    """Check whether a file descriptor is already closed.

    Args:
        fd: File descriptor integer.

    Returns:
        ``True`` if *fd* is closed, ``False`` otherwise.
    """
    try:
        os.fstat(fd)
        return False
    except OSError:
        return True


def _read_key(key_file: Path) -> str | None:
    """Read an existing key from disk.

    Args:
        key_file: Path to the secret key file.

    Returns:
        The key string if the file exists and is non-empty, else ``None``.
    """
    if not key_file.exists():
        return None
    content = key_file.read_text(encoding="utf-8").strip()
    return content if content else None


def get_secret_key(data_dir: Path) -> str:
    """Return the current secret key, generating one if absent.

    On first call (or if the file was deleted) a new key is generated
    and persisted.  Subsequent calls return the persisted key.

    Args:
        data_dir: Directory where application data is stored.

    Returns:
        A 64-character hex-encoded secret key.
    """
    key_file = _key_path(data_dir)
    existing = _read_key(key_file)
    if existing is not None:
        return existing

    key = _generate_key()
    _write_key(key_file, key)
    return key


def rotate_secret_key(data_dir: Path) -> str:
    """Generate a new secret key and overwrite the persisted copy.

    **Warning:** Rotating the key invalidates all existing sessions
    signed with the previous key.

    Args:
        data_dir: Directory where application data is stored.

    Returns:
        The newly generated 64-character hex-encoded secret key.
    """
    key = _generate_key()
    _write_key(_key_path(data_dir), key)
    return key
