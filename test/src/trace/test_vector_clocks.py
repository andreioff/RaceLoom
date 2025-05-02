import pytest

from src.trace.vector_clocks import (
    newVectorClocks,
    incrementVC,
    _elementWiseMax,
    transferVC,
)


def test_newVectorClocks_valid_size_returns_initialized_vcs():
    size = 3
    result = newVectorClocks(size)
    expected = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    assert result == expected, f"Expected {expected}, got {result}"


def test_newVectorClocks_size_1_returns_initialized_vcs():
    size = 1
    result = newVectorClocks(size)
    expected = [[0]]
    assert result == expected, f"Expected {expected}, got {result}"


def test_newVectorClocks_zero_size_returns_empty_list():
    size = 0
    result = newVectorClocks(size)
    expected = []
    assert result == expected, f"Expected {expected}, got {result}"


def test_newVectorClocks_negative_size_returns_empty_list():
    size = -1
    result = newVectorClocks(size)
    expected = []
    assert result == expected, f"Expected {expected}, got {result}"


def test_incrementVC_valid_position_increments_correctly():
    vcs = [[0, 0], [0, 0]]
    pos = 1
    result = incrementVC(vcs, pos)
    expected = [[0, 0], [0, 1]]
    assert result == expected, f"Expected {expected}, got {result}"


def test_incrementVC_position_0_increments_correctly():
    vcs = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    pos = 0
    result = incrementVC(vcs, pos)
    expected = [[2, 2, 3], [4, 5, 6], [7, 8, 9]]
    assert result == expected, f"Expected {expected}, got {result}"


def test_incrementVC_out_of_bounds_position_raises_value_error():
    vcs = [[0, 0], [0, 0]]
    pos = 2
    with pytest.raises(ValueError):
        incrementVC(vcs, pos)


def test_incrementVC_empty_vcs_raises_value_error():
    vcs = []
    pos = 0
    with pytest.raises(ValueError):
        incrementVC(vcs, pos)


def test_elementWiseMax_equal_length_vcs_returns_max_values():
    vcs1 = [1, 2, 3]
    vcs2 = [3, 1, 2]
    result = _elementWiseMax(vcs1, vcs2)
    expected = [3, 2, 3]
    assert result == expected, f"Expected {expected}, got {result}"


def test_elementWiseMax_vcs1_shorter_than_vcs2_returns_max_values_with_vcs1_size():
    vcs1 = [1, 2]
    vcs2 = [3, 1, 2]
    result = _elementWiseMax(vcs1, vcs2)
    expected = [3, 2]
    assert result == expected, f"Expected {expected}, got {result}"


def test_elementWiseMax_vcs2_shorter_than_vcs1_returns_max_values_with_vcs2_size():
    vcs1 = [1, 2, 3]
    vcs2 = [3, 1]
    result = _elementWiseMax(vcs1, vcs2)
    expected = [3, 2]
    assert result == expected, f"Expected {expected}, got {result}"


def test_elementWiseMax_empty_vcs1_returns_empty_list():
    vcs1 = []
    vcs2 = [3, 1, 2]
    result = _elementWiseMax(vcs1, vcs2)
    expected = []
    assert result == expected, f"Expected {expected}, got {result}"


def test_elementWiseMax_empty_vcs2_returns_empty_list():
    vcs1 = [1, 2, 3]
    vcs2 = []
    result = _elementWiseMax(vcs1, vcs2)
    expected = []
    assert result == expected, f"Expected {expected}, got {result}"


def test_transferVC_valid_vcs_and_positions_transfers_correctly():
    vcs = [[0, 0], [0, 0]]
    srcPos = 0
    dstPos = 1
    result = transferVC(vcs, srcPos, dstPos)
    expected = [[1, 0], [1, 1]]
    assert result == expected, f"Expected {expected}, got {result}"


def test_transferVC_valid_vcs_and_positions_transfers_correctly2():
    vcs = [[1, 2, 3], [4, 5, 2], [7, 2, 3]]
    srcPos = 1
    dstPos = 2
    result = transferVC(vcs, srcPos, dstPos)
    expected = [[1, 2, 3], [4, 6, 2], [7, 6, 4]]
    assert result == expected, f"Expected {expected}, got {result}"


def test_transferVC_valid_vcs_and_equal_positions_raises_value_error():
    vcs = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    srcPos = 2
    dstPos = 2
    with pytest.raises(ValueError):
        transferVC(vcs, srcPos, dstPos)


def test_transferVC_srcPos_out_of_bounds_returns_original():
    vcs = [[0, 0], [0, 0]]
    srcPos = 2
    dstPos = 1
    with pytest.raises(ValueError):
        transferVC(vcs, srcPos, dstPos)


def test_transferVC_dstPos_out_of_bounds_returns_original():
    vcs = [[0, 0], [0, 0]]
    srcPos = 0
    dstPos = 2
    with pytest.raises(ValueError):
        transferVC(vcs, srcPos, dstPos)


def test_transferVC_empty_vcs_returns_original():
    vcs = []
    srcPos = 0
    dstPos = 1
    with pytest.raises(ValueError):
        transferVC(vcs, srcPos, dstPos)
