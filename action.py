from enum import StrEnum

class Action(StrEnum):
    CALL = "CALL"
    CHECK = "CHECK"
    FOLD = "FOLD"
    RAISE = "RAISE"
