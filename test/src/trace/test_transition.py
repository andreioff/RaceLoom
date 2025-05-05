import pytest

from src.errors import ParseError
from src.trace.transition import (
    TraceTransition,
    PktProcTrans,
    RcfgTrans,
    newTraceTransition,
)


class TestTraceTransition:
    def test_new_trace_transition_has_empty_fields(self):
        transition = TraceTransition()
        assert transition.policy == ""
        assert transition.getSource() == -1

    def test_updateVC_returns_original_vc(self):
        vcs = [[0, 1], [2, 3]]
        transition = TraceTransition()
        updated_vcs = transition.updateVC(vcs)
        assert updated_vcs == vcs


class TestPktProcTrans:
    def test_getSource_returns_swPos(self):
        swPos = 2
        transition = PktProcTrans("", swPos)
        assert transition.getSource() == swPos

    def test_updateVC_returns_new_vcs_incremented_at_correct_position(self):
        vcs = [[0, 1], [2, 3]]
        swPos = 1
        transition = PktProcTrans("policy", swPos)
        updated_vcs = transition.updateVC(vcs)
        assert updated_vcs == [[0, 1], [2, 4]]
        assert not updated_vcs == vcs

    def test_updateVC_out_of_bounds_switch_position_raises_value_error(self):
        vcs = [[0, 1], [2, 3]]
        swPos = 4
        transition = PktProcTrans("policy", swPos)
        with pytest.raises(ValueError):
            transition.updateVC(vcs)

    def test_toStr_transition_is_formatted_as_expected(self):
        t = PktProcTrans("policy", 254)
        assert str(t) == "proc('policy', 254)"

    def test_fromStr_valid_string_returns_initialized_object(self):
        transition = PktProcTrans.fromStr("proc('policy',12345)")
        assert transition.policy == "policy"
        assert transition.swPos == 12345

    def test_fromStr_invalid_string_raises_parse_error(self):
        cases = [
            "proc('policy', -1)",
            "proc('policy',12345,67890)",
            "proc('policy')",
            "proc(12345)",
            "proc('policy', 'not_a_number')",
            "invalid_string",
        ]
        for case in cases:
            with pytest.raises(ParseError):
                PktProcTrans.fromStr(case)


class TestRcfgTrans:
    def test_getSource_returns_src_pos(self):
        t = RcfgTrans("policy", 4, 10, "ch")
        assert t.getSource() == 4

    def test_updateVC_returns_new_vcs_incremented_at_correct_positions(self):
        vcs = [[0, 1, 2], [3, 4, 5], [2, 4, 7]]
        t = RcfgTrans("policy", 1, 2, "ch")
        updated_vcs = t.updateVC(vcs)
        assert not updated_vcs == vcs
        assert updated_vcs == [[0, 1, 2], [3, 5, 5], [3, 5, 8]]

    def test_updateVC_out_of_bounds_src_pos_raises_value_error(self):
        vcs = [[0, 1], [2, 3]]
        t = RcfgTrans("policy", 2, 1, "ch")
        with pytest.raises(ValueError):
            t.updateVC(vcs)

    def test_updateVC_out_of_bounds_dst_pos_raises_value_error(self):
        vcs = [[0, 1], [2, 3]]
        t = RcfgTrans("policy", 0, 2, "ch")
        with pytest.raises(ValueError):
            t.updateVC(vcs)

    def test_toStr_transition_is_formatted_as_expected(self):
        t = RcfgTrans("policy", 2, 3, "ch")
        assert str(t) == "rcfg(ch, 'policy', 2, 3)"

    def test_fromStr_valid_string_returns_initialized_object(self):
        t = RcfgTrans.fromStr("rcfg(ch, 'policy', 4, 5)")
        assert t.policy == "policy"
        assert t.channel == "ch"
        assert t.srcPos == 4
        assert t.dstPos == 5

    def test_fromStr_invalid_string_raises_parse_error(self):
        cases = [
            "rcfg(ch, 'policy', 4, 4)",
            "rcfg(ch, 'policy', -1, 5)",
            "rcfg(ch, 'policy', 4, -1)",
            "rcfg(ch, 'policy', 4)",
            "rcfg(ch, 'policy', 4, 5, 6)",
            "rcfg(ch, 12345, 4, 5)",
            "rcfg(ch, 'policy', 'not_a_number', 5)",
            "invalid_string",
        ]
        for case in cases:
            with pytest.raises(ParseError):
                RcfgTrans.fromStr(case)


def test_newTraceTransition_valid_transition_string_returns_correct_object():
    cases = [
        "proc('policy',12345)",
        "rcfg(ch, 'policy', 12345, 75643)",
        "proc",
        "proc('policy', -1)",
        "rcfg(ch, 'policy', 123, 75643, 123)",
        "",
        "random_string",
    ]
    expected = [
        PktProcTrans,
        RcfgTrans,
        TraceTransition,
        TraceTransition,
        TraceTransition,
        TraceTransition,
        TraceTransition,
    ]
    for case, expected in zip(cases, expected):
        t = newTraceTransition(case)
        assert isinstance(t, expected)
