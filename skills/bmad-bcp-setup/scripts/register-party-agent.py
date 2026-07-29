#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit"]
# ///
"""Registra o agente do módulo (Bruno/BCP) na tabela [agents] de _bmad/custom/config.toml.

O Party Mode (bmad-party-mode) monta o roster lendo a tabela [agents] via
resolve_config.py, que faz deep-merge de _bmad/config.toml (base) com
_bmad/custom/config.toml (team). Os módulos OFICIAIS têm suas entradas [agents.*]
escritas no config.toml base pelo installer do BMAD core; um módulo CUSTOM (como
o BCP) não é escrito ali, então seu agente nunca aparece no Party Mode. Este
script grava a entrada na camada custom (team, committed), que sobrevive a
re-install. Idempotente: preserva comentários e demais seções (tomlkit
round-trip).

O `custom/config.toml` é um arquivo human-authored — o time comenta e edita as
entradas ali. Por isso um re-run NÃO reescreve o bloco inteiro: a entrada é
atualizada in-place (mantendo sua posição e os comentários que a precedem) e só
os campos estruturais (STRUCTURAL_FIELDS) são regravados. Campos editoriais já
presentes (name/title/icon/description) são preservados — use `--force` para
restaurá-los a partir do fragment.

Deriva tudo do agent-manifest-fragment.csv (primeira linha de dados): a chave da
tabela vem do diretório do SKILL apontado em `path`; nome/título/ícone/descrição
das colunas do fragment.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import tomlkit
except ModuleNotFoundError:
    print("Error: tomlkit is required (PEP 723 dependency). Run via `uv run`.", file=sys.stderr)
    sys.exit(2)

DEFAULT_TEAM = "software-development"

# Campos que o fragment é dono: identificam o registro e podem ser regravados a
# cada run sem perda. Os demais (name/title/icon/description) são editoriais —
# o time os ajusta direto no config.toml, e um re-run não deve achatá-los.
STRUCTURAL_FIELDS = ("module", "team")


def load_fragment(fragment_path: Path) -> dict | None:
    with fragment_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else None


def agent_key(row: dict) -> str:
    # deriva a chave da tabela do path do SKILL: .claude/skills/<dir>/SKILL.md
    path = (row.get("path") or "").strip()
    if path:
        return Path(path).parent.name
    # fallback: bmad-<module>-agent-<name>
    mod = (row.get("module") or "module").strip()
    nm = (row.get("displayName") or row.get("name") or "agent").strip().lower()
    return f"bmad-{mod}-agent-{nm}"


def build_entry(row: dict) -> dict:
    return {
        "module": (row.get("module") or "").strip(),
        "team": DEFAULT_TEAM,
        "name": (row.get("displayName") or row.get("name") or "").strip(),
        "title": (row.get("title") or "").strip(),
        "icon": (row.get("icon") or "").strip(),
        "description": (row.get("identity") or row.get("role") or "").strip(),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Register the module agent in _bmad/custom/config.toml [agents].")
    ap.add_argument("--project-root", required=True, help="Consumer project root")
    ap.add_argument("--fragment", required=True, help="Path to agent-manifest-fragment.csv")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Também sobrescreve os campos editoriais (name/title/icon/description) "
             "com os valores do fragment. Sem a flag, campos já presentes são preservados.",
    )
    args = ap.parse_args()

    root = Path(args.project_root)
    fragment = Path(args.fragment)
    custom = root / "_bmad" / "custom" / "config.toml"

    if not fragment.exists():
        print(json.dumps({"status": "error", "reason": f"fragment not found: {fragment}"}))
        sys.exit(1)

    row = load_fragment(fragment)
    if row is None:
        print(json.dumps({"status": "error", "reason": "empty fragment"}))
        sys.exit(1)

    key = agent_key(row)
    entry = build_entry(row)

    if custom.exists():
        doc = tomlkit.parse(custom.read_text(encoding="utf-8"))
    else:
        custom.parent.mkdir(parents=True, exist_ok=True)
        doc = tomlkit.document()

    agents = doc.get("agents")
    if agents is None:
        agents = tomlkit.table(is_super_table=True)
        doc["agents"] = agents

    existing = agents.get(key)
    if existing is None:
        tbl = tomlkit.table()
        for k, v in entry.items():
            tbl[k] = v
        agents[key] = tbl
        action = "created"
        written = dict(entry)
    else:
        # Atualiza in-place. Recriar a entrada (del + reatribuição) a moveria
        # para o fim de [agents], desgarrando os comentários que a precedem no
        # arquivo do time.
        for k, v in entry.items():
            if args.force or k in STRUCTURAL_FIELDS or k not in existing:
                existing[k] = v
        action = "forced" if args.force else "updated"
        written = {k: existing[k] for k in entry}

    custom.write_text(tomlkit.dumps(doc), encoding="utf-8")
    print(json.dumps(
        {
            "status": "success",
            "action": action,
            "agent_key": key,
            "custom_config_path": str(custom),
            "entry": written,
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
