"""seg.py

Base segment class for all pipeline steps.
"""

import typing as t
from abc import ABCMeta, abstractmethod
from uuid import uuid4

from mopipe.segments.io import IOType
from mopipe.segments.segmenttypes import SegmentType


class SegmentMeta(ABCMeta):
    def __new__(cls, name, bases, dct):
        # Add a class variable _segment_type to each class that uses this metaclass
        dct["_segment_type"] = dct.get("_segment_type", None)
        # Add a class variable _input_type to each class that uses this metaclass
        dct["_input_type"] = dct.get("_input_type", None)
        # Add a class variable _output_type to each class that uses this metaclass
        dct["_output_type"] = dct.get("_output_type", None)
        return super().__new__(cls, name, bases, dct)


class Segment(metaclass=SegmentMeta):
    """Base class for all pipeline steps."""

    _name: str
    _segment_id: str

    def __init__(self, name: str, segment_id: t.Optional[str] = None) -> None:
        """Initialize a Segment."""
        self._name = name
        self._segment_id = name + str(uuid4()) if segment_id is None else segment_id

    @property
    def name(self) -> str:
        """The name of the segment."""
        return self._name

    @property
    def segment_id(self) -> str:
        """The id of the segment."""
        return self._segment_id

    @abstractmethod
    def validate_input(self, *args, **kwargs) -> bool:
        """Validate the input."""
        raise NotImplementedError

    @abstractmethod
    def process(self, *args, **kwargs) -> t.Any:
        """Process the inputs and return the output."""
        raise NotImplementedError

    @property
    @abstractmethod
    def input_type(self) -> IOType:
        """The type of the input."""
        raise NotImplementedError

    @property
    @abstractmethod
    def output_type(self) -> IOType:
        """The type of the output."""
        raise NotImplementedError

    @property
    @abstractmethod
    def segment_type(self) -> SegmentType:
        """The type of the segment."""
        raise NotImplementedError

    def __call__(self, *args, **kwargs) -> t.Any:
        """Process the inputs and return the output."""
        if not self.validate_input(*args, **kwargs):
            msg = f"Invalid input for {self.name} segment."
            raise ValueError(msg)
        return self.process(*args, **kwargs)
