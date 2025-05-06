import os
import re
from enum import StrEnum
from typing import List, Tuple

from src.decorators.bool_cache import BoolCache, with_bool_cache
from src.decorators.exec_time import with_time_execution, ExecTimes
from src.stats import StatsEntry, StatsGenerator
from src.util import DyNetKATSymbols as sym
from src.util import executeCmd, exportFile, getTempFilePath

KATCH_FILE_EXT = "nkpl"
NKPL_LARROW = b"\xe2\x86\x90".decode()  # ←
NKPL_STAR = b"\xe2\x8b\x86".decode()  # ⋆
NKPL_FALSE = b"\xe2\x8a\xa5".decode()  # ⊥
NKPL_TRUE = b"\xe2\x8a\xa4".decode()  # ⊤
NKPL_AND = b"\xe2\x8b\x85".decode()  # ⋅
NKPL_EQUIV = b"\xe2\x89\xa1".decode()  # ≡
NKPL_NOT_EQUIV = b"\xe2\x89\xa2".decode()  # ≢
# the following character is not a regular backslash
NKPL_DIFF = b"\xe2\x88\x96".decode()  # ∖
NKPL_CHECK = "check"
NKPL_INOUTMAP = "inoutmap"
KATCH_TRUE = "True"
KATCH_FALSE = "False"


class _StatsKey(StrEnum):
    execTime = "katchExecTime"
    cacheHits = "katchCacheHits"
    cacheMisses = "katchCacheMisses"


class KATchError(Exception):
    pass


def _processCheckOpResult(output: str, error: str | None) -> bool:
    if output.find("Check passed") > -1:
        return True
    if error is not None and error.find("Check failed") > -1:
        return False
    raise KATchError(error)


def _toolFormat(netkatEncoding: str) -> str:
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


class KATchComm(ExecTimes, BoolCache, StatsGenerator):
    """Class for running KATch as an OS command."""

    def __init__(self, tool_path: str, output_dir: str) -> None:
        ExecTimes.__init__(self)
        BoolCache.__init__(self)
        self.tool_path: str = tool_path
        self.output_dir: str = output_dir

    def _runNPKLProgram(self, npklProgram: str) -> Tuple[str, str | None]:
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

    @with_time_execution
    @with_bool_cache
    def isNonEmptyDifference(self, nkEnc1: str, nkEnc2: str) -> bool:
        fmtNKEnc1 = _toolFormat(nkEnc1)
        fmtNKEnc2 = _toolFormat(nkEnc2)
        npklProgram = (
            f"{NKPL_CHECK} ({fmtNKEnc1}) {NKPL_DIFF} ({fmtNKEnc2}) "
            + f"{NKPL_NOT_EQUIV} {NKPL_FALSE}"
        )

        output, error = self._runNPKLProgram(npklProgram)

        return _processCheckOpResult(output, error)

    @with_time_execution
    @with_bool_cache
    def areNotEquiv(self, nkEnc1: str, nkEnc2: str) -> bool:
        fmtNKEnc1 = _toolFormat(nkEnc1)
        fmtNKEnc2 = _toolFormat(nkEnc2)
        npklProgram = f"{NKPL_CHECK} ({fmtNKEnc1}) {NKPL_NOT_EQUIV} ({fmtNKEnc2})"

        output, error = self._runNPKLProgram(npklProgram)

        return _processCheckOpResult(output, error)

    def getStats(self) -> List[StatsEntry]:
        return [
            StatsEntry(
                _StatsKey.execTime,
                "KATch total execution time",
                self.getTotalExecTime(),
            ),
            StatsEntry(
                _StatsKey.cacheHits, "KATch total cache hits", self.getTotalCacheHits()
            ),
            StatsEntry(
                _StatsKey.cacheMisses,
                "KATch total cache misses",
                self.getTotalCacheMisses(),
            ),
        ]
