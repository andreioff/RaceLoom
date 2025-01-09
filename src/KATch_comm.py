import json
import os
import re
from typing import Tuple

from src.packet import Packet
from src.util import DyNetKATSymbols as sym
from src.util import execute_cmd, export_file, get_temp_file_path

KATCH_FILE_EXT = "nkpl"
NKPL_LARROW = b"\xe2\x86\x90".decode("utf-8")  # ←
NKPL_STAR = b"\xe2\x8b\x86".decode("utf-8")  # ⋆
NKPL_FALSE = b"\xe2\x8a\xa5".decode("utf-8")  # ⊥
NKPL_TRUE = b"\xe2\x8a\xa4".decode("utf-8")  # ⊤
NKPL_AND = b"\xe2\x8b\x85".decode("utf-8")  # ⋅
KATCH_TRUE = "True"
KATCH_FALSE = "False"


class KATchComm:
    """Class for running KATch as an OS command."""

    def __init__(self, tool_path: str, output_dir: str) -> None:
        self.tool_path: str = tool_path
        self.output_dir: str = output_dir

    def process_output(self, output: str) -> Tuple[str, str | None]:
        """Parses the output obtained from KATch."""
        # Matches strings of the form:
        # Inoutmap at <path> <text until end of line>
        res = re.search(r"Inoutmap at ([^[ ]*) ([^\n]*)", output)
        if res is None:
            return "", "KATchComm: Could not match packet mapping output."

        jsonRes = json.loads(res.group(2))
        if not isinstance(jsonRes, list):
            return "", "KATchComm: Matched output is not a JSON list!"
        return self.__processJSONPackets(jsonRes)

    def __processJSONPackets(self, jsonRes: list) -> Tuple[str, str | None]:
        """Takes a list of packets as JSON objects, converts them
        into DyNetKAT expressions in Head-Normal Form, and joins
        them together using the DyNetKAT OR symbol.
        Returns the resulting expression and an error if the operation
        is unsuccessful, or None otherwise."""
        # drop all packets by default
        if len(jsonRes) == 0:
            return sym.ZERO, None

        # KATch may reduce a given network to True or False, which corresponds
        # to forwarding and dropping all packets, respectively.
        if len(jsonRes) == 1 and isinstance(jsonRes[0], list):
            if jsonRes[0] == [KATCH_TRUE]:
                return sym.ONE, None
            if jsonRes[0] == [KATCH_FALSE]:
                return sym.ZERO, None

        hnfPackets: list[str] = []
        for jsonP in jsonRes:
            p, err = Packet().fromJson(jsonP)
            if err is not None:
                return "", "KATchComm: " + err
            hnfPackets.append(f'"{p.toString()}"')
        return f" {sym.OR_ALT} ".join(hnfPackets), None

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
        netkatEncoding = re.sub(r"([a-zA-Z_]\w*)", r"@\1", netkatEncoding)

        # use the custom 'inoutmap' NKPL instruction to generate the packet-in
        # packet-out mapping of the given network
        npklProgram = "inoutmap " + netkatEncoding

        return npklProgram

    def execute(self, netkatEncoding: str) -> Tuple[str, str | None]:
        """
        Generates a file with an NPKL program, passes it to
        KATch, parses the obtained result, and returns it.
        """

        outfile = get_temp_file_path(self.output_dir, KATCH_FILE_EXT)
        npklProgram = self.tool_format(netkatEncoding)
        export_file(outfile, npklProgram)

        cmd = [self.tool_path, "run", outfile]
        output, error = execute_cmd(cmd)
        if error is not None:
            return output, error

        output, error = self.process_output(output)

        if os.path.exists(outfile):
            os.remove(outfile)

        return output, error
