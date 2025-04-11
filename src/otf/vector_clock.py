from typing import List


def newVectorClocks(size: int) -> List[List[int]]:
    vc: List[int] = [0 for _i in range(size)]
    return [vc.copy() for _i in range(size)]


def __isWithinBounds(vcs: List[List[int]], pos: int) -> bool:
    return pos >= 0 and pos < len(vcs) and pos < len(vcs[pos])


def incrementVC(vcs: List[List[int]], pos: int) -> List[List[int]]:
    if not __isWithinBounds(vcs, pos):
        return vcs
    newVc = [v.copy() for v in vcs]
    newVc[pos][pos] += 1
    return newVc


def elementWiseMax(vcs1: List[int], vcs2: List[int]) -> List[int]:
    """Returns a new vector clock containing the maximum value
    between the given VCs at each corresponding position.
    The resulting vector clock will have the size of the smallest given vc."""
    maxVc: List[int] = []
    minSize = min(len(vcs1), len(vcs2))
    for i in range(minSize):
        maxVc.append(max(vcs1[i], vcs2[i]))
    return maxVc


def transferVC(vcs: List[List[int]], srcPos: int, dstPos: int) -> List[List[int]]:
    if not __isWithinBounds(vcs, srcPos) or not __isWithinBounds(vcs, dstPos):
        return vcs
    newVc = [v.copy() for v in vcs]
    newVc[srcPos][srcPos] += 1
    newVc[dstPos] = elementWiseMax(newVc[srcPos], newVc[dstPos])
    newVc[dstPos][dstPos] += 1
    return newVc
