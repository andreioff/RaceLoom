import os

import pytest

import src
from src.KATch_comm import (
    _StatsKey,
    _processCheckOpResult,
    KATchError,
    KATchComm,
    _toolFormat,
    NKPL_LARROW,
    NKPL_STAR,
    NKPL_FALSE,
    NKPL_TRUE,
    NKPL_AND,
    NKPL_NOT_EQUIV,
    NKPL_CHECK,
)
from src.util import DyNetKATSymbols as sym

PROJECT_DIR_PATH = os.path.dirname(os.path.realpath(src.__file__))
KATCH_PATH = os.path.join(PROJECT_DIR_PATH, "..", "bin", "katch", "katch")


@pytest.fixture
def katch(tmp_path) -> KATchComm:
    outputDir = tmp_path / "katch_test_output"
    outputDir.mkdir()
    return KATchComm(KATCH_PATH, str(outputDir))


def test_processCheckOpResult_output_contains_check_passed_returns_true():
    output = "Check passed successfully"
    error = None
    result = _processCheckOpResult(output, error)
    assert result is True, "Expected True, got False"


def test_processCheckOpResult_error_contains_check_failed_returns_false():
    output = "Some other output"
    error = "Check failed due to mismatch"
    result = _processCheckOpResult(output, error)
    assert result is False, "Expected False, got True"


def test_processCheckOpResult_no_match_raises_katch_error():
    output = "Unexpected output"
    error = "Unexpected error"
    with pytest.raises(KATchError):
        _processCheckOpResult(output, error)


def test_processCheckOpResult_error_none_no_match_raises_katch_error():
    output = "Unexpected output"
    error = None
    with pytest.raises(KATchError):
        _processCheckOpResult(output, error)


def test_toolFormat_empty_netkatEncoding_returns_NKPL_FALSE():
    netkatEncoding = ""
    result = _toolFormat(netkatEncoding)
    assert (
        result == NKPL_FALSE
    ), "The result should be NKPL_FALSE when the input is empty."


def test_toolFormat_valid_symbols_replaced_with_NKPL_equivalents():
    netkatEncoding = f"{sym.ASSIGN} {sym.STAR} {sym.ZERO} {sym.ONE} {sym.AND}"
    result = _toolFormat(netkatEncoding)
    expected = f"{NKPL_LARROW} {NKPL_STAR} {NKPL_FALSE} {NKPL_TRUE} {NKPL_AND}"
    assert (
        result == expected
    ), "The result should replace valid symbols with their NKPL equivalents."


def test_toolFormat_packet_fields_prepended_with_at_symbol():
    netkatEncoding = "(field1) field2"
    result = _toolFormat(netkatEncoding)
    expected = "(@field1) @field2"
    assert result == expected, "The result should prepend '@' to each packet field."


def test_toolFormat_mixed_symbols_and_fields_processed_correctly():
    netkatEncoding = f"(field0{sym.EQUAL}3 {sym.AND} field1 {sym.EQUAL} 4{sym.OR}field2{sym.ASSIGN}field3){sym.STAR}"
    result = _toolFormat(netkatEncoding)
    expected = f"(@field0=3 {NKPL_AND} @field1 = 4{sym.OR}@field2{NKPL_LARROW}@field3)⋆"
    assert (
        result == expected
    ), "The result should handle both symbol replacements and '@' prepending correctly."


def test_runNPKLProgram_valid_input_returns_no_error(katch):
    npklProgram = f"{NKPL_CHECK} {NKPL_FALSE} {NKPL_NOT_EQUIV} {NKPL_TRUE}"
    output, error = katch._runNPKLProgram(npklProgram)
    assert error is None, f"Expected no error, got: {error}"
    assert output != "", "Expected non-empty output."


def test_runNPKLProgram_valid_input_but_failed_check_returns_error_with_check_result(
    katch,
):
    npklProgram = f"{NKPL_CHECK} {NKPL_FALSE} {NKPL_NOT_EQUIV} {NKPL_FALSE}"
    output, error = katch._runNPKLProgram(npklProgram)
    assert (
        output.find("Check passed") == -1
    ), "Expected output to not contain check result."
    assert (
        output.find("Check failed") == -1
    ), "Expected output to not contain check result."
    assert error is not None, f"Expected error, got None."
    assert (
        error.find("Check failed") > -1
    ), "Expected error message to contain 'Check failed'."


def test_isNonEmptyDifference_valid_input_returns_true(katch):
    nkEnc1 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
        + sym.OR
        + f"port {sym.EQUAL} 3 {sym.AND} dst {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 5 "
    )
    nkEnc2 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
        + sym.OR
        + f"field1 {sym.EQUAL} 50 {sym.AND} field2 {sym.EQUAL} 32 {sym.AND} field3 {sym.ASSIGN} 60 "
    )
    result = katch.isNonEmptyDifference(nkEnc1, nkEnc2)
    assert result is True, "Expected True, got False"


def test_isNonEmptyDifference_valid_input_returns_false(katch):
    nkEnc1 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
        + sym.OR
        + f"port {sym.EQUAL} 3 {sym.AND} dst {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 5 "
    )
    nkEnc2 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
        + sym.OR
        + f"field1 {sym.EQUAL} 50 {sym.AND} field2 {sym.EQUAL} 32 {sym.AND} field3 {sym.ASSIGN} 60 "
        + sym.OR
        + f"port {sym.EQUAL} 3 {sym.AND} dst {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 5 "
    )
    result = katch.isNonEmptyDifference(nkEnc1, nkEnc2)
    assert result is False, "Expected False, got True"


def test_isNonEmptyDifference_invalid_input_raises_katch_error(katch):
    nkEnc1 = "random input"
    nkEnc2 = "random input2"
    with pytest.raises(KATchError):
        katch.isNonEmptyDifference(nkEnc1, nkEnc2)


def test_isNonEmptyDifference_empty_expression_does_not_raise_error(katch):
    nkEnc1 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
    )
    nkEnc2 = ""
    result = katch.isNonEmptyDifference(nkEnc1, nkEnc2)
    assert result is True, "Expected True, got False"


def test_isNonEmptyDifference_empty_expression_does_not_raise_error2(katch):
    nkEnc1 = ""
    nkEnc2 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
    )
    result = katch.isNonEmptyDifference(nkEnc1, nkEnc2)
    assert result is False, "Expected False, got True"


def test_isNonEmptyDifference_empty_expression_does_not_raise_error3(katch):
    nkEnc1 = ""
    nkEnc2 = ""
    result = katch.isNonEmptyDifference(nkEnc1, nkEnc2)
    assert result is False, "Expected False, got True"


def test_areNotEquiv_valid_input_returns_true(katch):
    nkEnc1 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
        + sym.OR
        + f"port {sym.EQUAL} 3 {sym.AND} dst {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 5 "
    )
    nkEnc2 = (
        f"port {sym.EQUAL} 3 {sym.AND} dst {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 5 "
        + sym.OR
        + f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
    )
    result = katch.areNotEquiv(nkEnc1, nkEnc2)
    assert result is False, "Expected False, got True"


def test_areNotEquiv_valid_input_returns_false(katch):
    nkEnc1 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
    )
    nkEnc2 = (
        f"port {sym.EQUAL} 3 {sym.AND} dst {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 5 "
        + sym.OR
        + f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
    )
    result = katch.areNotEquiv(nkEnc1, nkEnc2)
    assert result is True, "Expected True, got False"


def test_areNotEquiv_invalid_input_raises_katch_error(katch):
    nkEnc1 = "random input"
    nkEnc2 = "random input2"
    with pytest.raises(KATchError):
        katch.areNotEquiv(nkEnc1, nkEnc2)


def test_areNotEquiv_empty_expression_does_not_raise_error(katch):
    nkEnc1 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
    )
    nkEnc2 = ""
    result = katch.areNotEquiv(nkEnc1, nkEnc2)
    assert result is True, "Expected True, got False"


def test_areNotEquiv_empty_expression_does_not_raise_error2(katch):
    nkEnc1 = ""
    nkEnc2 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
    )
    result = katch.areNotEquiv(nkEnc1, nkEnc2)
    assert result is True, "Expected True, got False"


def test_areNotEquiv_empty_expression_does_not_raise_error3(katch):
    nkEnc1 = ""
    nkEnc2 = ""
    result = katch.areNotEquiv(nkEnc1, nkEnc2)
    assert result is False, "Expected False, got True"


def test_get_stats(katch):
    nkEnc1 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
        + sym.OR
        + f"port {sym.EQUAL} 3 {sym.AND} dst {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 5 "
    )
    nkEnc2 = (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3 "
        + sym.OR
        + f"field1 {sym.EQUAL} 50 {sym.AND} field2 {sym.EQUAL} 32 {sym.AND} field3 {sym.ASSIGN} 60 "
    )
    katch.isNonEmptyDifference(nkEnc1, nkEnc2)
    katch.areNotEquiv(nkEnc1, nkEnc2)
    katch.isNonEmptyDifference(nkEnc1, nkEnc2)
    katch.areNotEquiv(nkEnc1, nkEnc2)
    statsPredicates = {
        _StatsKey.execTime: lambda x: x > 0.0,
        _StatsKey.cacheHits: lambda x: x == 2,
        _StatsKey.cacheMisses: lambda x: x == 2,
    }
    stats = katch.getStats()
    assert len(stats) == len(statsPredicates), "Expected the same number of stats"
    for stat in stats:
        assert (
            stat.key in statsPredicates
        ), f"Expected returned stats to have known keys, but got unknown '{stat.key}'."
        assert statsPredicates[stat.key](
            stat.value
        ), f"Predicate for {stat.key} failed."
