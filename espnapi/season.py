from enum import Enum
import sys

class SeasonType(Enum):
    PRESEASON           = 1
    REGULAR_SEASON      = 2
    PLAYOFFS            = 3
    OFF_SEASON          = 4

# sys.modules['season'] = SeasonType()
