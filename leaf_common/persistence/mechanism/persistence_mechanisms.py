
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


class PersistenceMechanisms():
    """
    Class containing string constants for persistence mechanisms.
    """
    # Persistence Mechanisms
    NULL = "null"           # No persistence
    LOCAL = "local"         # local file
    S3 = "s3"               # AWS S3 storage

    PERSISTENCE_MECHANISMS = [NULL, LOCAL, S3]
