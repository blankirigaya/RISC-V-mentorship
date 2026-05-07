# RISC-V Instruction Set Explorer

A Python program that parses, cross-references, and graphs the RISC-V instruction set extensions across three tiers. Built as a submission for the RISC-V Mentorship Coding Challenge.

---

## Project structure

```
riscv-explorer/
├── main.py           all three tiers in a single file
├── tests.py          23 unit tests (pytest)
├── instr_dict.json   instruction encoding data
├── riscv-isa-manual/ ISA manual source (cloned separately, see Setup)
└── README.md
```

---

## Setup

Python 3.6 or higher is required. The main program has no third-party dependencies. `pytest` is only needed to run the tests.

```bash
# Install pytest (only needed for tests)
pip install pytest

# Clone the ISA manual (needed for Tier 2)
git clone --depth=1 https://github.com/riscv/riscv-isa-manual.git

# Place instr_dict.json in the same directory as main.py
# Source: https://github.com/rpsene/riscv-extensions-landscape
```

---

## Usage

```bash
# Run all three tiers
python main.py

# Run with custom file paths
INSTR_DICT=path/to/instr_dict.json MANUAL_SRC=path/to/riscv-isa-manual/src python main.py

# Run the tests
python -m pytest tests.py -v
```

If `riscv-isa-manual/` is not found, Tier 2 is skipped with instructions on how to clone it. Tiers 1 and 3 still run normally.

---

## Sample output

### Tier 1 — Instruction Set Parsing

```
Extension                        Count  Example
-------------------------------------------------
rv_i                                37  ADD
rv_v                               627  VAADDU_VV
rv_zba                               3  SH1ADD
rv_zbb                              17  ANDN
rv_zk                               15  ANDN
...
Total extensions:    114
Total instruction slots:   1343

Instructions in multiple extensions: 73

Mnemonic      Extensions
------------------------------------------------------------------------
ANDN          rv_zbb, rv_zbkb, rv_zk, rv_zkn, rv_zks
CLMUL         rv_zbc, rv_zbkc, rv_zk, rv_zkn, rv_zks
SHA256SIG0    rv_zk, rv_zkn, rv_zknh
...
```

### Tier 2 — Cross-Reference with the ISA Manual

```
Matched  : 31
JSON only: 54
ISA only : 80

31 matched
  zba     json=rv_zba   manual=zba
  zbb     json=rv_zbb   manual=zbb
  zicsr   json=rv_zicsr manual=zicsr
  ...

54 in JSON only
  rv_zvkn, rv_zvks, rv_zbkb, rv_zk, ...

80 in manual only
  sv32, sv39, sm, ss, zmmul, zfa, ...
```

### Tier 3 — Extension Sharing Graph

```
Nodes : 32  |  Edges : 57

Top shared-instruction pairs
  Extension A          Extension B          Shared
  rv64_zk              rv64_zkn                 16
  rv_zk                rv_zkn                   15
  rv_zk                rv_zks                   11
  ...

Adjacency list
  rv_zk  → rv_zkn(15)  rv_zks(11)  rv_zbkb(7)  rv_zbb(5) ...
  ...
```

---

## What the output means

### Tier 1

The program groups all 1,188 instructions from `instr_dict.json` into 114 extension tags.

- **Total instruction slots (1,343)** is higher than unique instructions (1,188) because some instructions appear in multiple extensions and are counted once per extension. For example `ANDN` appears in 5 extensions so it contributes 5 slots.
- **73 instructions belong to more than one extension.** This is by design in RISC-V — bundle extensions like `rv_zk` (cryptography) are supersets that include everything from `rv_zkn`, `rv_zks`, and `rv_zknh`. Any instruction in those sub-extensions also appears under `rv_zk`.
- `rv_v` dominates with 627 instructions because the vector extension is very large, covering element-wise operations across every combination of data type and operand format.

### Tier 2

Extension names are normalised before comparing — `rv_zba` and `rv32_zknd` from the JSON are stripped to `zba` and `zknd`, and names from the manual like `Zba` are lowercased. This way naming differences between the two sources do not cause false mismatches.

- **31 matched** — these extensions exist in both the JSON encoding table and the ISA manual source files.
- **54 JSON only** — mostly newer crypto and vector sub-extensions (`rv_zvkn`, `rv_zvbb`, `rv_zvkned`, etc.) that were added to the encoding table after the manual chapters were written. Also includes compound tags like `rv_c_d` and `rv_zabha_zacas` which represent instruction subsets that the manual does not name separately.
- **80 manual only** — includes privilege and platform-level groupings (`sv32`, `sv39`, `sm`, `ss`) which describe CPU behaviour rather than individual instruction encodings, so they have no entries in the JSON. Also includes retired or draft extensions (`b`, `p`, `zfinx`) and profile shorthand names (`z`, `x`, `g`) that appear in manual prose but have no encoding table entries.

### Tier 3

The graph connects extensions that share at least one instruction. Two completely separate clusters are visible:

**Scalar crypto cluster** — `rv_zk`, `rv_zkn`, `rv_zks`, `rv_zbb`, `rv_zbkb`, `rv_zbc`, `rv_zbkc`, `rv_zbkx`, and their rv32/rv64 variants. These are all heavily interconnected because `rv_zk` and `rv_zkn`/`rv_zks` are bundle extensions that reuse the same primitives.

**Vector crypto cluster** — `rv_zvkn`, `rv_zvks`, `rv_zvbb`, `rv_zvkned`, `rv_zvknha`, `rv_zvknhb`, `rv_zvksed`, `rv_zvksh`. Same bundling pattern repeated in the vector domain.

The two clusters have zero edges between them — scalar and vector crypto instructions are entirely distinct.

---

## Design decisions

**Single file.** All three tiers live in `main.py` with clearly separated functions and sections. Tests import directly from `main`.

**Normalisation strategy (Tier 2).** Rather than fuzzy matching, the normaliser applies a deterministic rule: strip the `rv_`, `rv32_`, or `rv64_` prefix and lowercase. This means every mismatch in the output is a genuine discrepancy between the two sources, not a normalisation failure. Compound tags like `rv_zabha_zacas` and `rv_c_d` have no bare-name equivalent in the manual and correctly appear in the JSON-only list.

**Graph scope (Tier 3).** Only extensions with at least one shared instruction appear in the graph. Extensions with entirely unique instruction sets are excluded — they would be isolated nodes that add nothing to the graph.

**Graceful degradation.** If the ISA manual directory is missing, Tier 2 prints a helpful message and skips. The other two tiers still run.

---

## Assumptions

- The `"extension"` field in `instr_dict.json` is the authoritative list of which extensions an instruction belongs to.
- Extension anchors in the manual (`[[ext:name]]`) and inline references (`ext:name[]`) are treated as equally valid evidence that an extension is documented.
- The `rv32_` and `rv64_` prefixes in the JSON represent width-specific variants of the same logical extension, so `rv64_zknd` normalises to `zknd` and matches `zknd` in the manual.
- Instructions with no `"extension"` field are silently skipped.

---

## Sources

- Instruction encoding data: https://github.com/rpsene/riscv-extensions-landscape
- ISA manual source: https://github.com/riscv/riscv-isa-manual
