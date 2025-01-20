from typing import List, Self

from pydantic import BaseModel, ValidationError

from src.util import DyNetKATSymbols as sym

WILD_CARD = "?"  # matches any value a packet field can take


class PacketField(BaseModel):  # type: ignore
    field: str
    newValue: str
    oldValue: str


class PacketList(BaseModel):  # type: ignore
    packets: List[List[PacketField]]


class NetKATSymbolicPacket:
    def __init__(self) -> None:
        self.completeTest: list[str] = []
        self.completeAssign: list[str] = []

    def toString(self) -> str:
        return sym.AND.join(self.completeTest + self.completeAssign)

    def fromJsonPacket(self, pktFieldList: List[PacketField]) -> Self:
        """Takes a list of PacketField objects and converts it
        into an object of this class.
        Returns an object of this class.
        Raises pydantic.ValidationError if the 'newValue' and 'oldValue'
        attributes of the list objects are not integers or wild card."""

        for pktField in pktFieldList:
            if not self.__hasExpectedValues(pktField):
                raise ValidationError(
                    "JSON packet field doesn't contain the expected value pairs!", []
                )
            self.__processField(pktField)
        return self

    def __hasExpectedValues(self, pcktField: PacketField) -> bool:
        for value in [pcktField.oldValue, pcktField.newValue]:
            if value == WILD_CARD:
                continue

            try:
                int(value)
            except (TypeError, ValueError):
                return False

        return True

    def __processField(self, pktField: PacketField) -> None:
        if pktField.oldValue != WILD_CARD:
            self.completeTest.append(f"{pktField.field}{sym.EQUAL}{pktField.oldValue}")
        if pktField.newValue != WILD_CARD:
            self.completeAssign.append(
                f"{pktField.field}{sym.ASSIGN}{pktField.newValue}"
            )
