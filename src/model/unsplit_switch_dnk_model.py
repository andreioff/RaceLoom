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
_BIG_SW_VAR_NAME = "BSWMain"
_BIG_SW_RECV_VAR_NAME = "BSWRecv"
_SW_MAP_VAR_NAME = "Sws"
_CH_VAR_NAME = "CH"
_INDX_VAR_NAME = "I"
_FR_VAR_NAME = "FR"


class UnsplitSwDNKMaudeModel(DNKMaudeModel):
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
            for ru in sw.RequestedUpdates:
                channels[ru.RequestChannel] = True
                channels[ru.ResponseChannel] = True

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
        self.me.addVar(_FR_VAR_NAME, ms.STRING)
        self.me.addVar(_INDX_VAR_NAME, ms.NAT)
        # Declare the actual operators for the big switch
        # Main part that sends packet in
        self.me.addOp(_BIG_SW_VAR_NAME, ms.RECURSIVE, [ms.STR_MAP])
        # Second part that waits for the corresponding packet out
        self.me.addOp(
            _BIG_SW_RECV_VAR_NAME,
            ms.RECURSIVE,
            [ms.STR_MAP, ms.CHANNEL, ms.STRING, ms.NAT],
        )

        self.me.addEq(
            self.me.recPolTerm(f"{_BIG_SW_VAR_NAME} {_SW_MAP_VAR_NAME}"),
            self.__buildBigSwMainExpr(model),
        )
        self.me.addEq(
            self.me.recPolTerm(
                f"{_BIG_SW_RECV_VAR_NAME} {_SW_MAP_VAR_NAME} "
                + f"{_CH_VAR_NAME} {_FR_VAR_NAME} {_INDX_VAR_NAME}"
            ),
            self.__buildBigSwRecvExpr(model),
        )

    def __buildBigSwMainExpr(self, model: jm.DNKNetwork) -> str:
        # Applies the necessary maude operators to
        # concatenate the switches and link expressions,
        # and to re-write everything into head normal form
        # using the KATch hook
        exprs: List[str] = [
            f"({mo.BIG_SWITCH} {_SW_MAP_VAR_NAME} {_LINK_VAR_NAME}) "
            + f"{sym.SEQ} ({_BIG_SW_VAR_NAME} {_SW_MAP_VAR_NAME})",
        ]

        def recvAndReplace(ch: str, ft: str, i: int) -> str:
            insExpr = self.me.mapInsert(f"{i}", ft, _SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {ft}) {sym.SEQ} ({_BIG_SW_VAR_NAME} {insExpr})"

        def recvAndAppend(ch: str, fr: str, i: int) -> str:
            appExpr = self.me.concatStr(
                self.me.mapAccess(f"{i}", _SW_MAP_VAR_NAME),
                self.me.concatStr(f' " {sym.OR} " ', fr),
            )
            insExpr = self.me.mapInsert(f"{i}", f"({appExpr})", _SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {fr}) {sym.SEQ} ({_BIG_SW_VAR_NAME} {insExpr})"

        def sendAndEnterRecvMode(ru: jm.DNKRequestedUpdate, i: int) -> str:
            bigSwitchTerm = (
                f"{_BIG_SW_RECV_VAR_NAME} {_SW_MAP_VAR_NAME} "
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

        self.__addBranchCount("BSw", len(exprs))
        return f" {sym.OPLUS} ".join(exprs)

    def __buildBigSwRecvExpr(self, model: jm.DNKNetwork) -> str:
        def termName(swsMapTerm: str) -> str:
            return (
                f"{_BIG_SW_RECV_VAR_NAME} {swsMapTerm} "
                + f"{_CH_VAR_NAME} {_FR_VAR_NAME} {_INDX_VAR_NAME}"
            )

        # Applies the necessary maude operators to
        # concatenate the switches and link expressions,
        # and to re-write everything into head normal form
        # using the KATch hook
        exprs: List[str] = [
            f"({mo.BIG_SWITCH} {_SW_MAP_VAR_NAME} {_LINK_VAR_NAME}) "
            + f"{sym.SEQ} ({termName(_SW_MAP_VAR_NAME)})",
        ]

        def recvAndReplace(ch: str, ft: str, i: int) -> str:
            insExpr = self.me.mapInsert(f"{i}", ft, _SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {ft}) {sym.SEQ} ({termName(insExpr)})"

        def recvAndAppend(ch: str, fr: str, i: int) -> str:
            appExpr = self.me.concatStr(
                self.me.mapAccess(f"{i}", _SW_MAP_VAR_NAME),
                self.me.concatStr(f' " {sym.OR} " ', fr),
            )
            insExpr = self.me.mapInsert(f"{i}", f"({appExpr})", _SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {fr}) {sym.SEQ} ({termName(insExpr)})"

        for i, (_name, switch) in enumerate(model.Switches.items()):
            for du in switch.DirectUpdates:
                action = recvAndAppend if du.Append else recvAndReplace
                exprs.append(action(du.Channel, f'"{du.Policy}"', i))

        appExpr = self.me.concatStr(
            self.me.mapAccess(f"{_INDX_VAR_NAME}", _SW_MAP_VAR_NAME),
            self.me.concatStr(f' " {sym.OR} " ', _FR_VAR_NAME),
        )
        insExpr = self.me.mapInsert(
            f"{_INDX_VAR_NAME}", f"({appExpr})", _SW_MAP_VAR_NAME
        )
        bigSwTerm = f"{_BIG_SW_VAR_NAME} {insExpr}"
        exprs.append(
            f"({_CH_VAR_NAME} {sym.RECV} {_FR_VAR_NAME}) {sym.SEQ} ({bigSwTerm})"
        )

        return f" {sym.OPLUS} ".join(exprs)

    def __buildBigSwitchTerm(self, model: jm.DNKNetwork) -> str:
        sws: List[str] = []
        for name in model.Switches.keys():
            sws.append(name)
        return self.me.recPolTerm(f"{_BIG_SW_VAR_NAME} {self.me.convertIntoMap(sws)}")

    def __buildElementTerms(self, model: jm.DNKNetwork) -> None:
        elTerms: List[str] = [self.__buildBigSwitchTerm(model)]
        self.elMetadataDict = {0: ElementMetadata(0, ElementType.SW)}
        for i, name in enumerate(model.Controllers.keys()):
            elTerms.append(self.me.recPolTerm(name))
            self.elMetadataDict[i + 1] = ElementMetadata(i + 1, ElementType.CT)
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
