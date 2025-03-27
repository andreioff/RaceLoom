import os
import re
from typing import Tuple

from src.util import DyNetKATSymbols as sym
from src.util import executeCmd, exportFile, getTempFilePath

KATCH_FILE_EXT = "nkpl"
NKPL_LARROW = b"\xe2\x86\x90".decode("utf-8")  # ←
NKPL_STAR = b"\xe2\x8b\x86".decode("utf-8")  # ⋆
NKPL_FALSE = b"\xe2\x8a\xa5".decode("utf-8")  # ⊥
NKPL_TRUE = b"\xe2\x8a\xa4".decode("utf-8")  # ⊤
NKPL_AND = b"\xe2\x8b\x85".decode("utf-8")  # ⋅
NKPL_EQUIV = b"\xe2\x89\xa1".decode("utf-8")  # ≡
NKPL_NOT_EQUIV = b"\xe2\x89\xa2".decode("utf-8")  # ≢
NKPL_DIFF = b"\xe2\x88\x96".decode("utf-8")  # ∖ (this is not a normal backslash char)
NKPL_CHECK = "check"
NKPL_INOUTMAP = "inoutmap"
KATCH_TRUE = "True"
KATCH_FALSE = "False"


class KATchComm:
    """Class for running KATch as an OS command."""

    def __init__(self, tool_path: str, output_dir: str) -> None:
        self.tool_path: str = tool_path
        self.output_dir: str = output_dir

    def tool_format(self, netkatEncoding: str) -> str:
        """Converts the given NetKAT encoding into
        NKPL format (KATch's specification language)."""

        if netkatEncoding == "":
            netkatEncoding = sym.ZERO

        netkatEncoding = (
            netkatEncoding.replace(sym.ASSIGN, NKPL_LARROW)
            .replace(sym.STAR, NKPL_STAR)
            .replace(sym.ZERO, NKPL_FALSE)
            .replace(sym.ONE, NKPL_TRUE)
            .replace(sym.AND, NKPL_AND)
            .replace('"', "")
        )

        # Add a '@' before any packet field as required by NKPL,
        # assuming packet field names start with a letter or
        # underscore, and contain only alphanumeric characters and underscores.
        return re.sub(r"([a-zA-Z_]\w*)", r"@\1", netkatEncoding)

    def __runNPKLProgram(self, npklProgram: str) -> Tuple[str, str | None]:
        """
        Generates a file with the given NPKL program, passes it to
        KATch, and returns the result and an error, if any occured.
        """

        outfile = getTempFilePath(self.output_dir, KATCH_FILE_EXT)
        exportFile(outfile, npklProgram)

        cmd = [self.tool_path, "run", outfile]
        output, error = executeCmd(cmd)

        if os.path.exists(outfile):
            os.remove(outfile)

        return output, error

    def isNonEmptyDifference(self, nkEnc1: str, nkEnc2: str) -> Tuple[bool, str | None]:
        fmtNKEnc1 = self.tool_format(nkEnc1)
        fmtNKEnc2 = self.tool_format(nkEnc2)
        npklProgram = (
            f"{NKPL_CHECK} {fmtNKEnc1} {NKPL_DIFF} {fmtNKEnc2} "
            + f"{NKPL_NOT_EQUIV} {NKPL_FALSE}"
        )

        output, error = self.__runNPKLProgram(npklProgram)

        return self.__processCheckOpResult(output, error)

    def areNotEquiv(self, nkEnc1: str, nkEnc2: str) -> Tuple[bool, str | None]:
        fmtNKEnc1 = self.tool_format(nkEnc1)
        fmtNKEnc2 = self.tool_format(nkEnc2)
        npklProgram = f"{NKPL_CHECK} {fmtNKEnc1} {NKPL_NOT_EQUIV} {fmtNKEnc2}"

        output, error = self.__runNPKLProgram(npklProgram)
        return self.__processCheckOpResult(output, error)

    def __processCheckOpResult(
        self, output: str, error: str | None
    ) -> Tuple[bool, str | None]:
        if output.find("Check passed") > -1:
            return True, None
        if error is not None and error.find("Check failed") > -1:
            return False, None
        return False, error
