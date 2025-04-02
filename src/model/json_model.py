from typing import List, Optional

from pydantic import BaseModel, field_validator
from pydantic.types import StringConstraints
from typing_extensions import Annotated

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
VarNameString = Annotated[str, StringConstraints(
    pattern=r"^[A-Za-z][A-Za-z0-9]*$")]


class DNKDirectUpdate(BaseModel):  # type: ignore
    Channel: VarNameString
    Policy: NonEmptyString
    Append: bool


class DNKRequestedUpdate(BaseModel):  # type: ignore
    RequestChannel: VarNameString
    RequestPolicy: NonEmptyString
    ResponseChannel: VarNameString
    ResponsePolicy: NonEmptyString


class DNKSwitch(BaseModel):  # type: ignore
    InitialFlowTable: Optional[NonEmptyString] = None
    DirectUpdates: List[DNKDirectUpdate]
    RequestedUpdates: List[DNKRequestedUpdate]


class DNKNetwork(BaseModel):  # type: ignore
    Switches: dict[VarNameString, DNKSwitch]
    Links: Optional[NonEmptyString] = None
    Controllers: dict[VarNameString, NonEmptyString]
    OtherChannels: Optional[List[VarNameString]] = []

    @field_validator("Switches", "Controllers")
    @classmethod
    def ensure_non_empty(
        cls, v: dict[VarNameString, NonEmptyString]
    ) -> dict[VarNameString, NonEmptyString]:
        if len(v) == 0:
            raise ValueError(
                "DyNetKAT Network must contain at least 1 switch and 1 controller"
            )
        return v
