from typing import List

from typing_extensions import Self

import src.model.json_model as jm
from src.KATch_hook import KATCH_HOOK_MAUDE_NAME as KATCH_OP
from src.maude_encoder import MaudeEncoder
from src.maude_encoder import MaudeOps as mo
from src.maude_encoder import MaudeSorts as ms
from src.util import DyNetKATSymbols as sym

LINK_VAR_NAME = "Link"
BIG_SW_VAR_NAME = "BSWMain"
BIG_SW_RECV_VAR_NAME = "BSWRecv"
SW_MAP_VAR_NAME = "Sws"
CH_VAR_NAME = "CH"
INDX_VAR_NAME = "I"
FR_VAR_NAME = "FR"


class DNKModelError(Exception):
    pass


class DNKMaudeModel:
    def __init__(self) -> None:
        self.me = MaudeEncoder()
        self.bigSwitchTerm: str = ""
        self.controllersMaudeMap: str = self.me.toMaudeMap([])

    def fromJson(self, jsonStr: str) -> Self:
        """
        Raises: ValidationError if `jsonStr` does not correspond to the expected model
        """
        jsonModel = jm.DNKNetwork.model_validate_json(jsonStr)
        self.__declareLink(jsonModel)
        self.__declareChannels(jsonModel)
        self.__declareInitialSwitches(jsonModel)
        self.__declareControllers(jsonModel)
        self.__declareBigSwitch(jsonModel)
        self.__buildBigSwitchTerm(jsonModel)
        self.__buildControllersMapTerm(jsonModel)

        return self

    def toMaudeModuleContent(self) -> str:
        return self.me.build()

    def __declareChannels(self, model: jm.DNKNetwork) -> None:
        channels: dict[str, bool] = {}

        if model.OtherChannels is not None:
            for ch in model.OtherChannels:
                channels[ch] = True

        for sw in model.Switches.values():
            for du in sw.DirectUpdates:
                channels[du.Channel] = True
            for ru in sw.RequestedUpdates:
                channels[ru.RequestChannel] = True
                channels[ru.ResponseChannel] = True

        for ch in channels.keys():
            self.me.addOp(ch, ms.CHANNEL_SORT, [])

    def __declareInitialSwitches(self, model: jm.DNKNetwork) -> None:
        for name, switch in model.Switches.items():
            self.me.addOp(name, ms.STRING_SORT, [])
            initialValue = f"{sym.ZERO}"
            if switch.InitialFlowTable is not None:
                initialValue = switch.InitialFlowTable
            self.me.addEq(name, f'"{initialValue}"')

    def __declareControllers(self, model: jm.DNKNetwork) -> None:
        for name, expr in model.Controllers.items():
            self.me.addOp(name, ms.RECURSIVE_SORT, [])
            self.me.addEq(self.me.recPolTerm(name), expr)

    def __declareLink(self, model: jm.DNKNetwork) -> None:
        """
        If the given model has an empty 'Links' field, it sets the value of the
        actual Maude operator to NetKAT value 1, i.e. forward everything,
        to prevent NetKAT expressions using the link operator in
        conjunctions from breaking.
        """
        linksValue = sym.ONE.value
        if model.Links is not None:
            linksValue = model.Links
        self.me.addOp(LINK_VAR_NAME, ms.STRING_SORT, [])
        self.me.addEq(LINK_VAR_NAME, f'"{linksValue}"')

    def __declareBigSwitch(self, model: jm.DNKNetwork) -> None:
        # declare variable for the map of switches
        self.me.addVar(SW_MAP_VAR_NAME, ms.STR_MAP_SORT)
        self.me.addVar(CH_VAR_NAME, ms.CHANNEL_SORT)
        self.me.addVar(FR_VAR_NAME, ms.STRING_SORT)
        self.me.addVar(INDX_VAR_NAME, ms.NAT_SORT)
        # Declare the actual operators for the big switch
        # Main part that sends packet in
        self.me.addOp(BIG_SW_VAR_NAME, ms.RECURSIVE_SORT, [ms.STR_MAP_SORT])
        # Second part that waits for the corresponding packet out
        self.me.addOp(
            BIG_SW_RECV_VAR_NAME,
            ms.RECURSIVE_SORT,
            [ms.STR_MAP_SORT, ms.CHANNEL_SORT, ms.STRING_SORT, ms.NAT_SORT],
        )

        self.me.addEq(
            self.me.recPolTerm(f"{BIG_SW_VAR_NAME} {SW_MAP_VAR_NAME}"),
            self.__buildBigSwMainExpr(model),
        )
        self.me.addEq(
            self.me.recPolTerm(
                f"{BIG_SW_RECV_VAR_NAME} {SW_MAP_VAR_NAME} "
                + f"{CH_VAR_NAME} {FR_VAR_NAME} {INDX_VAR_NAME}"
            ),
            self.__buildBigSwRecvExpr(model),
        )

    def __buildBigSwMainExpr(self, model: jm.DNKNetwork) -> str:
        # Applies the necessary maude operators to
        # concatenate the switches and link expressions,
        # and to re-write everything into head normal form
        # using the KATch hook
        exprs: List[str] = [
            f"{KATCH_OP}({mo.BIG_SWITCH_OP} {SW_MAP_VAR_NAME} {LINK_VAR_NAME}) "
            + f"{sym.SEQ} ({BIG_SW_VAR_NAME} {SW_MAP_VAR_NAME})",
        ]

        def recvAndReplace(ch: str, ft: str, i: int) -> str:
            insExpr = self.me.mapInsert(f"{i}", ft, SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {ft}) {sym.SEQ} ({BIG_SW_VAR_NAME} {insExpr})"

        def recvAndAppend(ch: str, fr: str, i: int) -> str:
            appExpr = self.me.concatStr(
                self.me.mapAccess(f"{i}", SW_MAP_VAR_NAME),
                self.me.concatStr(f' " {sym.OR} " ', fr),
            )
            insExpr = self.me.mapInsert(f"{i}", f"({appExpr})", SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {fr}) {sym.SEQ} ({BIG_SW_VAR_NAME} {insExpr})"

        def sendAndEnterRecvMode(ru: jm.DNKRequestedUpdate, i: int) -> str:
            bigSwitchTerm = (
                f"{BIG_SW_RECV_VAR_NAME} {SW_MAP_VAR_NAME} "
                + f'{ru.ResponseChannel} "{ru.ResponsePolicy}" {i}'
            )
            return (
                f'({ru.RequestChannel} {sym.SEND} "{ru.RequestPolicy}") '
                + f"{sym.SEQ} ({bigSwitchTerm})"
            )

        for i, (_name, switch) in enumerate(model.Switches.items()):
            for du in switch.DirectUpdates:
                action = recvAndAppend if du.Append else recvAndReplace
                exprs.append(action(du.Channel, f'"{du.Policy}"', i))

            for ru in switch.RequestedUpdates:
                exprs.append(sendAndEnterRecvMode(ru, i))

        return f" {sym.OPLUS} ".join(exprs)

    def __buildBigSwRecvExpr(self, model: jm.DNKNetwork) -> str:
        def termName(swsMapTerm: str) -> str:
            return (
                f"{BIG_SW_RECV_VAR_NAME} {swsMapTerm} "
                + f"{CH_VAR_NAME} {FR_VAR_NAME} {INDX_VAR_NAME}"
            )

        # Applies the necessary maude operators to
        # concatenate the switches and link expressions,
        # and to re-write everything into head normal form
        # using the KATch hook
        exprs: List[str] = [
            f"{KATCH_OP}({mo.BIG_SWITCH_OP} {SW_MAP_VAR_NAME} {LINK_VAR_NAME}) "
            + f"{sym.SEQ} ({termName(SW_MAP_VAR_NAME)})",
        ]

        def recvAndReplace(ch: str, ft: str, i: int) -> str:
            insExpr = self.me.mapInsert(f"{i}", ft, SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {ft}) {sym.SEQ} ({termName(insExpr)})"

        def recvAndAppend(ch: str, fr: str, i: int) -> str:
            appExpr = self.me.concatStr(
                self.me.mapAccess(f"{i}", SW_MAP_VAR_NAME),
                self.me.concatStr(f' " {sym.OR} " ', fr),
            )
            insExpr = self.me.mapInsert(f"{i}", f"({appExpr})", SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {fr}) {sym.SEQ} ({termName(insExpr)})"

        for i, (_name, switch) in enumerate(model.Switches.items()):
            for du in switch.DirectUpdates:
                action = recvAndAppend if du.Append else recvAndReplace
                exprs.append(action(du.Channel, f'"{du.Policy}"', i))

        appExpr = self.me.concatStr(
            self.me.mapAccess(f"{INDX_VAR_NAME}", SW_MAP_VAR_NAME),
            self.me.concatStr(f' " {sym.OR} " ', FR_VAR_NAME),
        )
        insExpr = self.me.mapInsert(f"{INDX_VAR_NAME}", f"({appExpr})", SW_MAP_VAR_NAME)
        bigSwTerm = f"{BIG_SW_VAR_NAME} {insExpr}"
        exprs.append(
            f"({CH_VAR_NAME} {sym.RECV} {FR_VAR_NAME}) {sym.SEQ} ({bigSwTerm})"
        )

        return f" {sym.OPLUS} ".join(exprs)

    def __buildBigSwitchTerm(self, model: jm.DNKNetwork) -> None:
        sws: List[str] = []
        for name in model.Switches.keys():
            sws.append(name)
        self.bigSwitchTerm = self.me.recPolTerm(
            f"{BIG_SW_VAR_NAME} {self.me.toMaudeMap(sws)}"
        )

    def __buildControllersMapTerm(self, model: jm.DNKNetwork) -> None:
        recursiveControllers: List[str] = []
        for name in model.Controllers.keys():
            recursiveControllers.append(self.me.recPolTerm(name))

        self.controllersMaudeMap = self.me.toMaudeMap(recursiveControllers)

    def getBigSwitchTerm(self) -> str:
        return self.bigSwitchTerm

    def getControllersMaudeMap(self) -> str:
        return self.controllersMaudeMap
