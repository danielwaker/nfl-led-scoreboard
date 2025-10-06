from enum import Enum

class GroupType(Enum):
    AFC           = 8
    NFC           = 7
    NFC_EAST      = 1
    NFC_NORTH     = 10
    NFC_SOUTH     = 11
    NFC_WEST      = 3
    AFC_EAST      = 4
    AFC_WEST      = 6
    AFC_NORTH     = 12
    AFC_SOUTH     = 13
    NFL           = 9

def is_division(group_type: GroupType):
    return (group_type == GroupType.NFC_NORTH 
            or group_type == GroupType.NFC_EAST
            or group_type == GroupType.NFC_SOUTH
            or group_type == GroupType.NFC_WEST
            or group_type == GroupType.AFC_NORTH
            or group_type == GroupType.AFC_EAST
            or group_type == GroupType.AFC_SOUTH
            or group_type == GroupType.AFC_WEST)