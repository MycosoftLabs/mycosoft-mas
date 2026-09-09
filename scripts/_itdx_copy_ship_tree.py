"""Copy ITDX ship files into the clean MAS worktree. No secrets."""
from pathlib import Path

src = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas")
dst = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas-itdx-ship")

files = [
    "mycosoft_mas/agents/itdx_task8_agent.py",
    "mycosoft_mas/core/routers/itdx_api.py",
    "mycosoft_mas/core/routers/itdx_public_sources.py",
    "tests/test_itdx_task8_api.py",
    "docs/ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md",
    "docs/ITDX_VM_BACKENDS_SEP09_2026.md",
    "docs/ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md",
    "docs/ITDX_V14_LAB_INTEGRATION_SEP09_2026.md",
    "docs/MAS_MYCA_AVANI_FUSARIUM_ITDX_INTEGRATION_PLAN_SEP09_2026.md",
    "docs/CURSOR_ITDX26_CODEX_V13_CONNECT_SEP09_2026.md",
    "docs/CURSOR_ITDX26_INTEGRATION_SEP08_2026.md",
]

for rel in files:
    source = src / rel
    dest = dst / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(source.read_bytes())
    print("copied", rel)

main = dst / "mycosoft_mas/core/myca_main.py"
text = main.read_text(encoding="utf-8")
if "itdx_api" in text:
    print("myca_main already has itdx")
else:
    marker = "except ImportError:\n    pass\n"
    raas = text.find("# RaaS")
    if raas < 0:
        raise SystemExit("RaaS marker missing")
    before = text.rfind(marker, 0, raas)
    if before < 0:
        raise SystemExit("import pass before RaaS missing")
    end = before + len(marker)
    patch = (
        "except ImportError:\n"
        "    pass\n"
        "\n"
        "# ITDX Task 8 + Earth Sim situation assessment (September 9, 2026)\n"
        "try:\n"
        "    from mycosoft_mas.core.routers.itdx_api import (\n"
        "        avani_task8_router,\n"
        "        myca_task8_router,\n"
        "        router as itdx_router,\n"
        "    )\n"
        "\n"
        '    app.include_router(itdx_router, tags=["itdx"])\n'
        '    app.include_router(avani_task8_router, tags=["itdx"])\n'
        '    app.include_router(myca_task8_router, tags=["itdx"])\n'
        "except ImportError:\n"
        "    pass\n"
        "\n"
    )
    main.write_text(text[:before] + patch + text[end:], encoding="utf-8")
    print("patched myca_main")

idxp = dst / ".cursor/CURSOR_DOCS_INDEX.md"
index_text = idxp.read_text(encoding="utf-8")
if "ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md" not in index_text:
    pos = index_text.find("\n## ")
    block = (
        "\n## ITDX26 connect (Sep 09, 2026)\n"
        "- `docs/ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md` — Live ship: local proofs, 188/189 hot data, Weka PASS + trial NOT_MET, blue-green 187\n"
        "- `docs/ITDX_VM_BACKENDS_SEP09_2026.md` — 188/189 source of truth; NLM model_loaded=true BOUND; no stub 0.85 p\n"
        "- `docs/ITDX_V14_LAB_INTEGRATION_SEP09_2026.md` — v1.4 Weka replay PASS; trial criteria NOT_MET\n"
        "- `docs/ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md` — Public OSINT; traffic REQUEST_DENIED\n"
        "- `docs/MAS_MYCA_AVANI_FUSARIUM_ITDX_INTEGRATION_PLAN_SEP09_2026.md` — Situation contract; no fake green\n"
        "- `docs/CURSOR_ITDX26_CODEX_V13_CONNECT_SEP09_2026.md` — Codex v1.3 Fusarium ITDX app\n"
        "- `docs/CURSOR_ITDX26_INTEGRATION_SEP08_2026.md` — v1.2/v1.3 handoff; FOUO STOP_INGEST\n"
    )
    idxp.write_text(index_text[:pos] + "\n" + block + index_text[pos:], encoding="utf-8")
    print("updated CURSOR_DOCS_INDEX")
else:
    print("CURSOR_DOCS_INDEX already has ship doc")

master = dst / "docs/MASTER_DOCUMENT_INDEX.md"
master_text = master.read_text(encoding="utf-8")
if "ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md" not in master_text:
    insert = (
        "# Master Document Index\n"
        "\n"
        "## ITDX26 Fusarium live ship (SEP09 2026)\n"
        "- [ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md](ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md) — Local proofs + 188/189 hot data/math; Weka PASS / trial NOT_MET; add data without website rebuild; blue-green 187\n"
        "\n"
        "## ITDX26 VM backends (SEP09 2026)\n"
        "- [ITDX_VM_BACKENDS_SEP09_2026.md](ITDX_VM_BACKENDS_SEP09_2026.md) — 188/189 live prove; NLM BOUND; skip-startup on\n"
        "\n"
    )
    if master_text.startswith("# Master Document Index"):
        master_text = insert + master_text[len("# Master Document Index") :].lstrip("\n")
    else:
        master_text = insert + master_text
    master.write_text(master_text, encoding="utf-8")
    print("updated MASTER_DOCUMENT_INDEX")
else:
    print("MASTER already has ship doc")
