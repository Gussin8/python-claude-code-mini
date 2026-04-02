"""
Memory directory (memdir) core functionality.

Builds memory prompts and manages memory directory structure.
"""

import os
from dataclasses import dataclass
from typing import List, Optional

from .memory_types import (
    MEMORY_FRONTMATTER_EXAMPLE,
    TYPES_SECTION_INDIVIDUAL,
    WHAT_NOT_TO_SAVE_SECTION,
    WHEN_TO_ACCESS_SECTION,
    TRUSTING_RECALL_SECTION,
)


ENTRYPOINT_NAME = 'MEMORY.md'
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000


@dataclass
class EntrypointTruncation:
    """Result of truncating MEMORY.md content."""
    
    content: str
    """Truncated content with warning if applicable."""
    
    line_count: int
    """Original line count."""
    
    byte_count: int
    """Original byte count."""
    
    was_line_truncated: bool
    """True if line cap was hit."""
    
    was_byte_truncated: bool
    """True if byte cap was hit."""


def truncate_entrypoint_content(raw: str) -> EntrypointTruncation:
    """
    Truncate MEMORY.md content to the line AND byte caps, appending a warning
    that names which cap fired. Line-truncates first (natural boundary), then
    byte-truncates at the last newline before the cap so we don't cut mid-line.
    """
    trimmed = raw.strip()
    content_lines = trimmed.split('\n')
    line_count = len(content_lines)
    byte_count = len(trimmed)
    
    was_line_truncated = line_count > MAX_ENTRYPOINT_LINES
    # Check original byte count — long lines are the failure mode the byte cap
    # targets, so post-line-truncation size would understate the warning.
    was_byte_truncated = byte_count > MAX_ENTRYPOINT_BYTES
    
    if not was_line_truncated and not was_byte_truncated:
        return EntrypointTruncation(
            content=trimmed,
            line_count=line_count,
            byte_count=byte_count,
            was_line_truncated=was_line_truncated,
            was_byte_truncated=was_byte_truncated,
        )
    
    # Truncate lines first
    truncated = '\n'.join(
        content_lines[:MAX_ENTRYPOINT_LINES] 
        if was_line_truncated 
        else content_lines
    )
    
    # Then truncate bytes at last newline
    if len(truncated) > MAX_ENTRYPOINT_BYTES:
        cut_at = truncated.rfind('\n', 0, MAX_ENTRYPOINT_BYTES)
        truncated = truncated[:cut_at] if cut_at > 0 else truncated[:MAX_ENTRYPOINT_BYTES]
    
    # Build warning message
    def format_file_size(bytes_val: int) -> str:
        """Format bytes as human-readable size."""
        if bytes_val < 1024:
            return f'{bytes_val}B'
        elif bytes_val < 1024 * 1024:
            return f'{bytes_val / 1024:.1f}KB'
        else:
            return f'{bytes_val / (1024 * 1024):.1f}MB'
    
    if was_byte_truncated and not was_line_truncated:
        reason = f"{format_file_size(byte_count)} (limit: {format_file_size(MAX_ENTRYPOINT_BYTES)}) — index entries are too long"
    elif was_line_truncated and not was_byte_truncated:
        reason = f"{line_count} lines (limit: {MAX_ENTRYPOINT_LINES})"
    else:
        reason = f"{line_count} lines and {format_file_size(byte_count)}"
    
    warning = (
        f"\n\n> WARNING: {ENTRYPOINT_NAME} is {reason}. "
        f"Only part of it was loaded. Keep index entries to one line under ~200 chars; "
        f"move detail into topic files."
    )
    
    return EntrypointTruncation(
        content=truncated + warning,
        line_count=line_count,
        byte_count=byte_count,
        was_line_truncated=was_line_truncated,
        was_byte_truncated=was_byte_truncated,
    )


# Guidance text for memory directory existence
DIR_EXISTS_GUIDANCE = (
    "This directory already exists — write to it directly with the Write tool "
    "(do not run mkdir or check for its existence)."
)


def build_memory_lines(
    display_name: str,
    memory_dir: str,
    extra_guidelines: Optional[List[str]] = None,
    skip_index: bool = False,
) -> List[str]:
    """
    Build the typed-memory behavioral instructions (without MEMORY.md content).
    
    Constrains memories to a closed four-type taxonomy (user / feedback / project /
    reference) — content that is derivable from the current project state (code
    patterns, architecture, git history) is explicitly excluded.
    
    Individual-only variant: no `## Memory scope` section, no <scope> tags
    in type blocks, and team/private qualifiers stripped from examples.
    """
    if skip_index:
        how_to_save = [
            '## How to save memories',
            '',
            'Write each memory to its own file (e.g., `user_role.md`, `feedback_testing.md`) using this frontmatter format:',
            '',
        ] + MEMORY_FRONTMATTER_EXAMPLE + [
            '',
            '- Keep the name, description, and type fields in memory files up-to-date with the content',
            '- Organize memory semantically by topic, not chronologically',
            '- Update or remove memories that turn out to be wrong or outdated',
            '- Do not write duplicate memories. First check if there is an existing memory you can update before writing a new one.',
        ]
    else:
        how_to_save = [
            '## How to save memories',
            '',
            'Saving a memory is a two-step process:',
            '',
            '**Step 1** — write the memory to its own file (e.g., `user_role.md`, `feedback_testing.md`) using this frontmatter format:',
            '',
        ] + MEMORY_FRONTMATTER_EXAMPLE + [
            '',
            f"**Step 2** — add a pointer to that file in `{ENTRYPOINT_NAME}`. `{ENTRYPOINT_NAME}` is an index, not a memory — each entry should be one line, under ~150 characters: `- [Title](file.md) — one-line hook`. It has no frontmatter. Never write memory content directly into `{ENTRYPOINT_NAME}`.",
            '',
            f"- `{ENTRYPOINT_NAME}` is always loaded into your conversation context — lines after {MAX_ENTRYPOINT_LINES} will be truncated, so keep the index concise",
            '- Keep the name, description, and type fields in memory files up-to-date with the content',
            '- Organize memory semantically by topic, not chronologically',
            '- Update or remove memories that turn out to be wrong or outdated',
            '- Do not write duplicate memories. First check if there is an existing memory you can update before writing a new one.',
        ]
    
    lines: List[str] = [
        f'# {display_name}',
        '',
        f"You have a persistent, file-based memory system at `{memory_dir}`. {DIR_EXISTS_GUIDANCE}",
        '',
        "You should build up this memory system over time so that future conversations can have a complete picture of who the user is, how they'd like to collaborate with you, what behaviors to avoid or repeat, and the context behind the work the user gives you.",
        '',
        "If the user explicitly asks you to remember something, save it immediately as whichever type fits best. If they ask you to forget something, find and remove the relevant entry.",
        '',
    ] + TYPES_SECTION_INDIVIDUAL + [
        '',
    ] + WHAT_NOT_TO_SAVE_SECTION + [
        '',
    ] + how_to_save + [
        '',
    ] + WHEN_TO_ACCESS_SECTION + [
        '',
    ] + TRUSTING_RECALL_SECTION + [
        '',
        '## Memory and other forms of persistence',
        'Memory is one of several persistence mechanisms available to you as you assist the user in a given conversation. The distinction is often that memory can be recalled in future conversations and should not be used for persisting information that is only useful within the scope of the current conversation.',
        '- When to use or update a plan instead of memory: If you are about to start a non-trivial implementation task and would like to reach alignment with the user on your approach you should use a Plan rather than saving this information to memory. Similarly, if you already have a plan within the conversation and you have changed your approach persist that change by updating the plan rather than saving a memory.',
        '- When to use or update tasks instead of memory: When you need to break your work in current conversation into discrete steps or keep track of your progress use tasks instead of saving to memory. Tasks are great for persisting information about the work that needs to be done in the current conversation, but memory should be reserved for information that will be useful in future conversations.',
        '',
    ] + (extra_guidelines or []) + [
        '',
    ]
    
    lines.extend(build_searching_past_context_section(memory_dir))
    
    return lines


def build_searching_past_context_section(memory_dir: str) -> List[str]:
    """
    Build the "Searching past context" section if enabled.
    
    For now, returns empty list (feature gated off by default).
    """
    # TODO: Implement feature gate when config system supports it
    return []


async def load_memory_prompt(
    memory_dir: str,
    display_name: str = 'auto memory',
    extra_guidelines: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Load the memory prompt for inclusion in the system prompt.
    
    Reads MEMORY.md entrypoint and includes its content in the prompt.
    Returns None if auto memory is disabled.
    """
    # Ensure directory exists (idempotent)
    await ensure_memory_dir_exists(memory_dir)
    
    # Read existing memory entrypoint
    entrypoint_path = os.path.join(memory_dir, ENTRYPOINT_NAME)
    entrypoint_content = ''
    try:
        with open(entrypoint_path, 'r', encoding='utf-8') as f:
            entrypoint_content = f.read()
    except FileNotFoundError:
        pass
    
    # Build base memory lines
    lines = build_memory_lines(display_name, memory_dir, extra_guidelines)
    
    # Add entrypoint content if exists
    if entrypoint_content.strip():
        t = truncate_entrypoint_content(entrypoint_content)
        lines.append(f'## {ENTRYPOINT_NAME}')
        lines.append('')
        lines.append(t.content)
    else:
        lines.append(f'## {ENTRYPOINT_NAME}')
        lines.append('')
        lines.append(f'Your {ENTRYPOINT_NAME} is currently empty. When you save new memories, they will appear here.')
    
    return '\n'.join(lines)


async def ensure_memory_dir_exists(memory_dir: str) -> None:
    """
    Ensure a memory directory exists. Idempotent.
    
    Directory creation is recursive by default and swallows EEXIST,
    so the full parent chain is created in one call.
    """
    try:
        os.makedirs(memory_dir, exist_ok=True)
    except OSError as e:
        # Log but don't fail - the model's Write will surface the real perm error
        print(f"[memdir] ensure_memory_dir_exists failed for {memory_dir}: {e}")
