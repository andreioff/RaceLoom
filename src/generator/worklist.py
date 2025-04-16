from abc import ABC, abstractmethod
from collections import deque
from typing import List


class WorkList[T](ABC):
    @abstractmethod
    def pop(self) -> T: ...

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def append(self, el: T) -> None: ...

    @abstractmethod
    def isEmpty(self) -> bool: ...


class Stack[T](WorkList[T]):
    def __init__(self) -> None:
        self.stack: List[T] = []

    def pop(self) -> T:
        return self.stack.pop()

    def reset(self) -> None:
        self.stack = []

    def append(self, el: T) -> None:
        self.stack.append(el)

    def isEmpty(self) -> bool:
        return not self.stack


class Queue[T](WorkList[T]):
    def __init__(self) -> None:
        self.deq: deque[T] = deque()

    def pop(self) -> T:
        return self.deq.popleft()

    def reset(self) -> None:
        self.deq = deque()

    def append(self, el: T) -> None:
        self.deq.append(el)

    def isEmpty(self) -> bool:
        return not self.deq
