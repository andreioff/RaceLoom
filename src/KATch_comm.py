import os
import re
import string
from typing import Tuple

from pydantic import ValidationError

from src.packet import NetKATSymbolicPacket, PacketList
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

    def processPktMappingOutput(self, output: str) -> Tuple[str, str | None]:
        """Parses the output obtained from KATch."""
        # Matches strings of the form:
        # Inoutmap at <path> <text until end of line>
        res = re.search(r"Inoutmap at ([^[ ]*) ([^\n]*)", output)
        if res is None:
            return "", "KATchComm: Could not match packet mapping output."

        jsonRes = str(res.group(2))  # type: ignore
        # remove whitespaces
        jsonRes = jsonRes.translate(str.maketrans("", "", string.whitespace))

        # drop all packets by default
        if jsonRes == "":
            return sym.ZERO, None

        # KATch may reduce a given network to True or False, which corresponds
        # to forwarding and dropping all packets, respectively.
        if jsonRes == f'[["{KATCH_TRUE}"]]':
            return sym.ONE, None
        if jsonRes == f'[["{KATCH_FALSE}"]]':
            return sym.ZERO, None

        return self.__processJSONPackets(f'{{"packets": {jsonRes}}}')

    def __processJSONPackets(self, jsonRes: str) -> Tuple[str, str | None]:
        """Takes a JSON object of the form
        {"packets": <list of lists of packet fields>}, converts it into
        DyNetKAT symbolic packet expressions in Head-Normal Form, and joins
        them together using the NetKAT OR symbol.
        Returns a tuple of the resulting expression and an error if the operation
        is unsuccessful, or None otherwise."""
        try:
            res = PacketList.model_validate_json(jsonRes)

            hnfPackets: list[str] = []
            for jsonP in res.packets:
                p = NetKATSymbolicPacket().fromJsonPacket(jsonP)
                hnfPackets.append(f'"{p.toString()}"')

            if len(hnfPackets) == 0:
                return sym.ZERO, None
            return f" {sym.OR_ALT} ".join(hnfPackets), None

        except ValidationError as e:
            return "", f"KATchComm: Invalid JSON!\n{e}"

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

    def getPktInPktOutMapping(self, netkatEncoding: str) -> Tuple[str, str | None]:
        fmtNKEnc = self.tool_format(netkatEncoding)
        # use the custom 'inoutmap' NKPL instruction to generate the packet-in
        # packet-out mapping of the given network
        npklProgram = f"{NKPL_INOUTMAP}  {fmtNKEnc}"

        output, error = self.__runNPKLProgram(npklProgram)
        if error is not None:
            return "", error

        output, error = self.processPktMappingOutput(output)

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
