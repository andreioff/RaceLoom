from dataclasses import dataclass, field
from enum import StrEnum
from typing import List, Self

import src.model.json_model as jm
from src.maude_encoder import MaudeBuilder, MaudeEncoder
from src.maude_encoder import MaudeModules as mm
from src.maude_encoder import MaudeOps as mo
from src.maude_encoder import MaudeSorts as ms
from src.model.util import NetKATReplacer
from src.stats import StatsEntry, StatsGenerator
from src.util import DyNetKATSymbols as sym

_LINK_VAR_NAME = "Link"
_BIG_SW_VAR_NAME = "BSWMain"
_BIG_SW_RECV_VAR_NAME = "BSWRecv"
_SW_MAP_VAR_NAME = "Sws"
_CH_VAR_NAME = "CH"
_INDX_VAR_NAME = "I"
_FR_VAR_NAME = "FR"


class ElementType(StrEnum):
    CT = "CT"
    SW = "SW"


@dataclass(frozen=True)
class ElementMetadata:
    """Data related to a DNK element"""

    # id of the parent network component being modeled, e.g. multiple DNK
    # elements may model different parts of the same switch
    pID: int
    pType: ElementType  # type of parent component
    name: str = ""
    # list of channels for every switch (ordered by the position found
    # in the JSON model)
    switchChannels: List[List[str]] = field(default_factory=list)
    link: str = sym.ZERO
    initialFTs: List[str] = field(default_factory=list)

    def findSwitchIndex(self, ch: str) -> int:
        """Returns the index of the switch that uses the given channel
        or -1 if the channel is not used by any switch.
        """
        for i, channels in enumerate(self.switchChannels):
            if ch in channels:
                return i
        return -1


class DNKModelError(Exception):
    pass


def _collectSwitchChannels(model: jm.DNKNetwork) -> List[List[List[str]]]:
    # Every network has a list of switches. Every switch has a list of channels.
    res: List[List[List[str]]] = []

    switchChannels: List[List[str]] = []
    for sw in model.Switches.values():
        channels: List[str] = []
        for du in sw.DirectUpdates:
            channels.append(du.Channel)
        for ru in sw.RequestedUpdates:
            channels.append(ru.RequestChannel)
            channels.append(ru.ResponseChannel)
        switchChannels.append(channels)
    res.append(switchChannels)
    return res


class DNKMaudeModel(StatsGenerator):
    def __init__(self) -> None:
        self.me = MaudeBuilder()
        self.elsMetadata: List[ElementMetadata] = []
        self.elementTerms: List[str] = []
        self.branchCounts: dict[str, int] = {}
        self.netkatRepl = NetKATReplacer()
        self._networkChannels: List[List[List[str]]] = []

    @classmethod
    def fromJson(cls, jsonStr: str) -> Self:
        """
        Raises: ValidationError if `jsonStr` does not correspond to the expected model
        """
        jsonModel = jm.DNKNetwork.model_validate_json(jsonStr)
        jm.validateSwitchChannels(jsonModel)

        m = cls()
        m.netkatRepl = NetKATReplacer(jsonModel)
        m._networkChannels = _collectSwitchChannels(jsonModel)
        m.__declareLink(jsonModel)
        m.__declareChannels(jsonModel)
        m.__declareInitialSwitches(jsonModel)
        m.__declareControllers(jsonModel)
        m.__declareBigSwitch(jsonModel)
        m.__buildElementTerms(jsonModel)

        return m

    def toMaudeModule(self) -> str:
        self.me.addProtImport(mm.DNK_MODEL_UTIL)
        return self.me.buildAsFuncModule(mm.DNK_MODEL)

    def __declareChannels(self, model: jm.DNKNetwork) -> None:
        chDict: dict[str, bool] = {}

        if model.OtherChannels is not None:
            for ch in model.OtherChannels:
                chDict[ch] = True

        channels = list(chDict.keys())
        for netChannels in self._networkChannels:
            for swChannels in netChannels:
                channels.extend(swChannels)

        for ch in channels:
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
            self.me.addEq(MaudeEncoder.recPolTerm(name), expr)
            self.__addBranchCount(name, expr.count(sym.OPLUS) + 1)

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
            MaudeEncoder.recPolTerm(f"{_BIG_SW_VAR_NAME} {_SW_MAP_VAR_NAME}"),
            self.__buildBigSwMainExpr(model),
        )
        self.me.addEq(
            MaudeEncoder.recPolTerm(
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
            insExpr = MaudeEncoder.mapInsert(f"{i}", ft, _SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {ft}) {sym.SEQ} ({_BIG_SW_VAR_NAME} {insExpr})"

        def recvAndAppend(ch: str, fr: str, i: int) -> str:
            appExpr = MaudeEncoder.concatStr(
                MaudeEncoder.mapAccess(f"{i}", _SW_MAP_VAR_NAME),
                MaudeEncoder.concatStr(f' " {sym.OR} " ', fr),
            )
            insExpr = MaudeEncoder.mapInsert(f"{i}", f"({appExpr})", _SW_MAP_VAR_NAME)
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
            insExpr = MaudeEncoder.mapInsert(f"{i}", ft, _SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {ft}) {sym.SEQ} ({termName(insExpr)})"

        def recvAndAppend(ch: str, fr: str, i: int) -> str:
            appExpr = MaudeEncoder.concatStr(
                MaudeEncoder.mapAccess(f"{i}", _SW_MAP_VAR_NAME),
                MaudeEncoder.concatStr(f' " {sym.OR} " ', fr),
            )
            insExpr = MaudeEncoder.mapInsert(f"{i}", f"({appExpr})", _SW_MAP_VAR_NAME)
            return f"({ch} {sym.RECV} {fr}) {sym.SEQ} ({termName(insExpr)})"

        for i, (_name, switch) in enumerate(model.Switches.items()):
            for du in switch.DirectUpdates:
                action = recvAndAppend if du.Append else recvAndReplace
                exprs.append(action(du.Channel, f'"{du.Policy}"', i))

        appExpr = MaudeEncoder.concatStr(
            MaudeEncoder.mapAccess(f"{_INDX_VAR_NAME}", _SW_MAP_VAR_NAME),
            MaudeEncoder.concatStr(f' " {sym.OR} " ', _FR_VAR_NAME),
        )
        insExpr = MaudeEncoder.mapInsert(
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
        return MaudeEncoder.recPolTerm(
            f"{_BIG_SW_VAR_NAME} {MaudeEncoder.convertIntoMap(sws)}"
        )

    def __buildElementTerms(self, model: jm.DNKNetwork) -> None:
        elId: int = 0
        elTerms: List[str] = []
        for net in [model]:
            link = net.Links if net.Links else sym.ZERO
            initialFTs = [
                sw.InitialFlowTable if sw.InitialFlowTable is not None else sym.ZERO
                for sw in net.Switches.values()
            ]
            mdata = ElementMetadata(
                elId,
                ElementType.SW,
                switchChannels=self._networkChannels[elId],
                link=link,
                initialFTs=initialFTs,
            )
            elTerms.append(self.__buildBigSwitchTerm(net))
            self.elsMetadata.append(mdata)
            elId += 1
        for name in model.Controllers.keys():
            elTerms.append(MaudeEncoder.recPolTerm(name))
            self.elsMetadata.append(ElementMetadata(elId, ElementType.CT))
            elId += 1
        self.elementTerms = elTerms

    def __addBranchCount(self, key: str, count: int) -> None:
        while key in self.branchCounts:
            key += "*"
        self.branchCounts[key] = count

    def getBranchCounts(self) -> str:
        bStrs: List[str] = [
            f"{key}:{count}" for (key, count) in self.branchCounts.items()
        ]
        return ";".join(bStrs)

    def getElementTerms(self) -> List[str]:
        return self.elementTerms

    def getElementsMetadata(self) -> List[ElementMetadata]:
        return self.elsMetadata

    def getStats(self) -> List[StatsEntry]:
        return [
            StatsEntry(
                "modelBranchCounts", "Network model branches", self.getBranchCounts()
            )
        ]
