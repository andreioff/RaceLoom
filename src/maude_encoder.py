from enum import StrEnum
from typing import List, Tuple


class MaudeEncodingError(Exception):
    pass


class MaudeOps(StrEnum):
    BIG_SWITCH_OP = "bigSwitch"
    GET_REC_POL = "getRecPol"


class MaudeSorts(StrEnum):
    CHANNEL_SORT = "Channel"
    STRING_SORT = "String"
    NAT_SORT = "Nat"
    STR_MAP_SORT = "StrMap"
    RECURSIVE_SORT = "Recursive"
    TRACE_NODES_SORT = "TraceNodes"


class MaudeModules(StrEnum):
    TRACER = "TRACER"
    DNK_MODEL = "DNK-MODEL"
    DNK_MODEL_UTIL = "DNK-MODEL-UTIL"
    ENTRY = "ENTRY"


class OpTypeDef:
    def __init__(self, returnSort: str, argSorts: List[str]):
        self.returnSort = returnSort
        self.argSorts = argSorts
        self.__hash = hash(" ".join([self.returnSort] + self.argSorts))

    def __hash__(self) -> int:
        return self.__hash

    def __eq__(self, other: object) -> bool:
        if isinstance(other, OpTypeDef):
            return (
                self.returnSort == other.returnSort and self.argSorts == other.argSorts
            )
        return False


class MaudeEncoder:
    def __init__(self) -> None:
        self.protImports: List[str] = []
        # operator type definition to operator names
        self.ops: dict[OpTypeDef, List[str]] = {}
        # var type to var names
        self.variables: dict[str, List[str]] = {}
        self.eqs: List[Tuple[str, str]] = []

    def build(self) -> str:
        return "\n\n".join(
            [
                self.__buildProtImports(),
                self.__buildOps(),
                self.__buildVars(),
                self.__buildEqs(),
            ]
        )

    def buildAsModule(self, modName: str) -> str:
        return f"""
        mod {modName} is
        {self.build()}
        endm
        """

    def __buildProtImports(self) -> str:
        if not self.protImports:
            return ""

        importStrs: List[str] = []
        for modName in self.protImports:
            importStrs.append(f"protecting {modName} .")
        return "\n\n".join(importStrs)

    def __buildOps(self) -> str:
        if not self.ops:
            return ""

        opStrs: List[str] = []
        for typeDef, names in self.ops.items():
            declKeyword = "op"
            if len(names) > 1:
                declKeyword = "ops"
            opStrs.append(
                f"{declKeyword} {' '.join(names)} : "
                + f"{' '.join(typeDef.argSorts)} -> {typeDef.returnSort} ."
            )

        return "\n".join(opStrs)

    def __buildEqs(self) -> str:
        if not self.eqs:
            return ""

        eqStrs: List[str] = []
        for leftTerm, rightTerm in self.eqs:
            if not leftTerm or not rightTerm:
                continue

            eqStrs.append(f"eq {leftTerm} = {rightTerm} .")
        return "\n\n".join(eqStrs)

    def __buildVars(self) -> str:
        if not self.variables:
            return ""

        varStrs: List[str] = []
        for varSort, names in self.variables.items():
            declKeyword = "var"
            if len(names) > 1:
                declKeyword = "vars"
            varStrs.append(f"{declKeyword} {' '.join(names)} : {varSort} .")

        return "\n".join(varStrs)

    def addProtImport(self, modName: str) -> None:
        if modName not in MaudeModules:
            raise MaudeEncodingError(f"Unknown module name: '{modName}'")
        if modName not in self.protImports:
            self.protImports.append(modName)

    def addOp(self, name: str, retSort: str, argSorts: List[str]) -> None:
        opTypeDef = OpTypeDef(retSort, argSorts)
        if opTypeDef not in self.ops:
            self.ops[opTypeDef] = []
        opName = name + ("_" * len(argSorts))
        if opName not in self.ops[opTypeDef]:
            self.ops[opTypeDef].append(opName)

    def addVar(self, name: str, sort: str) -> None:
        if sort not in self.variables:
            self.variables[sort] = []
        if name not in self.variables[sort]:
            self.variables[sort].append(name)

    def addEq(self, leftTerm: str, rightTerm: str) -> None:
        self.eqs.append((leftTerm, rightTerm))

    def recPolTerm(self, term: str) -> str:
        return MaudeOps.GET_REC_POL + "(" + term + ")"

    def mapInsert(self, key: str, value: str, mapVar: str) -> str:
        return f"insert({key}, {value}, {mapVar})"

    def mapAccess(self, key: str, mapVar: str) -> str:
        return f"{mapVar}[{key}]"

    def convertIntoMap(self, strs: List[str]) -> str:
        if not strs:
            return "empty"

        if len(strs) == 1:
            return f"(0 |-> {strs[0]} , empty)"

        maudeMap: List[str] = []
        for i, s in enumerate(strs):
            maudeMap.append(f"{i} |-> {s}")
        return "(" + " , ".join(maudeMap) + ")"

    def concatStr(self, s1: str, s2: str) -> str:
        return f"{s1} + {s2}"
