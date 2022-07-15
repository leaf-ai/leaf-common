
# Copyright (C) 2019-2021 Cognizant Digital Business, Evolutionary AI.
# All Rights Reserved.
# Issued under the Academic Public License.
#
# You can be released from the terms, and requirements of the Academic Public
# License by purchasing a commercial license.
# Purchase of a commercial license is mandatory for any use of the
# leaf-common SDK Software in commercial settings.
#
# END COPYRIGHT
"""
Base class for condition representation
"""

from typing import Dict

from leaf_common.representation.rule_based.data.rules_constants import RulesConstants as LeafCommonConstants


class Condition:  # pylint: disable-msg=R0902
    """
    A class that encapsulates a binary condition with two operands (self.first_state and self.second_state)
    The operands used by the condition are randomly chosen at construction time from the list of states supplied
    from the Domain.
    An operator is randomly chosen from the `OPERATORS` list.
    """

    def __init__(self):

        # Genetic Material fields
        self.first_state_lookback: int = None
        self.first_state_key: str = None
        self.first_state_coefficient: float = None
        self.first_state_exponent: int = None
        self.operator: str = None
        self.second_state_lookback: int = None
        self.second_state_key: str = None
        self.second_state_value: float = None
        self.second_state_coefficient: float = None
        self.second_state_exponent: int = None

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return self.__str__()

    # see https://github.com/PyCQA/pycodestyle/issues/753 for why next line needs noqa
    def to_string(self, states: Dict[str, str] = None,
                  min_maxes: Dict[str, Dict[str, float]] = None) -> str:  # noqa: E252
        """
        FOR EXAMPLE:(for categorical)
        'race_is_category_Hispanic' becomes 'race is Hispanic'

        String representation for condition
        :param states: A dictionary of domain features
        :param min_maxes: A dictionary of domain features minimum and maximum values
        :return: condition.toString()
        """

        # Handle categorical conditions separately
        if states and Condition.is_categorical(states[self.first_state_key]):
            the_string = self.categorical_to_string(states)
        else:
            the_string = self.continuous_to_string(min_maxes, states)

        return the_string

    def continuous_to_string(self, min_maxes, states):
        """
        String representation for continuous condition
        :param states: A dictionary of domain features
        :param min_maxes: A dictionary of domain features minimum and maximum values
        :return: condition.toString()
        """
        # Prepare 1st condition string
        first_condition = self._condition_part_to_string(self.first_state_coefficient,
                                                         self.first_state_key,
                                                         self.first_state_lookback,
                                                         self.first_state_exponent,
                                                         states)
        # Prepare 2nd condition string
        # Note: None or empty dictionaries both evaluate to false
        if states and self.second_state_key in states:
            second_condition = self._condition_part_to_string(self.second_state_coefficient,
                                                              self.second_state_key,
                                                              self.second_state_lookback,
                                                              self.second_state_exponent,
                                                              states)
        # Note: None or empty dictionaries both evaluate to false
        elif min_maxes:
            # Per evaluation code, min/max is based on the first_state_key
            empty_dict = {}
            state_dict = min_maxes.get(self.first_state_key, empty_dict)
            min_value = state_dict.get(LeafCommonConstants.MIN_KEY)
            max_value = state_dict.get(LeafCommonConstants.MAX_KEY)
            second_condition_val = (min_value + self.second_state_value * (max_value - min_value))
            second_condition = \
                f'{second_condition_val:.{LeafCommonConstants.DECIMAL_DIGITS}f} {{{min_value}..{max_value}}}'
        else:
            second_condition = f'{self.second_state_value:.{LeafCommonConstants.DECIMAL_DIGITS}f}'
        the_string = f'{first_condition} {self.operator} {second_condition}'
        return the_string

    def categorical_to_string(self, states):
        """
        FOR EXAMPLE:(for categorical)
        'race_is_category_Hispanic' becomes 'race is Hispanic'

        String representation for categorical condition
        :param states: A dictionary of domain features
        :return: condition.toString()
        """
        name = Condition.extract_categorical_condition_name(states[self.first_state_key])
        category = Condition.extract_categorical_condition_category(states[self.first_state_key])
        look_back = ''
        if self.first_state_lookback > 0:
            look_back = '[' + str(self.first_state_lookback) + ']'
        operator = "is"

        # The categorical data are coming in as one-hot, and we put 1.0 as the value to be compared to,
        # so LESS_THAN means "< 1" or zero (equivalent to False) and GREATER_THAN_EQUAL means ">= 1"
        # which is equivalent to one (True).
        if self.operator == LeafCommonConstants.LESS_THAN:
            operator = operator + " not"
        the_string = f'{name}{look_back} {operator} {category}'
        return the_string

    # pylint: disable=too-many-arguments
    def _condition_part_to_string(self, coeff: float, key: str, lookback: int, exponent: int,
                                  states: Dict[str, str]) -> str:
        """
        Given features of a side of a condition inequality,
        return a string that describes the side, at least in a default capacity.
        (right side -- 2nd condition is not fully realized here in case of min/maxes)
        """
        del self
        use_key = key
        if states is not None and key in states:
            use_key = states[key]

        condition_part = f'{coeff:.{LeafCommonConstants.DECIMAL_DIGITS}f}*{use_key}'
        if lookback > 0:
            condition_part = f'{condition_part}[{lookback}]'
        if exponent > 1:
            condition_part = f'{condition_part}^{exponent}'

        return condition_part

    @staticmethod
    def is_categorical(condition_name):
        """
        Check if condition is categorical
        :param condition_name: if you are expecting me to tell you what this is you need therapy
        :return: Boolean
        """
        return LeafCommonConstants.CATEGORY_EXPLAINABLE_MARKER in condition_name

    @staticmethod
    def extract_categorical_condition_name(condition_name):
        """
        Extract the name of the categorical condition from the name string
        :param condition_name: if you are expecting me to tell you what this is you need therapy
        :return: Str
        """
        return condition_name.split(LeafCommonConstants.CATEGORY_EXPLAINABLE_MARKER)[0]

    @staticmethod
    def extract_categorical_condition_category(condition_name):
        """
        Extract the category name from the name string
        :param condition_name: if you are expecting me to tell you what this is you need drugs
        :return: Str
        """
        return condition_name.split(LeafCommonConstants.CATEGORY_EXPLAINABLE_MARKER)[1]
