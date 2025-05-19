import inspect
import os
import test.src
from typing import List, Self

import src
from src.maude_encoder import MaudeModules as mm
from src.model.dnk_maude_model import (DNKMaudeModel, ElementMetadata,
                                       ElementType)

PROJECT_DIR = os.path.dirname(inspect.getabsfile(src))
TEST_DIR = os.path.dirname(inspect.getabsfile(test.src))
KATCH_PATH = os.path.join(PROJECT_DIR, "..", "bin", "katch", "katch")


class DNKTestModel(DNKMaudeModel):
    def __init__(self, maudeModuleContent: str, parallelExpr: str):
        """Initializes a DNKModel object from a Maude module content
        and an expression of shape 'T1 || T2 || ...'. Considers any term in
        the expression to be a switch if it contains 'SW' in its name"""
        super().__init__()
        self.maudeModuleContent = maudeModuleContent
        self.elementTerms: List[str] = []
        self.elMetadata: List[ElementMetadata] = []

        for i, term in enumerate(parallelExpr.split("||")):
            self.elementTerms.append(term.strip())
            if "SW" in term:
                self.elMetadata.append(ElementMetadata(i, ElementType.SW))
                continue
            self.elMetadata.append(ElementMetadata(i, ElementType.CT))

    @classmethod
    def fromJson(cls, jsonStr: str) -> Self:
        raise Exception("Not implemented")

    def toMaudeModule(self) -> str:
        return f"""
            fmod {mm.DNK_MODEL} is
            protecting {mm.DNK_MODEL_UTIL} .
            {self.maudeModuleContent}
            endfm
        """

    def getElementTerms(self) -> List[str]:
        return self.elementTerms

    def getBranchCounts(self) -> str:
        return "unknown"

    def getElementsMetadata(self) -> List[ElementMetadata]:
        return self.elMetadata

    @classmethod
    def fromDebugMaudeFile(cls, fileContent: str) -> DNKMaudeModel:
        # Only for debugging purposes
        fileContentLines = fileContent.split("\n")
        maudeStr = "\n".join(fileContentLines[:-2])
        elsMap = fileContentLines[-2]
        return cls(maudeStr, elsMap)
