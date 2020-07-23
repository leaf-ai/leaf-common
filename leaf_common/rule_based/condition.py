"""
Base class for condition representation
"""

from typing import Dict
from typing import List
from typing import Tuple

from leaf_common.rule_based.rules_evaluation_constants \
    import RulesEvaluationConstants


class Condition:  # pylint: disable-msg=R0902
    """
    A class that encapsulates a binary condition with two operands (self.first_state and self.second_state)
    The operands used by the condition are randomly chosen at construction time from the list of states supplied
    from the Domain.
    An operator is randomly chosen from the `OPERATORS` list.
    """

    def __init__(self, states: Dict[str, str]):

        # State/Config needed for evaluation
        self.states = states

        # Genetic Material fields
        self.first_state_lookback: int = None
        self.first_state_key: str = None
        self.first_state_coefficient: float = None
        self.operator: str = None
        self.second_state_lookback: int = None
        self.second_state_key: str = None
        self.second_state_value: float = None
        self.second_state_coefficient: float = None

    def __str__(self):
        return self.get_str()

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    # see https://github.com/PyCQA/pycodestyle/issues/753 for why next line needs noqa
    def get_str(self, min_maxes: Dict[Tuple[str, str], float] = None) -> str:  # noqa: E252
        """
        String representation for condition
        :param min_maxes: A dictionary of domain features minimum and maximum values
        :return: condition.toString()
        """

        coeff1 = self.first_state_coefficient
        key1 = self.states[self.first_state_key]
        lookback1 = self.first_state_lookback

        first_condition = f'{coeff1:.{RulesEvaluationConstants.DECIMAL_DIGITS}f}*{key1}'
        if lookback1 > 0:
            first_condition = f'{first_condition}[{lookback1}]'

        if self.second_state_key in self.states:
            coeff2 = self.second_state_coefficient
            key2 = self.states[self.second_state_key]
            lookback2 = self.second_state_lookback
            second_condition = f'{coeff2:.{RulesEvaluationConstants.DECIMAL_DIGITS}f}*{key2}'
            if self.second_state_lookback > 0:
                second_condition = f'{second_condition}[{lookback2}]'
        elif min_maxes:
            min_value = min_maxes[self.first_state_key, RulesEvaluationConstants.MIN_KEY]
            max_value = min_maxes[self.first_state_key, RulesEvaluationConstants.MAX_KEY]
            second_condition_val = (min_value + self.second_state_value * (max_value - min_value))
            second_condition = \
                f'{second_condition_val:.{RulesEvaluationConstants.DECIMAL_DIGITS}f} {{{min_value}..{max_value}}}'
        else:
            second_condition = f'{self.second_state_value:.{RulesEvaluationConstants.DECIMAL_DIGITS}f}'

        return f'{first_condition} {self.operator} {second_condition}'

    def get_second_state_value(self, domain_states: List[Dict[str, float]], nb_states: int,
                               min_maxes: Dict[Tuple[str, str], float]) -> float:
        """
        Get second state value
        :param domain_states: list of domain states
        :param nb_states: the number of domain states
        :param min_maxes: list of states min and max values
        :return: the second state
        """
        if self.second_state_key in self.states.keys():
            second_state_idx = nb_states - self.second_state_lookback
            second_state = domain_states[second_state_idx][self.second_state_key]
            second_state *= self.second_state_coefficient
        else:
            the_min = min_maxes[self.first_state_key, RulesEvaluationConstants.MIN_KEY]
            the_max = min_maxes[self.first_state_key, RulesEvaluationConstants.MAX_KEY]
            the_range = the_max - the_min
            second_state = the_min + the_range * self.second_state_value

        return second_state

    def parse(self, domain_states: List[Dict[str, float]], min_maxes: Dict[Tuple[str, str], float]) -> bool:
        """
        Parse a condition
        :param domain_states: list of domain states
        :param min_maxes: list of min and max values, one pair per state
        :return: A boolean indicating whether this condition is satisfied by the given domain states
        """
        nb_states = len(domain_states) - 1

        # If we don't have sufficient history for the requested lookback, just return False
        if nb_states < self.first_state_lookback or nb_states < self.second_state_lookback:
            return False
        domain_state_idx = nb_states - self.first_state_lookback
        domain_state_value = domain_states[domain_state_idx][self.first_state_key]
        operand_1 = domain_state_value * self.first_state_coefficient
        operand_2 = self.get_second_state_value(domain_states, nb_states, min_maxes)
        condition = (
            (self.operator == RulesEvaluationConstants.GREATER_THAN_EQUAL and operand_1 >= operand_2) or
            (self.operator == RulesEvaluationConstants.LESS_THAN_EQUAL and operand_1 <= operand_2) or
            (self.operator == RulesEvaluationConstants.GREATER_THAN and operand_1 > operand_2) or
            (self.operator == RulesEvaluationConstants.LESS_THAN and operand_1 < operand_2)
        )
        return condition
