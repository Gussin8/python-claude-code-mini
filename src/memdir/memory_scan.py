"""
Memory-directory scanning primitives.

Scans memory directory for .md files, reads frontmatter, and returns
headers sorted newest-first (capped at MAX_MEMORY_FILES).
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .memory_types import MemoryType, parse_memory_type


@dataclass
class MemoryHeader:
    """Header information for a memory file."""
    
    filename: str
    """Relative path within the memory directory."""
    
    file_path: str
    """Absolute file path."""
    
    mtime_ms: float
    """Modification time in milliseconds since epoch."""
    
    description: Optional[str]
    """Description from frontmatter."""
    
    type: Optional[MemoryType]
    """Parsed memory type."""


MAX_MEMORY_FILES = 200
FRONTMATTER_MAX_LINES = 30


async def scan_memory_files(
    memory_dir: str,
) -> List[MemoryHeader]:
    """
    Scan a memory directory for .md files, read their frontmatter, 
    and return headers sorted newest-first (capped at MAX_MEMORY_FILES).
    
    Single-pass: reads content and gets mtime together, then sorts.
    For large N this reads extra small files but avoids double-stat on surviving 200.
    """
    try:
        # Get all entries recursively
        entries = []
        for root, dirs, files in os.walk(memory_dir):
            for f in files:
                if f.endswith('.md') and f != 'MEMORY.md':
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, memory_dir)
                    entries.append((rel_path, full_path))
        
        # Read frontmatter and mtime for each file
        header_results = []
        for rel_path, full_path in entries:
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= FRONTMATTER_MAX_LINES:
                            break
                        lines.append(line)
                    content = ''.join(lines)
                
                # Get mtime
                mtime_ms = os.path.getmtime(full_path) * 1000
                
                # Parse frontmatter
                description, mem_type = _parse_frontmatter(content, full_path)
                
                header_results.append(MemoryHeader(
                    filename=rel_path,
                    file_path=full_path,
                    mtime_ms=mtime_ms,
                    description=description,
                    type=mem_type,
                ))
            except Exception:
                # Skip files that can't be read
                continue
        
        # Sort by mtime descending (newest first) and cap
        header_results.sort(key=lambda h: h.mtime_ms, reverse=True)
        return header_results[:MAX_MEMORY_FILES]
    
    except Exception:
        return []


def _parse_frontmatter(content: str, file_path: str) -> tuple[Optional[str], Optional[MemoryType]]:
    """
    Parse YAML frontmatter from content.
    
    Returns (description, memory_type) tuple.
    Both are None if not found or invalid.
    """
    if not content.startswith('---'):
        return None, None
    
    # Find end of frontmatter
    end_idx = content.find('---', 3)
    if end_idx == -1:
        return None, None
    
    frontmatter_text = content[4:end_idx].strip()
    
    description = None
    mem_type_raw = None
    
    for line in frontmatter_text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip().strip('"\'')
            
            if key == 'description':
                description = value if value else None
            elif key == 'type':
                mem_type_raw = value if value else None
    
    return description, parse_memory_type(mem_type_raw)


def format_memory_manifest(memories: List[MemoryHeader]) -> str:
    """
    Format memory headers as a text manifest: one line per file with
    [type] filename (timestamp): description.
    
    Used by memory selector prompt.
    """
    lines = []
    for m in memories:
        tag = f"[{m.type}] " if m.type else ""
        ts = _format_timestamp(m.mtime_ms)
        if m.description:
            lines.append(f"- {tag}{m.filename} ({ts}): {m.description}")
        else:
            lines.append(f"- {tag}{m.filename} ({ts})")
    return '\n'.join(lines)


def _format_timestamp(mtime_ms: float) -> str:
    """Format mtime_ms as ISO timestamp string."""
    from datetime import datetime
    dt = datetime.fromtimestamp(mtime_ms / 1000)
    return dt.isoformat()
