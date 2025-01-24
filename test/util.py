import inspect
import os
import test.src

import src
from src.dnk_model import DNKModel

PROJECT_DIR = os.path.dirname(inspect.getabsfile(src))
TEST_DIR = os.path.dirname(inspect.getabsfile(test.src))


class DNKTestModel(DNKModel):
    def __init__(
        self, maudeModuleContent: str, bigSwitch: str, controllersMaudeMap: str
    ):
        super().__init__()
        self.maudeModuleContent = maudeModuleContent
        self.bigSwitch = bigSwitch
        self.controllersMaudeMap = controllersMaudeMap

    def toMaudeModuleContent(self) -> str:
        return self.maudeModuleContent

    def getBigSwitchTerm(self) -> str:
        return self.bigSwitch

    def getControllersMaudeMap(self) -> str:
        return self.controllersMaudeMap
