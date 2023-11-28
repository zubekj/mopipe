"""reader.py

This module contains the default Reader classes, including the
AbstractReader base class which can be used for creating new
readers.
"""

import typing as t
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from mopipe.common import DataLevel, MocapMetadata
from mopipe.common.qtm import parse_metadata_row


class AbstractReader(ABC):
    """AbstractReader

    Abstract base class for all Readers. Readers are used to read
    data from a source and return it in a pandas dataframe.
    """

    @property
    @abstractmethod
    def _allowed_extensions(self) -> list[str]:
        """The allowed extensions for the source."""
        return []

    @abstractmethod
    def __init__(
        self,
        source: t.Union[str, Path, pd.DataFrame],
        name: str,
        sample_rate: t.Optional[float] = None,
        level: t.Optional[DataLevel] = None,
        **kwargs,
    ):
        """Initialize the AbstractReader.

        Parameters
        ----------
        source : Path or DataFrame
            The source of the data to be read.
        name : str
            The name of the data/experiment to be read.
        sample_rate : float, optional
            The sample rate of the data to be read.
        level : DataLevel, optional
            The level of the data to be read.
        """
        if isinstance(source, str):
            source = Path(source)
        self._source = source
        self._name = name
        self._sample_rate = sample_rate
        self._level = level
        self._metadata: dict[str, t.Any] = {}

    @property
    def source(self) -> t.Union[Path, pd.DataFrame]:
        """The source of the data to be read."""
        return self._source

    @property
    def sample_rate(self) -> t.Optional[float]:
        """The sample rate of the data to be read."""
        return self._sample_rate

    @property
    def allowed_extensions(self) -> list[str]:
        """The allowed extensions for the source."""
        return self._allowed_extensions

    @property
    def metadata(self) -> dict[str, t.Any]:
        """The metadata for the data to be read."""
        return self._metadata

    @property
    def name(self) -> str:
        """The name of the data/experiment to be read."""
        return self._name

    @property
    def level(self) -> t.Optional[DataLevel]:
        """The level of the data to be read."""
        return self._level

    @abstractmethod
    def read(self) -> t.Optional[pd.DataFrame]:
        """Read the data from the source and return it as a dataframe."""
        if isinstance(self.source, pd.DataFrame):
            return self.source
        return None


class MocapReader(AbstractReader):
    """MocapReader

    The MocapReader class is used to read motion capture data from
    a source and return it as a pandas dataframe.
    """

    _start_line: int = 0
    _allowed_extensions: t.Final[list[str]] = [".tsv"]

    def __init__(
        self,
        source: t.Union[Path, pd.DataFrame],
        name: str,
        sample_rate: t.Optional[float] = None,
        level: t.Optional[DataLevel] = None,
        **kwargs,
    ):
        """Initialize the MocapReader.

        Parameters
        ----------
        source : Path or DataFrame
            The source of the data to be read.
        name : str
            The name of the data/experiment to be read.
        sample_rate : float, optional
            The sample rate of the data to be read.
        level : DataLevel, optional
            The level of the data to be read.
        """
        super().__init__(source, name, sample_rate, level, **kwargs)
        if not isinstance(self.source, pd.DataFrame):
            self._extract_metadata()

    def _parse_metadata_row(self, key: str, values: list[t.Any]) -> None:
        """Parse a metadata row and return the key and value.

        Parameters
        ----------
        key : str
            The key of the metadata row.
        values : List[Any]
            The values of the metadata row.
        """
        k, v = parse_metadata_row(key, values)
        self._metadata[k] = v

    def _extract_metadata_from_file(self, path: Path) -> None:
        """Extract the metadata from a file and return it as a dict.

        Parameters
        ----------
        path : Path
            The path to the file to extract the metadata from.
        """
        # open file
        line_number = 0
        with open(path) as file:
            # read the first line
            line = file.readline()
            # initialize the metadata dict

            # loop until the end of the file
            while line:
                # split the line into key and value
                line = line.strip()
                if not line:
                    line_number += 1
                    continue
                items = line.split("\t")
                key = items[0]
                values = items[1:]
                # if the key is a float
                # we have reached the end of the metadata
                try:
                    float(key)
                    break
                except ValueError:
                    pass
                line_number += 1
                # add the key and value to the metadata dict
                self._parse_metadata_row(key, values)
                # read the next line
                line = file.readline()
        if MocapMetadata.sample_rate not in self._metadata:
            err = f"Sample rate not found in {path}."
            raise ValueError(err)
        self._start_line = line_number

    def _extract_metadata(self) -> None:
        """Extract the metadata from the source and return it as a dict."""

        if isinstance(self.source, Path):
            self._extract_metadata_from_file(self.source)
            return
        err = f"Metadata from {type(self.source)} is not implemented."
        raise NotImplementedError(err)

    def _read_qtm_tsv(self) -> pd.DataFrame:
        """Read the data from a QTM .tsv file and return it as a dataframe.

        Returns
        -------
        DataFrame
            The data read from the source.
        """
        if not isinstance(self.source, Path):
            err = "The source must be a Path when reading from a QTM .tsv file."
            raise ValueError(err)
        df = pd.read_csv(
            self.source,
            sep="\t",
            skiprows=self._start_line,
            header=None,
        )
        # rename the columns to the marker labels
        cols: list[str] = ["frame", "elapsed"]
        m: str
        for m in self.metadata[str(MocapMetadata.marker_names)]:
            cols = [*cols, f"{m}_x", f"{m}_y", f"{m}_z"]
        df = df.set_axis(cols, axis="columns", copy=False)

        # set the index to the frame number
        df.set_index("frame", inplace=True)
        return df

    def read(self) -> pd.DataFrame:
        """Read the data from the source and return it as a dataframe.

        Returns
        -------
        DataFrame
            The data read from the source.
        """
        data = super().read()
        if data is not None:
            return data

        if isinstance(self.source, Path):
            if self.source.suffix not in self._allowed_extensions:
                err = f"Invalid file extension: {self.source.suffix}."
                err += f" Allowed extensions are: {self._allowed_extensions}"
                raise ValueError(err)
            return self._read_qtm_tsv()
        err = f"Reading from {type(self.source)} is not yet implemented."
        raise NotImplementedError(err)
