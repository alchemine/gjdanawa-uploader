"""Commonly used package."""

from base_project.utils.global_settings import configure_global_settings
from base_project.utils.depth_logging import D
from base_project.utils.files import ls_all, ls_dir, ls_file, load_yaml
from base_project.utils.timer import Timer, T
from base_project.utils.utils import (
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
