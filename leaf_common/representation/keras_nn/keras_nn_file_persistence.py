"""
See class comment for details
"""

from leaf_common.persistence.factory.simple_file_persistence import SimpleFilePersistence
from leaf_common.persistence.interface.persistence import Persistence
from leaf_common.serialization.interface.file_extension_provider import FileExtensionProvider


class KerasNNFilePersistence(Persistence, FileExtensionProvider):
    """
    Implementation of the Persistence interface, enough to save/restore
    Keras neural-nets to/from a file.
    """

    def __init__(self, evaluator):
        """
        Constructor

        :param evaluator: The EspEvaluator to use to help decode the model bytes
        """
        self._evaluator = evaluator
        self.simple = SimpleFilePersistence(None)

    def get_file_extension(self):
        """
        :return: A string representing a file extension for the
                serialization method, including the ".".
        """
        return ".h5"

    def persist(self, obj: object, file_reference: str = None) -> str:
        """
        Persists the object passed in.

        :param obj: an object to persist
        :param file_reference: The file reference to use when persisting.
        """
        file_name = self.simple.affix_file_extension(file_reference, self)

        # Convert the received bytes to a Keras model
        # Use everything opaquely, so as not to explicitly drag in unwanted dependencies
        keras_model = self._evaluator.keras_model_from_bytes(obj)
        keras_model.save(file_name, include_optimizer=False)

        return file_name

    def restore(self, file_reference: str = None):
        """
        :param file_reference: The file reference to use when restoring.
        :return: an object from some persisted store
        """
        raise NotImplementedError
