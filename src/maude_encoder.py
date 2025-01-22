from typing import List, Tuple


def declareOps(ops: dict[Tuple[str, str], List[str]]) -> str:
    if not ops:
        return ""

    opStrs: List[str] = []
    for (opSort, argSorts), names in ops.items():
        declKeyword = "op"
        if len(names) > 1:
            declKeyword = "ops"
        opStrs.append(f"{declKeyword} {' '.join(names)} : {argSorts} -> {opSort} .")

    return "\n".join(opStrs)


def declareEqs(eqs: List[Tuple[str, str]]) -> str:
    if not eqs:
        return ""

    eqStrs: List[str] = []
    for leftTerm, rightTerm in eqs:
        if not leftTerm or not rightTerm:
            continue

        eqStrs.append(f"eq {leftTerm} = {rightTerm} .")
    return "\n\n".join(eqStrs)


def declareVars(variables: dict[str, List[str]]) -> str:
    if not variables:
        return ""

    varStrs: List[str] = []
    for varSort, names in variables.items():
        declKeyword = "var"
        if len(names) > 1:
            declKeyword = "vars"
        varStrs.append(f"{declKeyword} {' '.join(names)} : {varSort} .")

    return "\n".join(varStrs)


def mapInsert(key: str, value: str, mapVar: str) -> str:
    return f"insert({key}, {value}, {mapVar})"


def toMaudeMap(strs: List[str]) -> str:
    if not strs:
        return "empty"

    if len(strs) == 1:
        return f"(0 |-> {strs[0]} , empty)"

    maudeMap: List[str] = []
    for i, s in enumerate(strs):
        maudeMap.append(f"{i} |-> {s}")
    return "(" + " , ".join(maudeMap) + ")"
