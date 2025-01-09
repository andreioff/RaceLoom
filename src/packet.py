from typing import Any, Self

from src.util import DyNetKATSymbols as sym

KEY_FIELD = "field"
KEY_OLD_VALUE = "oldValue"
KEY_NEW_VALUE = "newValue"
WILD_CARD = "?"  # matches any value a packet field can take


class Packet:
    def __init__(self) -> None:
        self.completeTest: list[str] = []
        self.completeAssign: list[str] = []

    def toString(self) -> str:
        return sym.AND.join(self.completeTest + self.completeAssign)

    def fromJson(self, json: Any) -> (Self, str | None):
        """Takes a JSON object of the form [{key: value, ...}, ...]
        and converts it into an object of this class.
        Returns an object of this class and an error string if the provided
        JSON is invalid, or None otherwise."""

        if not isinstance(json, list):
            return self, "JSON object is not a list"
        for pktField in json:
            if not (
                isinstance(pktField, dict) and self.__hasExpectedJSONPairs(pktField)
            ):
                return (
                    self,
                    "JSON packet field is not a dictionary or "
                    + "doesn't contain the expected key-value pairs!",
                )
            self.__processField(pktField)
        return self, None

    def __hasExpectedJSONPairs(self, pcktField: dict) -> bool:
        for key in [KEY_FIELD, KEY_OLD_VALUE, KEY_NEW_VALUE]:
            if key not in pcktField:
                return False

        for key in [KEY_OLD_VALUE, KEY_NEW_VALUE]:
            try:
                int(pcktField[key])
            except (TypeError, ValueError):
                return False

        return True

    def __processField(self, pcktField: dict) -> bool:
        field = pcktField[KEY_FIELD]
        oldVal = pcktField[KEY_OLD_VALUE]
        newVal = pcktField[KEY_NEW_VALUE]
        if oldVal != WILD_CARD:
            self.completeTest.append(f"{field}{sym.EQUAL}{oldVal}")
        if newVal != WILD_CARD:
            self.completeAssign.append(f"{field}{sym.ASSIGN}{newVal}")
