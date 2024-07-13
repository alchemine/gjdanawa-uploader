"""Commonly used package."""

from base_project.core.global_settings import configure_global_settings
from base_project.core.depth_logging import D
from base_project.core.files import ls_all, ls_dir, ls_file, load_yaml
from base_project.core.timer import Timer, T
from base_project.core.utils import (
    tprint,
    lmap,
    lstarmap,
    str2bool,
    str2dt,
    dt2str,
    MetaSingleton,
)

__all__ = [
    "D",
    "ls_all",
    "ls_dir",
    "ls_file",
    "load_yaml",
    "Timer",
    "T",
    "tprint",
    "lmap",
    "lstarmap",
    "str2bool",
    "str2dt",
    "dt2str",
    "MetaSingleton",
]

configure_global_settings()
