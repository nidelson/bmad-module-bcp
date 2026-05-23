"""Real installer end-to-end — the one thing the deterministic harness
cannot fake: `npx bmad-method install --custom-source <repo>`.

This actually downloads the BMAD CLI and runs a non-interactive install of
this module into a throwaway project, then asserts the installed surface.
It is the executable form of the v0.1.0 module validation (VM).

Gated behind BCP_E2E_INSTALL=1 because it needs network + npx and takes
~1–2 min — too heavy for every unit run. CI runs it in a dedicated job;
locally: `BCP_E2E_INSTALL=1 uv run --group test pytest -m integration -k install`.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.conftest import REPO_ROOT

pytestmark = pytest.mark.integration

REQUIRED = os.environ.get("BCP_E2E_INSTALL") == "1"
skip_reason = "set BCP_E2E_INSTALL=1 to run the real npx installer e2e"

EXPECTED_SKILLS = {
    "bmad-bcp-setup", "bmad-bcp-rule-card", "bmad-bcp-score",
    "bmad-bcp-score-batch", "bmad-bcp-rescore", "bmad-bcp-recalibrate",
    "bmad-bcp-backfill-baseline", "bmad-bcp-agent-bruno",
}

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_BOX_TRANS = str.maketrans("", "", "╭╮╯╰─│┌┐└┘├┤┬┴┼━┃║═╔╗╚╝")


def _flatten(s: str) -> str:
    """ANSI-strip, drop box-drawing chars, collapse whitespace.

    bmad-method renders the install summary inside a Rich panel; the
    target strings get split across visual rows with ANSI styling and
    border glyphs. Normalising to single-line whitespace lets the
    semantic substring checks stay panel-layout-agnostic.
    """
    s = _ANSI_RE.sub("", s).translate(_BOX_TRANS)
    return " ".join(s.split())


@pytest.mark.skipif(not REQUIRED, reason=skip_reason)
@pytest.mark.skipif(shutil.which("npx") is None, reason="npx not on PATH")
def test_real_npx_install_is_clean_and_complete(tmp_path: Path):
    proj = tmp_path / "consumer"
    proj.mkdir()
    subprocess.run(["git", "init", "-q", "."], cwd=proj, check=True)

    proc = subprocess.run(
        ["npx", "--yes", "bmad-method@latest", "install",
         "--directory", str(proj),
         "--custom-source", str(REPO_ROOT),
         "--modules", "bcp",
         "--tools", "claude-code",
         "--yes"],
        cwd=proj, capture_output=True, text=True, timeout=600,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = _flatten(proc.stdout)

    # 1. Module reported installed at the version pinned in module.yaml.
    #    Read it dynamically so release-please bumps don't require touching
    #    this test — the contract is "what module.yaml says is what installs".
    module_version = yaml.safe_load((REPO_ROOT / "module.yaml").read_text())["module_version"]
    assert f"BCP — Business Complexity Points Scorer (v{module_version}, installed)" in out

    # 2. No canonical-schema conformance warning. This regressed once
    #    (module-help.csv used after/before instead of
    #    preceded-by/followed-by) — VM caught it; pin it shut.
    assert "module-help.csv header does not match canonical schema" not in out
    assert "loaded positionally" not in out

    # 3. All eight skills materialised into the consumer.
    installed = {p.name for p in (proj / ".claude/skills").iterdir()
                 if p.name.startswith("bmad-bcp-")}
    assert installed == EXPECTED_SKILLS, (
        f"installed skills {sorted(installed)} != {sorted(EXPECTED_SKILLS)}"
    )

    # 4. Per-module config + help catalog generated.
    assert (proj / "_bmad/bcp/config.yaml").exists()
    assert (proj / "_bmad/bcp/module-help.csv").exists()

    # 5. The data folder the module declares was created.
    assert (proj / "_bmad-output/implementation-artifacts").is_dir()
