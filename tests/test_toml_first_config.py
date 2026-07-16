"""Issue #36: every BCP config consumer must resolve toml-first.

The ``bcp_*`` config readers are markdown workflows/agents (the LLM drives the
resolution) plus the Python engine. These are structural assertions:

- each markdown consumer invokes the ``bcp_config.py`` helper and documents the
  per-key yaml fallback and the module-default-last precedence;
- the helper itself reuses the core ``resolve_config.py`` for ``modules.bcp``;
- the setup write-path targets ``custom/config.toml`` and strips the legacy
  yaml module section.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]

# Markdown consumers that read bcp_* config at runtime.
CONSUMERS = [
    "skills/bmad-bcp-score/workflow.md",
    "skills/bmad-bcp-rescore/workflow.md",
    "skills/bmad-bcp-agent-bruno/SKILL.md",
]

HELPER = "skills/bmad-bcp-score/scripts/bcp_config.py"
MERGE = "skills/bmad-bcp-setup/scripts/merge-config.py"


@pytest.mark.parametrize("rel", CONSUMERS)
def test_consumer_invokes_bcp_config_helper(rel: str):
    text = (REPO / rel).read_text(encoding="utf-8")
    assert "bcp_config.py" in text, f"{rel} must resolve config via bcp_config.py"


@pytest.mark.parametrize("rel", CONSUMERS)
def test_consumer_documents_toml_first_fallback_and_default(rel: str):
    text = (REPO / rel).read_text(encoding="utf-8").lower()
    assert "toml" in text, f"{rel} must frame resolution as toml-first"
    assert "fallback" in text, f"{rel} must document the per-key yaml fallback"
    assert "config.yaml" in text, f"{rel} must name config.yaml as the fallback layer"
    assert "default" in text, f"{rel} must document the module.yaml default as last resort"


@pytest.mark.parametrize("rel", CONSUMERS)
def test_consumer_yaml_bcp_section_not_authoritative(rel: str):
    """The old prose loaded the `bcp` section from config.yaml as the source of
    truth. That phrasing must be gone — toml is authoritative now."""
    text = (REPO / rel).read_text(encoding="utf-8")
    assert "leia a seção `bcp` de `{project-root}/_bmad/config.yaml`" not in text
    assert "Carregue config de `{project-root}/_bmad/config.yaml`, seção `bcp`" not in text


def test_helper_reuses_core_resolver_for_modules_bcp():
    helper = (REPO / HELPER).read_text(encoding="utf-8")
    assert "resolve_config.py" in helper, "helper must reuse the core resolver"
    assert "modules.bcp" in helper, "helper must resolve the modules.bcp table"


def test_merge_config_writes_custom_toml_not_yaml_module_section():
    """The setup write-path must target custom/config.toml for the module
    section and must not re-introduce a config.yaml module write."""
    script = (REPO / MERGE).read_text(encoding="utf-8")
    assert "custom" in script and "config.toml" in script
    assert "write_module_toml" in script
    # anti-zombie strip of the legacy yaml module section
    assert "del config[module_code]" in script
