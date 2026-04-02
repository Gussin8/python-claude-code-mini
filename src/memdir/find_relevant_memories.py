"""
Find relevant memories in memory directory.

Uses side query (LLM) to select memories relevant to a user query.
"""

import asyncio
from dataclasses import dataclass
from typing import List, Optional, Set

from .memory_scan import MemoryHeader, scan_memory_files, format_memory_manifest


@dataclass
class RelevantMemory:
    """A memory file that is relevant to a query."""
    
    path: str
    """Absolute file path."""
    
    mtime_ms: float
    """Modification time for freshness tracking."""


SELECT_MEMORIES_SYSTEM_PROMPT = """You are selecting memories that will be useful to Claude Code as it processes a user's query. You will be given the user's query and a list of available memory files with their filenames and descriptions.

Return a list of filenames for the memories that will clearly be useful to Claude Code as it processes the user's query (up to 5). Only include memories that you are certain will be helpful based on their name and description.
- If you are unsure if a memory will be useful in processing the user's query, then do not include it in your list. Be selective and discerning.
- If there are no memories in the list that would clearly be useful, feel free to return an empty list.
- If a list of recently-used tools is provided, do not select memories that are usage reference or API documentation for those tools (Claude Code is already exercising them). DO still select memories containing warnings, gotchas, or known issues about those tools — active use is exactly when those matter.
"""


async def find_relevant_memories(
    query: str,
    memory_dir: str,
    recent_tools: Optional[List[str]] = None,
    already_surfaced: Optional[Set[str]] = None,
) -> List[RelevantMemory]:
    """
    Find memory files relevant to a query by scanning memory file headers
    and asking LLM to select the most relevant ones.
    
    Returns absolute file paths + mtime of the most relevant memories
    (up to 5). Excludes MEMORY.md (already loaded in system prompt).
    mtime is threaded through so callers can surface freshness to the
    main model without a second stat.
    
    `already_surfaced` filters paths shown in prior turns before the
    selection, so the selector spends its 5-slot budget on fresh
    candidates instead of re-picking files the caller will discard.
    """
    # Scan memory files
    memories = await scan_memory_files(memory_dir)
    
    # Filter out already surfaced memories
    if already_surfaced:
        memories = [m for m in memories if m.file_path not in already_surfaced]
    
    if not memories:
        return []
    
    # Select relevant memories using LLM
    selected_filenames = await select_relevant_memories(
        query,
        memories,
        recent_tools or [],
    )
    
    # Build lookup map
    by_filename = {m.filename: m for m in memories}
    
    # Filter to valid selections
    selected = [
        by_filename[filename] 
        for filename in selected_filenames 
        if filename in by_filename
    ]
    
    # Convert to RelevantMemory
    return [
        RelevantMemory(path=m.file_path, mtime_ms=m.mtime_ms)
        for m in selected
    ]


async def select_relevant_memories(
    query: str,
    memories: List[MemoryHeader],
    recent_tools: List[str],
) -> List[str]:
    """
    Use LLM to select relevant memories from a manifest.
    
    Returns list of filenames (not full paths).
    """
    valid_filenames = {m.filename for m in memories}
    manifest = format_memory_manifest(memories)
    
    # Add recently used tools section if provided
    tools_section = ""
    if recent_tools:
        tools_section = f"\n\nRecently used tools: {', '.join(recent_tools)}"
    
    try:
        # Import here to avoid circular dependency
        from ..services.api import APIService
        
        # Create API service instance
        api_service = APIService()
        
        # Build messages
        messages = [{
            'role': 'user',
            'content': f'Query: {query}\n\nAvailable memories:\n{manifest}{tools_section}'
        }]
        
        # Make side query
        result = await api_service.side_query(
            system=SELECT_MEMORIES_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=256,
            output_format={
                'type': 'json_schema',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'selected_memories': {
                            'type': 'array',
                            'items': {'type': 'string'}
                        }
                    },
                    'required': ['selected_memories'],
                    'additionalProperties': False
                }
            }
        )
        
        # Parse response
        if not result or 'content' not in result:
            return []
        
        content_blocks = result.get('content', [])
        text_block = next((b for b in content_blocks if b.get('type') == 'text'), None)
        
        if not text_block or 'text' not in text_block:
            return []
        
        import json
        parsed = json.loads(text_block['text'])
        selected = parsed.get('selected_memories', [])
        
        # Filter to valid filenames
        return [f for f in selected if f in valid_filenames]
    
    except Exception as e:
        # Log error but don't fail
        print(f"[memdir] select_relevant_memories failed: {e}")
        return []
