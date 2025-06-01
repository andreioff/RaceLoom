from pydantic import BaseModel, field_validator
from pydantic.types import StringConstraints
from typing_extensions import Annotated

from src.analyzer.harmful_trace import RaceType
from src.KATch_comm import NKPL_EQUIV, NKPL_FALSE, NKPL_NOT_EQUIV

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class SafetyProperty(BaseModel):  # type: ignore
    Expression: NonEmptyString
    MustBe: bool


class SafetyProperties(BaseModel):  # type: ignore
    Properties: dict[RaceType, SafetyProperty]

    @field_validator("Properties")
    @classmethod
    def only_allowed_race_types(
        cls, v: dict[RaceType, SafetyProperty]
    ) -> dict[RaceType, SafetyProperty]:
        allowedRaceTypes = [RaceType.CT_SW, RaceType.CT_SW_CT, RaceType.CT_CT_SW]
        for key in v.keys():
            if key not in allowedRaceTypes:
                raceTypesStr = ", ".join(allowedRaceTypes)
                raise ValueError(
                    f"Unknown race type: '{key}'. Safety properties can only be "
                    + f"specified for the following race types: {raceTypesStr}."
                )
        return v

    def convertToNetKAT(self) -> dict[RaceType, str]:
        spDict: dict[RaceType, str] = {}
        for raceType, sp in self.Properties.items():
            rightSide = f"{NKPL_NOT_EQUIV} {NKPL_FALSE}"
            if sp.MustBe is False:
                rightSide = f"{NKPL_EQUIV} {NKPL_FALSE}"
            spDict[raceType] = f"{sp.Expression} {rightSide}"
        return spDict
