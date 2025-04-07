import pytest

from src.KATch_comm import KATCH_FALSE, KATCH_TRUE, KATchComm
from src.packet import WILD_CARD
from src.util import DyNetKATSymbols as sym


@pytest.fixture
def katch() -> KATchComm:
    return KATchComm("", "")


def test_processJSONPackets_invalid_json_empty_string_error(katch: KATchComm):
    res, err = katch._KATchComm__processJSONPackets("")
    assert not res
    assert err


def test_processJSONPackets_invalid_json_random_string_error(katch: KATchComm):
    res, err = katch._KATchComm__processJSONPackets("ThisIsARandomString")
    assert not res
    assert err


def test_processJSONPackets_invalid_json_expected_field_not_found_error(
    katch: KATchComm,
):
    res, err = katch._KATchComm__processJSONPackets('{"unexpectedField": "test"}')
    assert not res
    assert err


def test_processJSONPackets_invalid_json_incorect_field_type_error(
    katch: KATchComm,
):
    res, err = katch._KATchComm__processJSONPackets('{"packets": "test"}')
    assert not res
    assert err


def test_processJSONPackets_valid_json_no_packets_success(katch: KATchComm):
    res, err = katch._KATchComm__processJSONPackets('{"packets": []}')
    assert res == sym.ZERO
    assert err is None


def test_processJSONPackets_valid_json_invalid_packet_field_values_error(
    katch: KATchComm,
):
    # packet field values must number or wild card
    res, err = katch._KATchComm__processJSONPackets(
        f'{{"packets": [[\
                {{"field": "dst", "oldValue": "0", "newValue": "{WILD_CARD}"}},\
                {{"field": "port", "oldValue": "test", "newValue": "0"}}\
        ]]}}'
    )
    assert not res
    assert err


def test_processJSONPackets_valid_json_one_packet_success(katch: KATchComm):
    res, err = katch._KATchComm__processJSONPackets(
        '{"packets": [[\
                {"field": "dst", "oldValue": "0", "newValue": "0"},\
                {"field": "port", "oldValue": "1", "newValue": "0"}\
        ]]}'
    )
    assert (
        res
        == f'"dst{sym.EQUAL}0{sym.AND}port{sym.EQUAL}1{sym.AND}dst{sym.ASSIGN}0{sym.AND}port{sym.ASSIGN}0"'
    )
    assert err is None


def test_processJSONPackets_valid_json_multiple_packet_success(katch: KATchComm):
    res, err = katch._KATchComm__processJSONPackets(
        '{"packets": [\
            [\
                {"field": "dst", "oldValue": "0", "newValue": "0"},\
                {"field": "port", "oldValue": "1", "newValue": "0"}\
            ],\
            [\
                {"field": "dst", "oldValue": "1", "newValue": "0"},\
                {"field": "port", "oldValue": "6", "newValue": "7"}\
            ],\
            [\
                {"field": "dst", "oldValue": "0", "newValue": "1"},\
                {"field": "port", "oldValue": "3", "newValue": "2"}\
            ]\
        ]}'
    )
    assert (
        res
        == f'"dst{sym.EQUAL}0{sym.AND}port{sym.EQUAL}1{sym.AND}dst{sym.ASSIGN}0{sym.AND}port{sym.ASSIGN}0"'
        + f" {sym.OR_ALT} "
        + f'"dst{sym.EQUAL}1{sym.AND}port{sym.EQUAL}6{sym.AND}dst{sym.ASSIGN}0{sym.AND}port{sym.ASSIGN}7"'
        + f" {sym.OR_ALT} "
        + f'"dst{sym.EQUAL}0{sym.AND}port{sym.EQUAL}3{sym.AND}dst{sym.ASSIGN}1{sym.AND}port{sym.ASSIGN}2"'
    )
    assert err is None


def test_process_output_empty_string_error(katch: KATchComm):
    res, err = katch.processPktMappingOutput("")
    assert not res
    assert err


def test_process_output_no_matching_string_error(katch: KATchComm):
    res, err = katch.processPktMappingOutput(
        'invalid Inoutmap at /path/to/file {"json": "json"}\n'
    )
    assert not res
    assert err


def test_process_output_no_path_error(katch: KATchComm):
    res, err = katch.processPktMappingOutput("Inoutmap at []\n")
    assert not res
    assert err


def test_process_output_no_json_error(katch: KATchComm):
    res, err = katch.processPktMappingOutput("Inoutmap at /path/to/file\n")
    assert not res
    assert err


def test_process_output_empty_matching_path_and_json_success(katch: KATchComm):
    res, err = katch.processPktMappingOutput("Inoutmap at  \n")
    assert res == sym.ZERO
    assert err is None


def test_process_output_empty_matching_json_success(katch: KATchComm):
    res, err = katch.processPktMappingOutput("Inoutmap at /path/to/file \n")
    assert res == sym.ZERO
    assert err is None


def test_process_output_empty_matching_json_only_whitespaces_success(katch: KATchComm):
    res, err = katch.processPktMappingOutput("Inoutmap at /path/to/file \t\t\n\n")
    assert res == sym.ZERO
    assert err is None


def test_process_output_empty_matching_path_success(katch: KATchComm):
    res, err = katch.processPktMappingOutput("Inoutmap at  []\n")
    assert res == sym.ZERO
    assert err is None


def test_process_output_no_new_line_success(katch: KATchComm):
    res, err = katch.processPktMappingOutput("Inoutmap at /path/to/file []")
    assert res == sym.ZERO
    assert err is None


def test_process_output_no_new_line(katch: KATchComm):
    res, err = katch.processPktMappingOutput("Inoutmap at /path/to/file []")
    assert res == sym.ZERO
    assert err is None


def test_process_output_drop_all_packets_success(katch: KATchComm):
    res, err = katch.processPktMappingOutput(
        f"Inoutmap at /path/to/file [[ {KATCH_FALSE} ]]"
    )
    assert res == sym.ZERO
    assert err is None


def test_process_output_forward_all_packets_success(katch: KATchComm):
    res, err = katch.processPktMappingOutput(
        f"Inoutmap at /path/to/file [[ {KATCH_TRUE} ]]"
    )
    assert res == sym.ONE
    assert err is None
