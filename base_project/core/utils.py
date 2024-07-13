"""Utility module.

Commonly used functions and classes are here.
"""

from itertools import starmap
from datetime import datetime

import numpy as np
import tabulate
from dask import delayed, compute


tprint = lambda dic: print(
    tabulate(dic, headers="keys", tablefmt="psql")
)  # print with fancy 'psql' format
vars_ = lambda obj: {k: v for k, v in vars(obj).items() if not k.startswith("__")}
str2dt = lambda s, format="%Y-%m-%d": datetime.datetime.strptime(s, format)
dt2str = lambda dt, format="%Y-%m-%d": dt.strftime(format)


def lmap(fn: callable, arr: list, scheduler: str | None = None) -> list:
    """List map.

    Args:
        fn (callable): Function to apply
        arr (list): List to apply function
        scheduler (str, optional): Dask scheduler. Defaults to None.
            - None | "single-threaded": Single-threaded
            - "threads": Multi-threaded
            - "processes": Multi-process

    Returns:
        list: List of results
    """
    if scheduler is None:
        return list(map(fn, arr))
    else:
        assert scheduler in [
            "single-threaded",
            "threads",
            "processes",
        ], f"Invalid scheduler: {scheduler}"
        tasks = [delayed(fn)(e) for e in arr]
        return list(compute(*tasks, scheduler=scheduler))


def lstarmap(fn: callable, *arrs, scheduler: str | None = None) -> list:
    """List starmap.

    Args:
        fn (callable): Function to apply
        arrs (list): Lists to apply function
        scheduler (str, optional): Dask scheduler. Defaults to None.
            - None | "single-threaded": Single-threaded
            - "threads": Multi-threaded
            - "processes": Multi-process

    Returns:
        list: List of results
    """
    assert (
        len(np.unqiue(lmap(len, arrs))) == 1
    ), "All parameters should have same length."
    if scheduler is None:
        return list(starmap(fn, arrs))
    else:
        tasks = [delayed(fn)(*es) for es in zip(*arrs)]
        return list(compute(*tasks, scheduler=scheduler))


def str2bool(s: str | bool) -> bool:
    """String to boolean."""
    if isinstance(s, bool):
        return s
    if s.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif s.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise ValueError(f"Invalid input: {s} (type: {type(s)})")


class MetaSingleton(type):
    """Meta singleton.

    Example:
        >>> class A(metaclass=MetaSingleton):
        ...     pass
        >>> a1 = A()
        >>> a2 = A()
        >>> assert a1 is a2
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(MetaSingleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
