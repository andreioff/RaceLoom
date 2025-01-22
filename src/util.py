import os
import subprocess
import time
from enum import StrEnum
from typing import Tuple

TMP_FILE_NAME = "_tmp"


class DyNetKATSymbols(StrEnum):
    ASSIGN = "<-"
    EQUAL = "="
    AND = "."
    OR = "+"
    OR_ALT = "n+"  # netkat or alternative
    STAR = "*"
    ZERO = "zero"
    ONE = "one"
    SEQ = ";"
    RECV = "?"
    SEND = "!"
    OPLUS = "o+"


def getTempFilePath(dirPath: str, ext: str) -> str:
    """
    Returns a unique temporary file path with the given extension.
    @param ext: the extension of the file.
        Must not contain any dots or other special symbols.
    """

    currTimeMili = int(round(time.time() * 1000))
    return "{}/{}{}.{}".format(dirPath, TMP_FILE_NAME, currTimeMili, ext)


def executeCmd(cmd: list[str]) -> Tuple[str, str | None]:
    """Executes a given system command and returns the obtained output."""
    proc = subprocess.run(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )

    error = proc.stderr.decode("utf-8")
    return proc.stdout.decode("utf-8"), error if error != "" else None


def exportFile(filePath: str, contents: str) -> None:
    """Exports a file with the given name and contents."""
    with open(filePath, "w") as f:
        f.write(contents)


def readFile(filePath: str) -> str:
    """
    Reads the file at the given path and returns its contents as string
    Raises: FileNotFoundError if the given path does not point to any valid file"""
    file = open(filePath, "r")
    content = file.read()
    file.close()

    return content


def isJson(fpath: str) -> bool:
    """Takes a file path and checks if the file is in .json format."""
    return len(fpath) > 5 and fpath[-5:] == ".json"


def isExe(fpath: str) -> bool:
    """Takes a file path and checks if the file is an executable."""
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


def createDir(dirPath: str) -> None:
    if os.path.exists(dirPath):
        return
    os.mkdir(dirPath)
