"""Memory directory (memdir) module for persistent file-based memory."""

from .memory_types import (
    MEMORY_TYPES,
    MemoryType,
    parse_memory_type,
    TYPES_SECTION_INDIVIDUAL,
    WHAT_NOT_TO_SAVE_SECTION,
    WHEN_TO_ACCESS_SECTION,
    TRUSTING_RECALL_SECTION,
    MEMORY_FRONTMATTER_EXAMPLE,
    MEMORY_DRIFT_CAVEAT,
)
from .memory_scan import (
    MemoryHeader,
    scan_memory_files,
    format_memory_manifest,
)
from .memory_age import (
    memory_age_days,
    memory_age,
    memory_freshness_text,
    memory_freshness_note,
)
from .find_relevant_memories import (
    RelevantMemory,
    find_relevant_memories,
    select_relevant_memories,
)
from .memdir import (
    ENTRYPOINT_NAME,
    MAX_ENTRYPOINT_LINES,
    MAX_ENTRYPOINT_BYTES,
    truncate_entrypoint_content,
    EntrypointTruncation,
    ensure_memory_dir_exists,
    build_memory_lines,
    load_memory_prompt,
)

__all__ = [
    # Memory types
    "MEMORY_TYPES",
    "MemoryType",
    "parse_memory_type",
    "TYPES_SECTION_INDIVIDUAL",
    "WHAT_NOT_TO_SAVE_SECTION",
    "WHEN_TO_ACCESS_SECTION",
    "TRUSTING_RECALL_SECTION",
    "MEMORY_FRONTMATTER_EXAMPLE",
    "MEMORY_DRIFT_CAVEAT",
    # Memory scan
    "MemoryHeader",
    "scan_memory_files",
    "format_memory_manifest",
    # Memory age
    "memory_age_days",
    "memory_age",
    "memory_freshness_text",
    "memory_freshness_note",
    # Find relevant memories
    "RelevantMemory",
    "find_relevant_memories",
    "select_relevant_memories",
    # Memdir
    "ENTRYPOINT_NAME",
    "MAX_ENTRYPOINT_LINES",
    "MAX_ENTRYPOINT_BYTES",
    "truncate_entrypoint_content",
    "EntrypointTruncation",
    "ensure_memory_dir_exists",
    "build_memory_lines",
    "load_memory_prompt",
]
