"""Filesystem boundaries for personal research; no private export to Pages."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def outside_repo(path: Path | str) -> Path:
    path = Path(path).expanduser().resolve()
    # Also reject linked worktrees and other repositories, including their parents.
    if path == ROOT or ROOT in path.parents:
        raise ValueError('Private storage must be outside the Git working tree')
    if any((parent / '.git').is_file() or (parent / '.git/HEAD').is_file()
           for parent in (path, *path.parents)):
        raise ValueError('Private storage cannot be inside a Git working tree')
    if path in ROOT.parents:
        raise ValueError('Choose a dedicated private folder, not an ancestor of the repository')
    return path


def private_dir(path: Path | str) -> Path:
    path = outside_repo(path)
    if path == Path('/tmp') or path == Path.home():
        raise ValueError('Choose a dedicated private subfolder, not a shared/root home directory')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def private_write(path: Path, data: bytes):
    path = outside_repo(path)
    private_dir(path.parent)
    # Never follow an existing output symlink; replace atomically with mode 0600.
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def private_json(path: Path, value):
    private_write(path, (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode())


def data_dir(value=None) -> Path:
    return outside_repo(value or os.environ.get('PAGEFINDER_PRIVATE_DIR') or
                        Path.home() / '.local/share/github-pages-discovery')


def config_dir(value=None) -> Path:
    return outside_repo(value or Path.home() / '.config/github-pages-discovery/youtube')
