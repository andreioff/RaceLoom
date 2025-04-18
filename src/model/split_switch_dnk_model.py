from typing import List

from typing_extensions import Self

import src.model.json_model as jm
from src.maude_encoder import MaudeEncoder
from src.maude_encoder import MaudeModules as mm
from src.maude_encoder import MaudeOps as mo
from src.maude_encoder import MaudeSorts as ms
from src.model.dnk_maude_model import (DNKMaudeModel, ElementMetadata,
                                       ElementType)
from src.util import DyNetKATSymbols as sym

_LINK_VAR_NAME = "Link"
_BIG_SW_COMM_VAR_NAME = "SWComm"
_BIG_SW_RECV_VAR_NAME = "SWRecv"
_BIG_SW_PROC_VAR_NAME = "SWProc"
_SW_MAP_VAR_NAME = "Sws"
_CH_VAR_NAME = "CH"
_INNER_CH_VAR_NAME = "CHInner"
_FR_VAR_NAME = "FR"
_INNER = "Inner"


class SplitSwDNKMaudeModel(DNKMaudeModel):
    def __init__(self) -> None:
        self.me = MaudeEncoder()
        self.elMetadataDict: dict[int, ElementMetadata] = {}
        self.elementTerms: List[str] = []
        self.branchCounts: dict[str, int] = {}

    @classmethod
    def fromJson(cls, jsonStr: str) -> Self:
        """
        Raises: ValidationError if `jsonStr` does not correspond to the expected model
        """
        jsonModel = jm.DNKNetwork.model_validate_json(jsonStr)

        m = cls()
        m.__declareLink(jsonModel)
        m.__declareChannels(jsonModel)
        m.__declareInitialSwitches(jsonModel)
        m.__declareControllers(jsonModel)
        m.__declareBigSwitch(jsonModel)
        m.__buildElementTerms(jsonModel)

        return m

    def toMaudeModule(self) -> str:
        self.me.addProtImport(mm.DNK_MODEL_UTIL)
        return self.me.buildAsModule(mm.DNK_MODEL)

    def __declareChannels(self, model: jm.DNKNetwork) -> None:
        channels: dict[str, bool] = {}

        if model.OtherChannels is not None:
            for ch in model.OtherChannels:
                channels[ch] = True

        for sw in model.Switches.values():
            for du in sw.DirectUpdates:
                channels[du.Channel] = True
                channels[du.Channel + _INNER] = True
            for ru in sw.RequestedUpdates:
                channels[ru.RequestChannel] = True
                channels[ru.ResponseChannel] = True
                channels[ru.ResponseChannel + _INNER] = True

        for ch in channels.keys():
            self.me.addOp(ch, ms.CHANNEL, [])

    def __declareInitialSwitches(self, model: jm.DNKNetwork) -> None:
        for name, switch in model.Switches.items():
            self.me.addOp(name, ms.STRING, [])
            initialValue = f"{sym.ZERO}"
            if switch.InitialFlowTable is not None:
                initialValue = switch.InitialFlowTable
            self.me.addEq(name, f'"{initialValue}"')

    def __declareControllers(self, model: jm.DNKNetwork) -> None:
        for name, expr in model.Controllers.items():
            self.me.addOp(name, ms.RECURSIVE, [])
            self.me.addEq(self.me.recPolTerm(name), expr)
            self.__addBranchCount(name, expr.count(sym.OPLUS))

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
        self.me.addOp(_LINK_VAR_NAME, ms.STRING, [])
        self.me.addEq(_LINK_VAR_NAME, f'"{linksValue}"')

    def __declareBigSwitch(self, model: jm.DNKNetwork) -> None:
        # declare variable for the map of switches
        self.me.addVar(_SW_MAP_VAR_NAME, ms.STR_MAP)
        self.me.addVar(_CH_VAR_NAME, ms.CHANNEL)
        self.me.addVar(_INNER_CH_VAR_NAME, ms.CHANNEL)
        self.me.addVar(_FR_VAR_NAME, ms.STRING)
        # Declare the actual operators for the big switch
        # SW expression that processes packets and updates the flow table
        self.me.addOp(_BIG_SW_PROC_VAR_NAME, ms.RECURSIVE, [ms.STR_MAP])
        # SW expression that communicates with the controller and sends packet in
        self.me.addOp(_BIG_SW_COMM_VAR_NAME, ms.RECURSIVE, [])
        # SW expression that communicates with the controller and
        # waits for the corresponding packet out
        self.me.addOp(
            _BIG_SW_RECV_VAR_NAME,
            ms.RECURSIVE,
            [ms.CHANNEL, ms.CHANNEL, ms.STRING],
        )

        self.me.addEq(
            self.me.recPolTerm(f"{_BIG_SW_COMM_VAR_NAME}"),
            self.__buildBigSwCommExpr(model),
        )
        self.me.addEq(
            self.me.recPolTerm(
                f"{_BIG_SW_RECV_VAR_NAME} {_CH_VAR_NAME} "
                + f"{_INNER_CH_VAR_NAME} {_FR_VAR_NAME}"
            ),
            self.__buildBigSwRecvExpr(model),
        )
        self.me.addEq(
            self.me.recPolTerm(f"{_BIG_SW_PROC_VAR_NAME} {_SW_MAP_VAR_NAME}"),
            self.__buildBigSwProcExpr(model),
        )

    def __buildBigSwCommExpr(self, model: jm.DNKNetwork) -> str:
        exprs: List[str] = []

        def recvAndSendToProc(ch: str, pol: str) -> str:
            innerCh = ch + _INNER
            return (
                f"({ch} {sym.RECV} {pol}) {sym.SEQ} "
                + f"(({innerCh} {sym.SEND} {pol}) {sym.SEQ} {_BIG_SW_COMM_VAR_NAME})"
            )

        def sendAndEnterRecvMode(ru: jm.DNKRequestedUpdate, i: int) -> str:
            innerCh = ru.ResponseChannel + _INNER
            bigSwitchTerm = (
                f"{_BIG_SW_RECV_VAR_NAME} {ru.ResponseChannel} "
                + f'{innerCh} "{ru.ResponsePolicy}"'
            )
            return (
                f'({ru.RequestChannel} {sym.SEND} "{ru.RequestPolicy}") '
                + f"{sym.SEQ} ({bigSwitchTerm})"
            )

        for i, (_name, switch) in enumerate(model.Switches.items()):
            for du in switch.DirectUpdates:
                exprs.append(recvAndSendToProc(du.Channel, f'"{du.Policy}"'))

            for ru in switch.RequestedUpdates:
                exprs.append(sendAndEnterRecvMode(ru, i))

        return f" {sym.OPLUS} ".join(exprs)

    def __buildBigSwRecvExpr(self, model: jm.DNKNetwork) -> str:
        termName = (
            f"{_BIG_SW_RECV_VAR_NAME} {_CH_VAR_NAME} "
            + f"{_INNER_CH_VAR_NAME} {_FR_VAR_NAME}"
        )

        exprs: List[str] = []

        def recvAndSendToProc(ch: str, pol: str) -> str:
            innerCh = ch + _INNER
            return (
                f"({ch} {sym.RECV} {pol}) {sym.SEQ} "
                + f"(({innerCh} {sym.SEND} {pol}) {sym.SEQ} ({termName}))"
            )

        for _name, switch in model.Switches.items():
            for du in switch.DirectUpdates:
                exprs.append(recvAndSendToProc(du.Channel, f'"{du.Policy}"'))

        exprs.append(
            f"({_CH_VAR_NAME} {sym.RECV} {_FR_VAR_NAME}) {sym.SEQ} "
            + f"(({_INNER_CH_VAR_NAME} {sym.SEND} {_FR_VAR_NAME}) "
            + f"{sym.SEQ} {_BIG_SW_COMM_VAR_NAME})"
        )

        return f" {sym.OPLUS} ".join(exprs)

    def __buildBigSwProcExpr(self, model: jm.DNKNetwork) -> str:
        # Applies the necessary maude operators to
        # concatenate the switches and link expressions,
        # and to re-write everything into head normal form
        # using the KATch hook
        exprs: List[str] = [
            f"({mo.BIG_SWITCH} {_SW_MAP_VAR_NAME} {_LINK_VAR_NAME}) "
            + f"{sym.SEQ} ({_BIG_SW_PROC_VAR_NAME} {_SW_MAP_VAR_NAME})",
        ]

        def recvAndReplace(ch: str, ft: str, i: int) -> str:
            insExpr = self.me.mapInsert(f"{i}", ft, _SW_MAP_VAR_NAME)
            return (
                f"({ch} {sym.RECV} {ft}) {sym.SEQ} ({_BIG_SW_PROC_VAR_NAME} {insExpr})"
            )

        def recvAndAppend(ch: str, fr: str, i: int) -> str:
            appExpr = self.me.concatStr(
                self.me.mapAccess(f"{i}", _SW_MAP_VAR_NAME),
                self.me.concatStr(f' " {sym.OR} " ', fr),
            )
            insExpr = self.me.mapInsert(f"{i}", f"({appExpr})", _SW_MAP_VAR_NAME)
            return (
                f"({ch} {sym.RECV} {fr}) {sym.SEQ} ({_BIG_SW_PROC_VAR_NAME} {insExpr})"
            )

        for i, (_name, switch) in enumerate(model.Switches.items()):
            for du in switch.DirectUpdates:
                action = recvAndAppend if du.Append else recvAndReplace
                exprs.append(action(du.Channel + _INNER, f'"{du.Policy}"', i))

            for ru in switch.RequestedUpdates:
                exprs.append(
                    recvAndAppend(
                        ru.ResponseChannel + _INNER, f'"{ru.ResponsePolicy}"', i
                    )
                )

        self.__addBranchCount("BSw", len(exprs))
        return f" {sym.OPLUS} ".join(exprs)

    def __buildBigSwitchProcTerm(self, model: jm.DNKNetwork) -> str:
        sws: List[str] = []
        for name in model.Switches.keys():
            sws.append(name)
        return self.me.recPolTerm(
            f"{_BIG_SW_PROC_VAR_NAME} {self.me.convertIntoMap(sws)}"
        )

    def __buildElementTerms(self, model: jm.DNKNetwork) -> None:
        elTerms: List[str] = [
            self.__buildBigSwitchProcTerm(model),
            self.me.recPolTerm(_BIG_SW_COMM_VAR_NAME),
        ]
        self.elMetadataDict = {
            0: ElementMetadata(0, ElementType.SW, _BIG_SW_PROC_VAR_NAME),
            1: ElementMetadata(0, ElementType.SW, _BIG_SW_COMM_VAR_NAME),
        }
        metadataId = 1
        key = len(self.elMetadataDict)
        for i, name in enumerate(model.Controllers.keys()):
            elTerms.append(self.me.recPolTerm(name))
            self.elMetadataDict[key + i] = ElementMetadata(
                metadataId + i, ElementType.CT
            )
        self.elementTerms = elTerms

    def __addBranchCount(self, key: str, count: int) -> None:
        while key in self.branchCounts:
            key = key + "*"
        self.branchCounts[key] = count

    def getBranchCounts(self) -> str:
        bStrs: List[str] = [
            f"{key}:{count}" for (key, count) in self.branchCounts.items()
        ]
        return ";".join(bStrs)

    def getElementTerms(self) -> List[str]:
        return self.elementTerms

    def getMaudeModuleName(self) -> str:
        return mm.DNK_MODEL

    def getElementMetadataDict(self) -> dict[int, ElementMetadata]:
        return self.elMetadataDict
