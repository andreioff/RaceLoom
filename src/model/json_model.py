from typing import List, Optional

from pydantic import BaseModel, field_validator
from pydantic.types import StringConstraints
from pydantic_core import PydanticCustomError
from typing_extensions import Annotated

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
VarNameString = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9]*$")]


class DNKDirectUpdate(BaseModel):  # type: ignore
    Channel: VarNameString
    Policy: NonEmptyString
    Append: bool


class DNKRequestedUpdate(BaseModel):  # type: ignore
    RequestChannel: VarNameString
    RequestPolicy: NonEmptyString
    ResponseChannel: VarNameString
    ResponsePolicy: NonEmptyString
    Append: bool


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
        cls, v: dict[VarNameString, NonEmptyString] | dict[VarNameString, DNKSwitch]
    ) -> dict[VarNameString, NonEmptyString] | dict[VarNameString, DNKSwitch]:
        if len(v) == 0:
            raise ValueError(
                "DyNetKAT Network must contain at least 1 switch and 1 controller"
            )
        return v


def validateSwitchChannels(model: DNKNetwork) -> None:
    """Raises ValidationError if the switches across all networks in the given
    JSON model do not use unique channels"""

    def raiseError(channel: str, swName: str) -> None:
        raise PydanticCustomError(
            "Re-used switch channel",
            f"Channel '{channel}' cannot be re-used for switch '{swName}'. "
            + "A channel name used to receive updates for "
            + "a switch in a network cannot be re-used for any other switch.",
        )

    channels: dict[str, bool] = {}

    for name, sw in model.Switches.items():
        swChannels: dict[str, bool] = {}
        for du in sw.DirectUpdates:
            if du.Channel in channels:
                raiseError(du.Channel, name)
            swChannels[du.Channel] = True
        for ru in sw.RequestedUpdates:
            if ru.RequestChannel in channels:
                raiseError(ru.RequestChannel, name)
            if ru.ResponseChannel in channels:
                raiseError(ru.ResponseChannel, name)
            swChannels[ru.RequestChannel] = True
            swChannels[ru.ResponseChannel] = True
        channels.update(swChannels)
