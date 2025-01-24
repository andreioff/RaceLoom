from typing import Callable, List, Self, Tuple

from pydantic import BaseModel, ValidationError
from pydantic.types import StringConstraints
from typing_extensions import Annotated

import src.maude_encoder as me
from src.KATch_hook import KATCH_HOOK_MAUDE_NAME
from src.util import DyNetKATSymbols as sym

MAUDE_CHANNEL_SORT = "Channel"
MAUDE_STRING_SORT = "String"
MAUDE_STR_MAP_SORT = "StrMap"
MAUDE_RECURSIVE_SORT = "Recursive"
LINK_VAR_NAME = "Link"
SWITCHES_MAP_VAR_NAME = "Sws"
BIG_SWITCH_VAR_NAME = "SDN"
BIG_SWITCH_MAUDE_OPERATOR = "bigSwitch"
PACKET_IN_CH_NAME = "pi"
PACKET_OUT_CH_NAME = "po"

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
VarNameString = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9]*$")]


class NetKATSwitch(BaseModel):  # type: ignore
    old: NonEmptyString
    new: NonEmptyString
    channel: VarNameString


class DNKJsonModel(BaseModel):  # type: ignore
    link: NonEmptyString
    switches: dict[VarNameString, NetKATSwitch]
    # controller expressions can refer to switch NetKAT strings
    # by using variables of the form 'new<switch name>' or 'old<switch name>'.
    controllers: dict[VarNameString, NonEmptyString]


class DNKModelError(Exception):
    pass


class DNKModel:
    def __init__(self) -> None:
        self.channels: List[str] = []
        self.netkatSwitches: dict[str, NetKATSwitch] = {}
        self.netkatLink: str = ""
        self.controllers: dict[str, str] = {}

    def fromJson(self, jsonStr: str) -> Self:
        """
        Raises: ValidationError if `jsonStr` does not correspond to the expected model
        """
        jsonModel = DNKJsonModel.model_validate_json(jsonStr)
        if not jsonModel.switches:
            raise ValidationError("DNK model must contain at least 1 switch", [])
        if not jsonModel.controllers:
            raise ValidationError("DNK model must contain at least 1 controller", [])

        self.netkatLink = jsonModel.link
        self.netkatSwitches = jsonModel.switches
        self.controllers = jsonModel.controllers
        return self

    def toMaudeModuleContent(self) -> str:
        ops: dict[Tuple[str, str], List[str]] = {
            (MAUDE_CHANNEL_SORT, ""): [],
            (MAUDE_STRING_SORT, ""): [LINK_VAR_NAME],
            (MAUDE_RECURSIVE_SORT, ""): [],
        }
        variables: dict[str, List[str]] = {MAUDE_STR_MAP_SORT: [SWITCHES_MAP_VAR_NAME]}
        eqs: List[Tuple[str, str]] = [(LINK_VAR_NAME, f'"{self.netkatLink}"')]

        for i in range(len(self.netkatSwitches)):
            ops[(MAUDE_CHANNEL_SORT, "")].append(f"{PACKET_IN_CH_NAME}{i}")
            ops[(MAUDE_CHANNEL_SORT, "")].append(f"{PACKET_OUT_CH_NAME}{i}")

        for name, switch in self.netkatSwitches.items():
            ops[(MAUDE_CHANNEL_SORT, "")].append(switch.channel)
            ops[(MAUDE_STRING_SORT, "")].append("old" + name)
            ops[(MAUDE_STRING_SORT, "")].append("new" + name)
            eqs.append(("old" + name, f'"{switch.old}"'))
            eqs.append(("new" + name, f'"{switch.new}"'))

        for name, expr in self.controllers.items():
            ops[(MAUDE_RECURSIVE_SORT, "")].append(name)
            eqs.append((self.__recLeftTerm(name), expr))

        ops[(MAUDE_RECURSIVE_SORT, MAUDE_STR_MAP_SORT)] = [BIG_SWITCH_VAR_NAME + "_"]
        eqs.append(
            (
                self.__recLeftTerm(f"{BIG_SWITCH_VAR_NAME} {SWITCHES_MAP_VAR_NAME}"),
                self.__getBigSwitchExpr(),
            )
        )

        return "\n\n".join(
            [
                me.declareOps(ops),
                me.declareVars(variables),
                me.declareEqs(eqs),
            ]
        )

    def __getBigSwitchExpr(self) -> str:
        expr: List[str] = [
            "{}({} {} {}) {} ({} {})".format(
                KATCH_HOOK_MAUDE_NAME,
                BIG_SWITCH_MAUDE_OPERATOR,
                SWITCHES_MAP_VAR_NAME,
                LINK_VAR_NAME,
                sym.SEQ,
                BIG_SWITCH_VAR_NAME,
                SWITCHES_MAP_VAR_NAME,
            )
        ]

        recvAndInsert: Callable[[str, str, int], str] = (
            lambda ch, sw, index: "({} {} {}) {} ({} {})".format(
                ch,
                sym.RECV,
                sw,
                sym.SEQ,
                BIG_SWITCH_VAR_NAME,
                me.mapInsert(f"{index}", sw, SWITCHES_MAP_VAR_NAME),
            )
        )

        for i, (name, switch) in enumerate(self.netkatSwitches.items()):
            expr.append(recvAndInsert(switch.channel, "new" + name, i))

        for i, name in enumerate(self.netkatSwitches.keys()):
            newSwInstall = recvAndInsert(f"{PACKET_OUT_CH_NAME}{i}", "new" + name, i)
            expr.append(
                '({} {} "{}") {} ({})'.format(
                    f"{PACKET_IN_CH_NAME}{i}", sym.SEND, sym.ONE, sym.SEQ, newSwInstall
                )
            )

        return f" {sym.OPLUS} ".join(expr)

    def __recLeftTerm(self, name: str) -> str:
        return f"getRecPol({name})"

    def getBigSwitchTerm(self) -> str:
        sws: List[str] = []
        for name in self.netkatSwitches.keys():
            sws.append(f"old{name}")
        return self.__recLeftTerm(f"{BIG_SWITCH_VAR_NAME} {me.toMaudeMap(sws)}")

    def getControllersMaudeMap(self) -> str:
        recursiveControllers: List[str] = []
        for name in self.controllers.keys():
            recursiveControllers.append(self.__recLeftTerm(name))

        return me.toMaudeMap(recursiveControllers)
