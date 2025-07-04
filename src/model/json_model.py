from typing import List, Optional, Self

from pydantic import BaseModel, field_validator, model_validator
from pydantic.types import StringConstraints
from pydantic_core import PydanticCustomError
from typing_extensions import Annotated

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
VarNameString = Annotated[str, StringConstraints(pattern=r"^[A-Za-z](-?[A-Za-z0-9])*$")]


class DNKDirectUpdate(BaseModel):  # type: ignore
    Channel: VarNameString
    Policy: NonEmptyString


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
    RecursiveVariables: dict[VarNameString, NonEmptyString]
    Controllers: List[VarNameString]
    OtherChannels: Optional[List[VarNameString]] = []

    @field_validator("Switches", "Controllers")
    @classmethod
    def ensureNonEmpty(
        cls, v: List[VarNameString] | dict[VarNameString, DNKSwitch]
    ) -> List[VarNameString] | dict[VarNameString, DNKSwitch]:
        if len(v) == 0:
            raise PydanticCustomError(
                "Missing switch or controller",
                "DyNetKAT Network must contain at least 1 switch and 1 controller",
            )
        return v

    @model_validator(mode="after")
    def _switchChannelsAreUnique(self) -> Self:
        """Raises PydanticCustomError if the switches across all networks in the given
        JSON model do not use unique channels"""

        def raiseError(channel: str, swName: str) -> None:
            raise PydanticCustomError(
                "Re-used switch channel",
                f"Channel '{channel}' cannot be re-used for switch '{swName}'. "
                + "A channel name used to receive updates for "
                + "a switch in a network cannot be re-used for any other switch.",
            )

        channels: dict[str, bool] = {}

        for name, sw in self.Switches.items():
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
        return self

    @model_validator(mode="after")
    def _controllerVariablesAreDeclared(self) -> Self:
        """Raises PydanticCustomError if the variables used as controllers
        are not declared"""
        for varName in self.Controllers:
            if varName not in self.RecursiveVariables:
                raise PydanticCustomError(
                    "Undeclared controller variable",
                    f"Recursive variable '{varName}' used as controller "
                    + "is not defined!",
                )
        return self
