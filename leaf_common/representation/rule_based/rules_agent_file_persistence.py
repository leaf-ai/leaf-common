"""
See class comment for details.
"""

from leaf_common.persistence.factory.simple_file_persistence import SimpleFilePersistence
from leaf_common.representation.rule_based.rules_agent_serialization_format import RulesAgentSerializationFormat
from leaf_common.serialization.interface.serialization_format import SerializationFormat


class RulesAgentFilePersistence(SimpleFilePersistence):
    """
    Implementation of the leaf-common Persistence interface which
    saves/restores a RulesAgent to a file.
    """

    def __init__(self, serialization_format: SerializationFormat = None):
        """
        Constructor.

        :param serialization_format: A means of serializing a RulesAgent
                by default this is None and a RulesAgentSerializationFormat is used
        """
        use_format = serialization_format
        if use_format is None:
            use_format = RulesAgentSerializationFormat()
        super(RulesAgentFilePersistence, self).__init__(use_format)
