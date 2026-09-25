from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelRequest:
    task: str
    context: str
    response_contract: str = "single_file"


@dataclass
class ModelResponse:
    content: str
    model: str


class FixSimpleModel(ABC):
    """
    FixSimple-owned model boundary.

    Builder logic depends only on this interface.
    Local or remote inference backends are replaceable adapters.
    """

    @abstractmethod
    def complete(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError
