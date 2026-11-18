from abc import ABC, abstractmethod

from .action import StageAction
from .common import display_fields


class StageFlow(ABC):
    STAGE_TITLES = ()
    STAGE_FIELDS = ()

    def __init__(self, start_stage, end_stage):
        if not isinstance(start_stage, StageAction) or not isinstance(end_stage, StageAction):
            raise TypeError("Stage actions must implement StageAction")
        self.start_stage = start_stage
        self.end_stage = end_stage

    def run_stage(self, stage, record, repo):
        if stage not in range(1, 9):
            raise ValueError("Stage is not available for navigation")
        return getattr(self, f"stage_{stage}")(record, repo)

    def view_fields(self, record):
        return display_fields(record["payload"], self.STAGE_FIELDS[record["stage"] - 1])

    def stage_1(self, record_1, repo):
        return self.start_stage.execute(record_1, repo)

    @abstractmethod
    def stage_2(self, record_2, repo):
        raise NotImplementedError

    @abstractmethod
    def stage_3(self, record_3, repo):
        raise NotImplementedError

    @abstractmethod
    def stage_4(self, record_4, repo):
        raise NotImplementedError

    @abstractmethod
    def stage_5(self, record_5, repo):
        raise NotImplementedError

    @abstractmethod
    def stage_6(self, record_6, repo):
        raise NotImplementedError

    @abstractmethod
    def stage_7(self, record_7, repo):
        raise NotImplementedError

    @abstractmethod
    def stage_8(self, record_8, repo):
        raise NotImplementedError

    @abstractmethod
    def stage_9(self, record_9, repo):
        raise NotImplementedError

    def stage_10(self, record_10, repo):
        return self.end_stage.execute(record_10, repo)
