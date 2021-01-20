
# Copyright (C) 2019-2020 Cognizant Digital Business, Evolutionary AI.
# All Rights Reserved.
# Issued under the Academic Public License.
#
# You can be released from the terms, and requirements of the Academic Public
# License by purchasing a commercial license.
# Purchase of a commercial license is mandatory for any use of the
# ENN-release SDK Software in commercial settings.
#
# END COPYRIGHT
"""
See class comment for details.
"""

from leaf_common.persistence.factory.abstract_persistence \
    import AbstractPersistence
from leaf_common.serialization.format.json_serialization_format \
    import JsonSerializationFormat


class JsonPersistence(AbstractPersistence):
    """
    Implementation of the AbstractPersistence class which
    saves JSON data for an object via some persistence mechanism.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, persistence_mechanism,
                 use_file_extension=None, reference_pruner=None,
                 dictionary_converter=None, pretty=True):
        """
        Constructor

        :param persistence_mechanism: the PersistenceMechanism to use
                for storage
        :param use_file_extension: Use the provided string instead of the
                standard file extension for the format. Default is None,
                indicating the standard file extension for the format should
                be used.
        :param reference_pruner: a ReferencePruner implementation
                that knows how to prune/graft repeated references
                throughout the object hierarchy
        :param dictionary_converter: A DictionaryConverter implementation
                that knows how to convert from a dictionary to the object type
                in question.
        :param pretty: a boolean which says whether the JSON is to be
                nicely formatted or not.  indent=4, sort_keys=True
        """

        super().__init__(persistence_mechanism,
                         use_file_extension=use_file_extension)
        self._serialization = JsonSerializationFormat(
            reference_pruner=reference_pruner,
            dictionary_converter=dictionary_converter,
            pretty=pretty)

    def get_serialization_format(self):
        """
        :return: The SerializationFormat instance to be used in persist()
                 and restore()
        """
        return self._serialization
