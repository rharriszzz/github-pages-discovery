"""Fail closed before generating or deploying the deliberately public catalog."""
from __future__ import annotations

import json
from pathlib import Path
import re

from .core import ROOT, safe_site

SITE_FIELDS = frozenset(('url', 'owner', 'account_type', 'account_type_source', 'repository',
                         'repo_url', 'repo_description', 'topics', 'language', 'stars', 'updated_at',
                         'source', 'site_status', 'title', 'summary', 'body', 'review'))
PUBLIC_DOCS = frozenset(('index.html', 'architecture.md', 'implementation_status.md', 'youtube_setup.md'))
SECRET_PATTERNS = (
    re.compile(r'\b(?:ya29\.|1//|ghp_|github_pat_)[A-Za-z0-9_.-]{12,}'),
    re.compile(r'AIza[A-Za-z0-9_-]{30,}'),
    re.compile(r'(?i)["\x27](?:access_token|refresh_token|client_secret)["\x27]\s*:\s*["\x27][^"\x27]+'),
    re.compile(r'(?i)authorization\s*:\s*bearer\s+\S+'),
    re.compile(r'(?i)["\x27]visibility["\x27]\s*:\s*["\x27]private["\x27]'),
    re.compile(r'(?i)["\x27](?:titleUrl|observed_at|playlist_annotations|playlist_membership)["\x27]\s*:'),
    re.compile(r'(?:/home/[^/\s]+/|/mnt/[a-z]/Users/[^/\s]+/)'),
)


def check_text(text):
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        raise ValueError('Publication blocked: possible credential/private record or personal path')


def validate_public_inputs(root=ROOT):
    root = Path(root)
    for path in (root / 'data/sites.json', root / 'data/interests.json'):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Publication blocked: input symlink outside reviewed public data')
        check_text(path.read_text(encoding='utf-8'))
    rows = json.loads((root / 'data/sites.json').read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('Publication blocked: expected public site array')
    for row in rows:
        if not isinstance(row, dict) or set(row) - SITE_FIELDS or not safe_site(row.get('url', '')):
            raise ValueError('Publication blocked: fields/source outside reviewed public site contract')
        if row.get('account_type') not in ('User', 'Organization', 'Unknown'):
            raise ValueError('Publication blocked: invalid public account type')
    profile = json.loads((root / 'data/interests.json').read_text(encoding='utf-8'))
    if set(profile) - {'profile_name', 'notes', 'interests'}:
        raise ValueError('Publication blocked: unreviewed profile fields')
    for concept in profile.get('interests', []):
        if set(concept) - {'name', 'terms', 'weight'}:
            raise ValueError('Publication blocked: private graph fields in public profile')


def check_publication(root=ROOT):
    root = Path(root)
    validate_public_inputs(root)
    for folder in ('docs', 'reports'):
        if (root / folder).is_symlink():
            raise ValueError('Publication blocked: symlinked public artifact directory')
        for path in (root / folder).rglob('*'):
            if path.is_symlink():
                raise ValueError('Publication blocked: symlink in public artifacts')
            if path.is_dir():
                continue
            if folder == 'docs' and path.relative_to(root / folder).as_posix() not in PUBLIC_DOCS:
                raise ValueError('Publication blocked: unreviewed artifact in docs')
            if path.suffix not in ('.html', '.json', '.csv', '.md'):
                raise ValueError('Publication blocked: unexpected public file type')
            check_text(path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    check_publication()
    print('Public input and artifact guards passed.')
