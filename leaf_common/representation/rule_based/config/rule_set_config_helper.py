
# Copyright (C) 2019-2022 Cognizant Digital Business, Evolutionary AI.
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
See class comment for details
"""

from typing import Dict, Any

CATEGORY_EXPLAINABLE_MARKER = "_is_category_"


class RuleSetConfigHelper:
    """
    Rule-set config helper class.
    """

    @staticmethod
    def get_states(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract states from Esp configuration
        :param config: Esp config
        :return: states
        """
        states = RuleSetConfigHelper._read_config_shape_var(config['network']['inputs'])
        return states

    @staticmethod
    def get_actions(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract actions from Esp configuration
        :param config: Esp config
        :return: actions
        """
        actions = RuleSetConfigHelper._read_config_shape_var(config['network']['outputs'])
        return actions

    @staticmethod
    def _read_config_shape_var(config_vars: Dict[str, Any]) -> Dict[str, str]:
        """
        This method handles the following two examples of defining network parameters into an enumerated list of them:
        FIRST CASE EXAMPLE:
        "network": {
            "inputs": [
                {
                    "name": "context",
                    "size": 21,
                    "values": [
                        "float"
                    ]
                }
            ],

        SECOND CASE EXAMPLE:
        "network": {
            "inputs": [
                {
                    "name": "param1",
                    "size": 1,
                    "values": [
                        "float"
                    ]
                },
                {
                    "name": "param2",
                    "size": 1,
                    "values": [
                        "float"
                    ]
                }, ... etc.

        THIRD CASE EXAMPLE: (including the return values format)
            INPUT/STATES:
                [{'name': 'admission_source_id', 'size': 6, 'values': ['Court/Law Enforcement',
                                                                        'Emergency Room',
                                                                        'Medical Healthcare Professional Referral',
                                                                        'Not Available', 'Pregnancy',
                                                                        'Transfer from another Medical Facility']},
                                                                         ... etc.
                {'0': 'admission_source_id_is_category_Court/Law Enforcement',
                '1': 'admission_source_id_is_category_Emergency Room',
                '2': 'admission_source_id_is_category_Medical Healthcare Professional Referral',
                '3': 'admission_source_id_is_category_Not Availaible',
                '4': 'admission_source_id_is_category_Pregnancy',
                '5': 'admission_source_id_is_category_Transfer from another Medical Facility',
                ... etc.

            OUTPUT/ACTIONS:
                [{'name': 'acarbose', 'size': 2, 'activation': 'softmax', 'use_bias': True, 'values': ['No', 'Yes']},
                ... etc.
                {'0': 'acarbose_is_category_No',
                '1': 'acarbose_is_category_Yes',
                ... etc.


        :param config_vars: A dictionary definition of input or output parameters of a domain
        :return: A dictionary enumerating the parameter definition
        """

        var_index = 0
        var = {}
        for var_item in config_vars:
            if var_item['size'] > 1:
                for i in range(var_item['size']):
                    var[str(var_index)] = var_item['name'] + CATEGORY_EXPLAINABLE_MARKER + var_item['values'][i]
                    var_index += 1
            else:
                var[str(var_index)] = var_item['name']
                var_index += 1
        return var

    @staticmethod
    def is_categorical(condition_name):
        """
        Check if condition is categorical
        :param condition_name: if you are expecting me to tell you what this is you need therapy
        :return: Boolean
        """
        return CATEGORY_EXPLAINABLE_MARKER in condition_name

    @staticmethod
    def extract_categorical_condition_name(condition_name):
        """
        Extract the name of the categorical condition from the name string
        :param condition_name: if you are expecting me to tell you what this is you need therapy
        :return: Str
        """
        return condition_name.split(CATEGORY_EXPLAINABLE_MARKER)[0]

    @staticmethod
    def extract_categorical_condition_category(condition_name):
        """
        Extract the category name from the name string
        :param condition_name: if you are expecting me to tell you what this is you need drugs
        :return: Str
        """
        return condition_name.split(CATEGORY_EXPLAINABLE_MARKER)[1]
