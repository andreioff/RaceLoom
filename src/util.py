import os
import subprocess
import time
from enum import StrEnum
from typing import List, Tuple

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
    return os.path.join(dirPath, "{}{}.{}".format(TMP_FILE_NAME, currTimeMili, ext))


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


def removeFile(filePath: str) -> None:
    """Removes the file at the given path if it exists."""
    if os.path.exists(filePath):
        os.remove(filePath)


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


def isExe(fpath: str) -> bool:
    """Takes a file path and checks if the file is an executable."""
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


def createDir(dirPath: str) -> None:
    if os.path.exists(dirPath):
        return
    os.mkdir(dirPath)


def getFileName(filePath: str) -> str:
    fileName = os.path.basename(filePath)
    return fileName.split(".")[0]


def splitIntoLines(s: str, lineSize: int, charMargin: int = 0) -> str:
    """Inserts new line characters in the given string every 'lineSize' chars.
    If a character margin is given, the string remains unchanged if its length
    is <= lineSize + charMargin."""
    if lineSize < 1 or lineSize + charMargin > len(s):
        return s
    return os.linesep.join([s[i : i + lineSize] for i in range(0, len(s), lineSize)])


def uniformSplit[T](li: List[T], parts: int) -> List[List[T]]:
    if parts == 0:
        return [li]
    if len(li) == 0:
        return []
    parts = len(li) if parts > len(li) else parts
    sublistSize = len(li) // parts
    splitList: List[List[T]] = []
    start, end = 0, sublistSize
    while len(splitList) < parts and end <= len(li):
        splitList.append(li[start:end])
        start = end
        end += sublistSize
    for j in range(len(li) % parts):
        splitList[j].append(li[start + j])
    return splitList


def indexInBounds(index: int, arrayLength: int) -> bool:
    return 0 <= index and index < arrayLength
