"""
See class comment
"""

import math


class RulesEvaluationConstants():
    """
    Constants for various aspects of Rules evaluation
    """

    # Rules stuff
    RULE_FILTER_FACTOR = 1
    AGE_STATE_KEY = "age"
    MEM_FACTOR = 100  # max memory cells required
    TOTAL_KEY = "total"

    # Rule stuff
    RULE_ELEMENTS = ["condition", "action", "action_lookback"]
    LOOK_BACK = "lb"
    NO_ACTION = -1

    # pylint: disable-fixme
    # XXX If these are used as a keys, they would be better off as a strings
    #       Think: More intelligible in JSON.
    ACTION_KEY = 0
    LOOKBACK_KEY = 1

    # Condition stuff
    CONDITION_ELEMENTS = [
        "first_state",
        "first_state_coefficient",
        "first_state_exponent",
        "first_state_lookback",
        "operator",
        "second_state",
        "second_state_coefficient",
        "second_state_exponent",
        "second_state_lookback",
        "second_state_value"
    ]
    MIN_KEY = "min"
    MAX_KEY = "max"
    GRANULARITY = 100
    DECIMAL_DIGITS = int(math.log10(GRANULARITY))

    # Condition operator strings
    LESS_THAN = "<"
    LESS_THAN_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_EQUAL = ">="
