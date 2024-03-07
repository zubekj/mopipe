import typing as t

import numpy as np
import pandas as pd
import scipy

from mopipe.core.common.util import int_or_str_slice
from mopipe.core.segments.inputs import AnySeriesInput, MultivariateSeriesInput, UnivariateSeriesInput
from mopipe.core.segments.outputs import SingleNumericValueOutput, UnivariateSeriesOutput, MultivariateSeriesOutput
from mopipe.core.segments.seg import Segment
from mopipe.core.segments.segmenttypes import SummaryType, AnalysisType


class Mean(SummaryType, AnySeriesInput, SingleNumericValueOutput, Segment):
    def process(self, x: t.Union[pd.Series, pd.DataFrame], **kwargs) -> float:  # noqa: ARG002
        if x.empty:
            return np.nan
        mean = np.nanmean(x)
        return float(mean)


class ColMeans(SummaryType, MultivariateSeriesInput, UnivariateSeriesOutput, Segment):
    def process(
        self, x: pd.DataFrame, col: t.Union[str, int, slice, None] = None, **kwargs  # noqa: ARG002
    ) -> pd.Series:
        slice_type = None
        if x.empty:
            return pd.Series()
        if isinstance(col, slice):
            slice_type = int_or_str_slice(col)
        if isinstance(col, int) or slice_type == int:
            return x.iloc(axis=1)[col].mean()
        if isinstance(col, str) or slice_type == str:
            return x.loc(axis=1)[col].mean()
        if col is None:
            return x.select_dtypes(include="number").mean()
        msg = f"Invalid col type {type(col)} provided, Must be None, int, str, or a slice."
        raise ValueError(msg)


def calc_RQA(x: np.array, y: np.array, dim: int = 1, tau: int = 1, threshold: float = 0.1, lmin: int = 2):
    embed_data_x, embed_data_y = [], []
    for i in range(dim):
        embed_data_x.append(x[i*tau:x.shape[0]-(dim-i-1)*tau])
        embed_data_y.append(y[i*tau:y.shape[0]-(dim-i-1)*tau])
    embed_data_x, embed_data_y = np.array(embed_data_x), np.array(embed_data_y)

    distance_matrix = scipy.spatial.distance_matrix(embed_data_x.T, embed_data_y.T)
    recurrence_matrix = distance_matrix < threshold
    msize = recurrence_matrix.shape[0]

    line_dist = np.zeros(msize+1)
    for i in range(-msize+1, msize):
        d = np.diagonal(recurrence_matrix, i)
        cline = 0
        for e in d:
            if e:
                cline += 1
            else:
                line_dist[cline] += 1
                cline = 0
        line_dist[cline] += 1

    rr = recurrence_matrix.mean()
    det = (line_dist[lmin:] * np.arange(msize+1)[lmin:]).sum() / recurrence_matrix.sum()

    return rr, det


class RQAStats(AnalysisType, UnivariateSeriesInput, MultivariateSeriesOutput, Segment):
    def process(
            self, x: pd.Series, dim: int = 1, tau: int = 1, threshold: float = 0.1, lmin: int = 2, **kwargs  # noqa: ARG005
    ) -> pd.DataFrame:
        out = pd.DataFrame(columns=["recurrence_rate", "determinism"])
        if x.empty:
            return out

        x = x.values
        rr, det = calc_RQA(x, x, dim, tau, threshold, lmin)
        out.loc[len(out)] = [rr, det]
        return out


class CrossRQAStats(AnalysisType, MultivariateSeriesInput, MultivariateSeriesOutput, Segment):
    def process(
            self, x: pd.DataFrame, colA: t.Union[str, int] = 0, colB: t.Union[str, int] = 0,
            dim: int = 1, tau: int = 1, threshold: float = 0.1, lmin: int = 2, **kwargs  # noqa: ARG007
    ) -> pd.DataFrame:
        out = pd.DataFrame(columns=["recurrence_rate", "determinism"])
        if x.empty:
            return out
        if isinstance(colA, int):
            xA = x.iloc[:, colA].values
        if isinstance(colA, str):
            xA = x.loc[:, colA].values
        if isinstance(colB, int):
            xB = x.iloc[:, colB].values
        if isinstance(colB, str):
            xB = x.loc[:, colB].values

        rr, det = calc_RQA(xA, xB, dim, tau, threshold, lmin)
        out.loc[len(out)] = [rr, det]
        return out
