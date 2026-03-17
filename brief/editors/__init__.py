"""LunaClaw Brief — Editor Factory (Registry-driven)

All editors are discovered via @register_editor decorator.
The factory resolves preset.editor_type → Editor class at runtime.
"""

# Import all editor modules to trigger @register_editor decorators
import brief.editors.weekly   # noqa: F401
import brief.editors.daily    # noqa: F401
import brief.editors.finance  # noqa: F401
import brief.editors.stock    # noqa: F401
import brief.editors.generic  # noqa: F401

from brief.models import PresetConfig
from brief.editors.base import BaseEditor
from brief.llm import LLMClient
from brief.registry import EditorRegistry


def create_editor(preset: PresetConfig, global_config: dict) -> BaseEditor:
    """Create the appropriate editor based on preset.editor_type via Registry."""
    llm = LLMClient(global_config.get("llm", {}))
    editor_type = preset.editor_type

    if EditorRegistry.has(editor_type):
        cls = EditorRegistry.get(editor_type)
        return cls(preset, llm)

    raise ValueError(
        f"Editor '{editor_type}' not registered. "
        f"Available: {list(EditorRegistry.list_all().keys())}"
    )
