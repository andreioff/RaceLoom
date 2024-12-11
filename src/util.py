import subprocess
import time
from enum import StrEnum


TMP_FILE_NAME = "_tmp"


class DyNetKATSymbols(StrEnum):
    ASSIGN = "<-"
    EQUAL = "="
    AND = "."
    OR = "+"
    STAR = "*"
    ZERO = "zero"
    ONE = "one"


def get_temp_file_path(dirPath: str, ext: str):
    """
    Returns a unique temporary file path with the given extension.
    @param ext: the extension of the file.
        Must not contain any dots or other special symbols.
    """

    currTimeMili = int(round(time.time() * 1000))
    return '{}/{}{}.{}'.format(dirPath, TMP_FILE_NAME, currTimeMili, ext)


def execute_cmd(cmd: list[str]) -> (str, str | None):
    '''Executes a given system command and returns the obtained output.'''
    proc = subprocess.run(cmd, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          shell=False)

    error = proc.stderr.decode('utf-8')
    return proc.stdout.decode('utf-8'), error if error != "" else None


def export_file(filePath: str, contents: str):
    '''Exports a file with the given name and contents.'''
    with open(filePath, "w") as f:
        f.write(contents)
