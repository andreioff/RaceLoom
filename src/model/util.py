import re
from typing import List

import src.model.json_model as jm
from src.util import DyNetKATSymbols as sym


class NetKATReplacer:
    """Walks throw the given DNK Network JSON model and replaces all NetKAT policies
    with a string id of shape: "%i", where "i" is an index.

    The model passed as argument will be modified!

    Once created, an object of this class can also be used to transform
    ids back to policies.
    """

    def __init__(self, model: jm.DNKNetwork | None = None) -> None:
        if model is None:
            model = jm.DNKNetwork(
                Switches={"sw": jm.DNKSwitch(DirectUpdates=[], RequestedUpdates=[])},
                Controllers={"ct": sym.BOT},
            )
        self.policies: List[str] = []
        self.policyToId: dict[str, int] = {}
        self.model = model
        self._replace()

    def reset(self) -> None:
        self.policies = []
        self.policyToId = {}

    def _addPolicyAndReturnId(self, policy: str) -> str:
        index = self.policyToId.get(policy, None)
        if index is None:
            index = len(self.policies)
            self.policies.append(policy)
            self.policyToId[policy] = index
        return f"#{index}"

    def restore(self, s: str) -> str:
        regex = re.compile(r"#\d+")
        newS = s
        res = regex.search(newS)
        while res is not None:
            strId = newS[res.start() : res.end()]
            index = int(strId[1:])  # remove '#' prefix
            policy = self.policies[index]
            newS = newS[: res.start()] + policy + newS[res.end() :]
            res = regex.search(
                newS, res.start() + len(strId) + 1
            )  # skip the policy str
        return newS

    def _replace(self) -> None:
        self.reset()
        if self.model.Links is not None:
            self.model.Links = self._addPolicyAndReturnId(self.model.Links)
        self._replaceNetKATInSwitches()
        self._replaceNetKATInControllers()

    def _replaceNetKATInSwitches(self) -> None:
        for sw in self.model.Switches.values():
            if sw.InitialFlowTable is not None:
                sw.InitialFlowTable = self._addPolicyAndReturnId(sw.InitialFlowTable)
            for du in sw.DirectUpdates:
                du.Policy = self._addPolicyAndReturnId(du.Policy)

            for ru in sw.RequestedUpdates:
                ru.RequestPolicy = self._addPolicyAndReturnId(ru.RequestPolicy)
                ru.ResponsePolicy = self._addPolicyAndReturnId(ru.ResponsePolicy)

    def _replaceNetKATInControllers(self) -> None:
        regex = re.compile(r'"[^"]*"')
        for key, ct in self.model.Controllers.items():
            newCt = ct
            res = regex.search(newCt)
            while res is not None:
                # exclude double quotes " from the ends of the string
                policy = newCt[res.start() + 1 : res.end() - 1]
                strId = self._addPolicyAndReturnId(policy)
                newCt = (
                    newCt[: res.start() + 1]  # include '"' from the start of the string
                    + strId
                    + newCt[res.end() - 1 :]
                )  # include '"' from the start of the string
                res = regex.search(
                    newCt, res.start() + len(strId) + 2
                )  # skip the id str
            self.model.Controllers[key] = newCt
