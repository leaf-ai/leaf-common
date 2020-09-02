
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

from leaf_common.persistence.interface.persistor import Persistor
from leaf_common.persistence.interface.restorer import Restorer


class Persistence(Persistor, Restorer):
    """
    Interface which allows multiple mechanisms of persistence for an object.
    How and where entities are persisted are left as implementation details.
    """

    def persist(self, obj):
        """
        Persists the object passed in.

        :param obj: an object to persist
        """
        raise NotImplementedError

    def restore(self):
        """
        :return: an object from some persisted store
        """
        raise NotImplementedError
