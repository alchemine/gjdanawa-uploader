"""Configuration file for the data pipeline."""

import yaml
from easydict import EasyDict
from os.path import join, abspath, dirname


def load_yaml(path: str) -> EasyDict:
    """Load yaml file."""
    with open(path, "r", encoding="utf8") as f:
        config = yaml.safe_load(f)
    return EasyDict(config)


##################################################
# PATH
##################################################
ROOT_PATH = dirname(dirname(abspath(__file__)))
SRC_PATH = join(ROOT_PATH, "gjdanawa_uploader")
CONFIG_PATH = join(ROOT_PATH, "configs")


##################################################
# Configs
##################################################
CFG_CRAWLER = load_yaml(join(CONFIG_PATH, "crawler.yml"))


if __name__ == "__main__":
    print(CFG_CRAWLER)
