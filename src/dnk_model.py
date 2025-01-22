from typing import Self


class DNKModel:
    def fromJson(self, jsonStr: str) -> Self:
        return self

    def toMaudeModuleContent(self) -> str:
        return ""

    def getSwitchesMaudeMap(self) -> str:
        return "empty"

    def getControllersMaudeMap(self) -> str:
        return "empty"
