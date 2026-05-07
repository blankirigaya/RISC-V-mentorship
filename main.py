import json
import re
import os
from collections import defaultdict
from pathlib import Path


# ── Tier 1 ────────────────────────────────────────────────────────────────────

def load_instr_dict(path):
    with open(path) as f:
        return json.load(f)

def group_by_extension(data):
    ext_map = defaultdict(list)
    for mnemonic, info in data.items():
        for ext in info.get("extension", []):
            ext_map[ext].append(mnemonic.upper())
    return dict(sorted(ext_map.items()))

def find_multi_extension(data):
    result = []
    for mnemonic, info in data.items():
        exts = info.get("extension", [])
        if len(exts) > 1:
            result.append((mnemonic.upper(), sorted(exts)))
    return sorted(result)

def print_tier1(data):
    ext_map = group_by_extension(data)
    multi   = find_multi_extension(data)

    W = max(len(e) for e in ext_map) + 2
    print(f"\n{'Extension':<{W}} {'Count':>6}  Example")
    print("-" * (W + 22))
    for ext, mnemonics in ext_map.items():
        print(f"{ext:<{W}} {len(mnemonics):>6}  {sorted(mnemonics)[0]}")
    print("-" * (W + 22))
    print(f"{'Total extensions:':<{W}} {len(ext_map):>6}")
    print(f"{'Total instruction slots:':<{W}} {sum(len(v) for v in ext_map.values()):>6}")

    print(f"\nInstructions in multiple extensions: {len(multi)}")
    if multi:
        MW = max(len(m) for m, _ in multi) + 2
        print(f"\n{'Mnemonic':<{MW}} Extensions")
        print("-" * 72)
        for mnemonic, exts in multi:
            print(f"{mnemonic:<{MW}} {', '.join(exts)}")

    return ext_map


# ── Tier 2 ────────────────────────────────────────────────────────────────────

def normalise(name):
    name = name.lower().strip()
    name = re.sub(r'^rv(32|64)?_', '', name)
    return name

def extract_manual_extensions(manual_src_dir):
    found = set()
    anchor_pat  = re.compile(r'\[\[ext:([a-zA-Z0-9_]+)\]\]')
    heading_pat = re.compile(r'"([A-Z][a-zA-Z0-9_]+)"\s+[Ee]xtension')
    inline_pat  = re.compile(r'ext:([a-zA-Z0-9_]+)\[\]')
    for adoc in Path(manual_src_dir).rglob("*.adoc"):
        text = adoc.read_text(errors="replace")
        for pat in (anchor_pat, heading_pat, inline_pat):
            for m in pat.finditer(text):
                found.add(m.group(1).lower())
    return found

def print_tier2(ext_map, manual_src):
    if not os.path.isdir(manual_src):
        print(f"\n  ISA manual not found at '{manual_src}'.")
        print("  Clone it with: git clone --depth=1 https://github.com/riscv/riscv-isa-manual.git")
        return

    manual_exts = extract_manual_extensions(manual_src)
    json_norm   = {normalise(e): e for e in ext_map}
    manual_norm = {normalise(e): e for e in manual_exts}

    matched     = sorted(k for k in json_norm if k in manual_norm)
    json_only   = sorted(k for k in json_norm if k not in manual_norm)
    manual_only = sorted(k for k in manual_norm if k not in json_norm)

    print(f"\n  Matched  : {len(matched)}")
    print(f"  JSON only: {len(json_only)}")
    print(f"  ISA only : {len(manual_only)}")

    print(f"\n{'─'*60}")
    print(f"  {len(matched)} matched")
    print(f"{'─'*60}")
    for k in matched:
        print(f"  {k:<30} json={json_norm[k]}  manual={manual_norm[k]}")

    print(f"\n{'─'*60}")
    print(f"  {len(json_only)} in JSON only")
    print(f"{'─'*60}")
    for k in json_only:
        print(f"  {json_norm[k]}")

    print(f"\n{'─'*60}")
    print(f"  {len(manual_only)} in manual only")
    print(f"{'─'*60}")
    for k in manual_only:
        print(f"  {manual_norm[k]}")


# ── Tier 3 ────────────────────────────────────────────────────────────────────

def build_sharing_graph(data):
    pairs = defaultdict(int)
    for mnemonic, info in data.items():
        exts = sorted(info.get("extension", []))
        if len(exts) < 2:
            continue
        for i in range(len(exts)):
            for j in range(i + 1, len(exts)):
                pairs[(exts[i], exts[j])] += 1
    return pairs

def print_tier3(data):
    pairs = build_sharing_graph(data)
    edges = sorted(((a, b, w) for (a, b), w in pairs.items()), key=lambda x: -x[2])
    nodes = sorted({n for a, b, _ in edges for n in (a, b)})
    node_idx = {n: i for i, n in enumerate(nodes)}

    adj = defaultdict(list)
    for a, b, w in edges:
        adj[a].append((b, w))
        adj[b].append((a, w))

    W = max(len(n) for n in nodes) + 1
    print(f"\n  Nodes : {len(nodes)}  |  Edges : {len(edges)}\n")

    print(f"{'─'*70}")
    print(f"  Top shared-instruction pairs")
    print(f"{'─'*70}")
    print(f"  {'Extension A':<34} {'Extension B':<34} Shared")
    print(f"  {'─'*34} {'─'*34} ──────")
    for a, b, w in edges[:30]:
        print(f"  {a:<34} {b:<34} {w:>4}")
    if len(edges) > 30:
        print(f"  ... and {len(edges)-30} more edges")

    print(f"\n{'─'*70}")
    print(f"  Adjacency list")
    print(f"{'─'*70}")
    for node in nodes:
        neighbours = sorted(adj[node], key=lambda x: -x[1])
        nb_str = "  ".join(f"{b}({w})" for b, w in neighbours)
        print(f"  {node:<{W}} → {nb_str}")

    if len(nodes) <= 50:
        n = len(nodes)
        matrix = [[0] * n for _ in range(n)]
        for a, b, w in edges:
            i, j = node_idx[a], node_idx[b]
            matrix[i][j] = w
            matrix[j][i] = w

        abbr = []
        for nd in nodes:
            s = nd.replace("rv64_", "6:").replace("rv32_", "3:").replace("rv_", "")
            abbr.append(s[:6])

        col_w = 7
        print(f"\n{'─'*70}")
        print("  Adjacency matrix  (● = no shared  |  number = shared count)")
        print(f"{'─'*70}\n")
        header = " " * 20
        for a in abbr:
            header += f"{a:>{col_w}}"
        print(header)
        print(" " * 20 + "─" * (col_w * n))
        for i, node in enumerate(nodes):
            row = f"  {node[:17]:<17} |"
            for j in range(n):
                v = matrix[i][j]
                row += f"{'●':>{col_w}}" if v == 0 else f"{v:>{col_w}}"
            print(row)


# ── Entry point ───────────────────────────────────────────────────────────────

def section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def main():
    instr_dict = os.environ.get("INSTR_DICT", "instr_dict.json")
    manual_src = os.environ.get("MANUAL_SRC", "riscv-isa-manual/src")

    data = load_instr_dict(instr_dict)

    section("Tier 1 — Instruction Set Parsing")
    ext_map = print_tier1(data)

    section("Tier 2 — Cross-Reference with the ISA Manual")
    print_tier2(ext_map, manual_src)

    section("Tier 3 — Extension Sharing Graph")
    print_tier3(data)

if __name__ == "__main__":
    main()
