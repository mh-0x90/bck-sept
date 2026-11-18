from abc import ABC, abstractmethod


class StageAction(ABC):
    @abstractmethod
    def execute(self, stage_record, repo):
        raise NotImplementedError
