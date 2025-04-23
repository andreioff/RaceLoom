from dataclasses import dataclass


@dataclass
class TracerConfig:
    outputDirPath: str
    katchPath: str
    maudeFilesDirPath: str
    threads: int
    verbose: bool
    inputFileName: str
