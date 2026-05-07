import pytest
from collections import defaultdict
from main import (
    group_by_extension, find_multi_extension,
    normalise, extract_manual_extensions,
    build_sharing_graph
)

SAMPLE_DATA = {
    "add":     {"extension": ["rv_i"]},
    "addi":    {"extension": ["rv_i"]},
    "sh1add":  {"extension": ["rv_zba"]},
    "sh2add":  {"extension": ["rv_zba"]},
    "andn":    {"extension": ["rv_zbb", "rv_zbkb", "rv_zk"]},
    "orn":     {"extension": ["rv_zbb", "rv_zbkb", "rv_zk"]},
    "clmul":   {"extension": ["rv_zbc", "rv_zbkc"]},
    "no_ext":  {},
}


class TestGroupByExtension:
    def test_basic_grouping(self):
        result = group_by_extension(SAMPLE_DATA)
        assert set(result["rv_i"]) == {"ADD", "ADDI"}

    def test_multi_ext_instruction_appears_in_each(self):
        result = group_by_extension(SAMPLE_DATA)
        assert "ANDN" in result["rv_zbb"]
        assert "ANDN" in result["rv_zbkb"]
        assert "ANDN" in result["rv_zk"]

    def test_missing_extension_key_handled(self):
        result = group_by_extension(SAMPLE_DATA)
        for mnemonics in result.values():
            assert "NO_EXT" not in mnemonics

    def test_all_extensions_present(self):
        result = group_by_extension(SAMPLE_DATA)
        expected = {"rv_i", "rv_zba", "rv_zbb", "rv_zbkb", "rv_zk", "rv_zbc", "rv_zbkc"}
        assert expected.issubset(result.keys())

    def test_counts_correct(self):
        result = group_by_extension(SAMPLE_DATA)
        assert len(result["rv_i"]) == 2
        assert len(result["rv_zba"]) == 2
        assert len(result["rv_zk"]) == 2


class TestFindMultiExtension:
    def test_finds_multi(self):
        result = find_multi_extension(SAMPLE_DATA)
        mnemonics = [m for m, _ in result]
        assert "ANDN" in mnemonics
        assert "ORN" in mnemonics
        assert "CLMUL" in mnemonics

    def test_single_ext_not_included(self):
        result = find_multi_extension(SAMPLE_DATA)
        mnemonics = [m for m, _ in result]
        assert "ADD" not in mnemonics
        assert "SH1ADD" not in mnemonics

    def test_extensions_are_sorted(self):
        for _, exts in find_multi_extension(SAMPLE_DATA):
            assert exts == sorted(exts)

    def test_result_is_sorted_by_mnemonic(self):
        result = find_multi_extension(SAMPLE_DATA)
        mnemonics = [m for m, _ in result]
        assert mnemonics == sorted(mnemonics)

    def test_empty_input(self):
        assert find_multi_extension({}) == []

    def test_no_multi_ext(self):
        data = {"add": {"extension": ["rv_i"]}, "sub": {"extension": ["rv_i"]}}
        assert find_multi_extension(data) == []


class TestNormalise:
    def test_strips_rv_prefix(self):
        assert normalise("rv_zba") == "zba"

    def test_strips_rv64_prefix(self):
        assert normalise("rv64_zbb") == "zbb"

    def test_strips_rv32_prefix(self):
        assert normalise("rv32_zknd") == "zknd"

    def test_already_bare(self):
        assert normalise("zba") == "zba"

    def test_lowercases(self):
        assert normalise("Zba") == "zba"

    def test_plain_letter(self):
        assert normalise("rv_i") == "i"

    def test_strips_whitespace(self):
        assert normalise("  rv_zba  ") == "zba"


class TestBuildSharingGraph:
    def test_shared_pair_detected(self):
        pairs = build_sharing_graph(SAMPLE_DATA)
        assert ("rv_zbb", "rv_zbkb") in pairs or ("rv_zbkb", "rv_zbb") in pairs

    def test_weight_correct(self):
        pairs = build_sharing_graph(SAMPLE_DATA)
        key = ("rv_zbb", "rv_zbkb") if ("rv_zbb", "rv_zbkb") in pairs else ("rv_zbkb", "rv_zbb")
        assert pairs[key] == 2

    def test_single_ext_not_in_graph(self):
        pairs = build_sharing_graph(SAMPLE_DATA)
        all_nodes = {n for (a, b) in pairs for n in (a, b)}
        assert "rv_zba" not in all_nodes

    def test_empty_input(self):
        assert build_sharing_graph({}) == {}

    def test_no_multi_ext_means_empty_graph(self):
        data = {"add": {"extension": ["rv_i"]}, "sub": {"extension": ["rv_m"]}}
        assert build_sharing_graph(data) == {}
