
# Copyright (C) 2019-2023 Cognizant Digital Business, Evolutionary AI.
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
See class comment for details.
"""

import logging
import threading
import traceback

import grpc

from leaf_common.time.timeout import Timeout

from leaf_common.session.grpc_channel_security import GrpcChannelSecurity
from leaf_common.session.grpc_metadata_util import GrpcMetadataUtil


class GrpcClientRetry():
    """
    A class aiding in the retrying of grpc methods, allowing for the services
    on the other end to come up and down while client code is trying to call
    them, and the client code requires results.

    No entity wrapping a socket is created in constructing this object.
    gRPC entities wrapping sockets (channels) are created for each attempt
    at a single gRPC method call.  This allows for the retry logic supported
    by this class to withstand the services on the other end going up and down.
    """

    # Public Enemy #1 for too-many-arguments
    # pylint: disable=too-many-arguments
    # Public Enemy #2 for too-many-instance-attributes
    # pylint: disable=too-many-instance-attributes
    def __init__(self, service_name, service_stub, host, port,
                 timeout_in_seconds=30, poll_interval_seconds=15,
                 max_message_length=-1, limited_retry_set=None,
                 limited_retry_attempts=3, metadata=None,
                 security_cfg=None, channel_security=None,
                 umbrella_timeout=None):
        """
        :param service_name: a string for the name of the service,
                            used for logging
        :param service_stub: a reference to the grpc code-generated class
                            for the client service Stub. For instance,
                            a service generated by grpc from a file called
                            foo.proto for a service called "Bar" will have
                            its service stub be references as
                            foo_pb2_grpc.BarStub
        :param host: The host which is hosting the service
        :param port: The port on the host for the service
        :param timeout_in_seconds: A timeout given for any gRPC call to fail.
                            Timeouts longer than 1 minute will likely
                            be subject to other os-level socket timeouts
                            which are not modifiable at this level of API.
        :param poll_interval_seconds: length of time in seconds methods
                            on this class will wait before retrying connections
                            or specific gRPC calls. Default to 15 seconds.
        :param max_message_length: Maximum size in bytes of a response from
                            the service being called. By default this is -1,
                            which according to the gRPC docs indicates that
                            there is no limit to the message size receivable
                            on this client end of the connection.
        :param limited_retry_set: A set of GRPC StatusCodes which will have
                            limited ability to retry.
                            None by default, indicating that any error has
                            unlimited retries.
        :param limited_retry_attempts: the limited number of retries for the
                            StatusCodes in the limited_retry_set before raising
                            the exception upstream.  Default is 3.
        :param metadata: A grpc metadata of key/value pairs to be inserted into
                         the header. Default is None. Preferred format is a
                         dictionary of string keys to string values.
        :param security_cfg: An optional dictionary of parameters used to
                        secure the TLS and the authentication of the gRPC
                        connection.  Supplying this implies use of a secure
                        GRPC Channel.  Default is None, uses insecure channel.
        :param channel_security: A GrpcChannelSecurity object which controls
                        the lifetime of any token received from a secure service
        :param umbrella_timeout: A Timeout object under which the length of all
                        looping and retries should be considered
        """

        self.logger = logging.getLogger(__name__)

        self.service_name = service_name
        self.service_stub = service_stub
        self.host = host
        self.port = port
        self.timeout_in_seconds = timeout_in_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_message_length = max_message_length
        self.connect_timeout_seconds = 15
        self.limited_retry_set = limited_retry_set
        self.limited_retry_attempts = limited_retry_attempts
        self.channel = None
        self.metadata = metadata

        self.channel_security = channel_security
        if self.channel_security is None:
            # If there is no channel_security, make one whose token
            # potentially lasts as long as this class does.
            self.channel_security = \
                GrpcChannelSecurity(security_cfg=security_cfg,
                                    auth0_defaults=None,
                                    service_name=service_name,
                                    poll_interval_seconds=timeout_in_seconds,
                                    umbrella_timeout=umbrella_timeout)
        self.debug = False
        self.call_credentials = None
        self.umbrella_timeout = umbrella_timeout

        if self.limited_retry_set is None:
            # Empty set
            self.limited_retry_set = set()

    def must_connect(self):
        """
        Keeps trying to connect to the service indefinitely until
        an attempt is successful.

        Upon success, the GRPC channel is left open so further communications
        can continue.

        Callers are responsible for calling close_channel() on this instance.

        :return: If the single connection attmept is successful,
                an instance of the gRPC stub service with the socket/channel
                connected is returned.
        """

        stub_instance = None
        while stub_instance is None and \
            Timeout.has_time(self.poll_interval_seconds,
                             timeout=self.umbrella_timeout):

            try:
                stub_instance = self._connect_to_service()

            except KeyboardInterrupt:
                # Allow for command-line quitting
                self.close_channel_and_reset_token()
                raise

            # DEF: Had a pass on grpc.FutureTimeoutError here
            # Where did that go?

            if stub_instance is not None:
                # We want to leave the channel open if the connect is successful.
                break

            # Close the channel just in case to avoid resource leaks
            # We do not necessarily want a new token just because there is
            # a retry situation.
            self.close_channel()

            # Log the problem and wait to try again.
            err = "Retrying initial connection to %s in %s secs."
            self.logger.warning(err, str(self.service_name),
                                str(self.poll_interval_seconds))

            threading.Event().wait(timeout=self.poll_interval_seconds)

        return stub_instance

    def must_have_response(self, method_name, rpc_call_from_stub, *args):   # noqa: C901
        """
        Keeps trying to connect to the gRPC service to make a single
        gRPC call.  Attempts will continue indefinitely until
        an attempt is successful with a non-None response by the gRPC call.

        Each attempt is made with a new socket/channel to the service,
        allowing for the service on the other end to go up and down.

        :param method_name: a string name for the gRPC method invoked
                    used for logging purposes.
        :param rpc_call_from_stub: a global-scope method whose signature looks
                    like this:

            def _my_rpc_call_from_stub(stub, timeout_in_seconds,
                                        metadata, credentials, *args):
                response = stub.MyRpcCall(*args, timeout=timeout_in_seconds,
                                            metadata=metadata,
                                            credentials=credentials)
                return response

        :param *args: a list of arguments to pass to the rpc call method.
                    Even if the gRPC call only takes a single argument,
                    you must put that single argument in a list like this:
                    [ my_one_arg ]

        :return: When a gRPC method call attmept is successful,
                    the instance of the response for that call is returned.
        """

        converted_metadata = GrpcMetadataUtil.to_tuples(self.metadata)

        num_attempts = 0
        response = None
        while response is None and \
            Timeout.has_time(self.poll_interval_seconds,
                             timeout=self.umbrella_timeout):
            try:
                # Connect with a fresh socket each time we make a request.
                # This allows for the service going down in between retries.
                stub_instance = self.must_connect()

                # Even though we must_connect(), we might not due to the
                # umbrella timeout
                if stub_instance is None:
                    break

                # It's possible that the above connection can be successful
                # and then the rpc call below is when the service decides to
                # go down. That's OK. the rpc_call_from_stub() will fail, and
                # a new socket will be connected to the new service instance
                # upon the detection of the failure below.

                # By this point self.call_credentials should have been set up
                # if they were necessary, which is the case when there are
                # call credentials, but no channel credentials..

                # Make the rpc call attempt
                response = rpc_call_from_stub(stub_instance,
                                              self.timeout_in_seconds,
                                              converted_metadata,
                                              self.call_credentials,
                                              *args)

            except KeyboardInterrupt as exception:
                # Allow for command-line quitting
                self.close_channel_and_reset_token()
                raise exception

            except Exception as exception:      # pylint: disable=broad-except

                # See if the error is an RpcError with status codes
                # that are registered as limited-retry.
                if self.debug:
                    self.logger.error(exception)
                    error = traceback.format_exc()
                    self.logger.error(error)

                log_exception = True
                exception_str = str(exception)
                if isinstance(exception, grpc.RpcError):
                    # pylint-protobuf cannot see the typing at this point
                    # pylint: disable=no-member
                    status_code = exception.code()

                    log_exception = not self._check_unauthenticated(status_code)

                    # Allow exceptions that say our own service is
                    # refusing for shut down purposes.
                    if status_code in self.limited_retry_set \
                            and not self._is_shut_down_refusal(exception):

                        num_attempts = num_attempts + 1
                        if num_attempts == self.limited_retry_attempts:
                            # We do not necessarily want a new token just
                            # because there is a retry situation.
                            self.close_channel()
                            raise

                elif isinstance(exception, KeyError):
                    error = "Could not get access token for secure " + \
                            "communication to %s.\n" + \
                            "Check your ~/.enn/security_config.hocon to be " + \
                            "sure the values for the keys:\n" + \
                            "    auth_client_id\n" + \
                            "    auth_secret\n" + \
                            "    username\n" + \
                            "    password\n" + \
                            "have been entered correctly."
                    host_and_port = f"{self.host}:{self.port}"
                    self.logger.error(error, host_and_port)
                    self.close_channel_and_reset_token()
                    raise

                if log_exception:
                    # Log the problem and wait to try again.
                    info = "Info: Exception when calling %s: %s. " + \
                            "Retrying in %s secs."
                    self.logger.warning(info, str(method_name), exception_str,
                                        str(self.poll_interval_seconds))

                # Close the channel before sleep to tidy up sooner
                # We do not necessarily want a new token just
                # because there is a retry situation.
                self.close_channel()

                # For some reason using a sleep causes threads to lock in here.
                # The cause is unknown but using the interruptable sleep
                # seems to alliviate/fix the problem.  Not enough is yet
                # known as to the cause
                threading.Event().wait(timeout=self.poll_interval_seconds)

            finally:
                # Always close the channel
                # We do not necessarily want a new token just
                # because there is a retry situation.
                self.close_channel()

        return response

    def _check_unauthenticated(self, status_code):
        """
        Checks for an unauthenticated error on grpc request
        :return: True if we found the unauthenticated error.
        """
        found_unauthenticated = False

        # This is the GRPC StatusCode that will be returned
        # when we had a token and we found that it expired.
        if status_code == grpc.StatusCode.UNAUTHENTICATED:

            found_unauthenticated = True
            if self.channel_security.has_token():
                message = "Security token expired, trying again"
                self.logger.info(message)
            else:

                # Consider a case where we were not authenticated
                # and never had a token in the first place.
                error = "Could not get access token for secure " + \
                    "communication to %s.\n" + \
                    "Check your ~/.enn/security_config.hocon to be " + \
                    "sure the values for the keys:\n" + \
                    "    auth_client_id\n" + \
                    "    auth_secret\n" + \
                    "    username\n" + \
                    "    password\n" + \
                    "have been entered correctly."
                host_and_port = f"{self.host}:{self.port}"
                self.logger.error(error, host_and_port)
            self.close_channel_and_reset_token()

        return found_unauthenticated

    def close_channel_and_reset_token(self):
        """
        Called whenever we close the channel in response to an exception
        which requires us to reset the token.
        """
        self.close_channel()
        self.channel_security.reset_token()

    def close_channel(self):
        """
        Close the GRPC Channel if one has been opened.
        Allow for this being an older GRPC Channel object
        that might not have the close() method yet.

        This is done for you if you call must_have_response(),
        but if you use must_connect(), you must do this yourself.
        """
        if self.channel is not None:
            if "close" in dir(self.channel):
                self.channel.close()
            self.channel = None

    def _connect_to_service(self):
        """
        Attempt to connect to the service specified in the constructor once.
        :return: If the single connection attmept is successful,
                an instance of the gRPC stub service with the socket/channel
                connected is returned. If the connection is unsuccessful,
                None is returned.
        """

        host_and_port = f"{self.host}:{self.port}"

        self.logger.info("Connecting to %s on %s ...",
                         self.service_name, host_and_port)

        options = [
            ('grpc.max_send_message_length', self.max_message_length),
            ('grpc.max_receive_message_length', self.max_message_length),
        ]

        # Add a few more tuples if there is auth_host_override set
        auth_host_override = self.channel_security.get_auth_host_override()
        if auth_host_override is not None:
            options.append(('grpc.ssl_target_name_override',
                            auth_host_override))
            options.append(('grpc.default_authority',
                            auth_host_override))

        # We do not necessarily want a new token just
        # because we want a new channel next time.
        self.close_channel()

        try:
            # "Channels" are gRPC's wrappers for sockets.

            self.call_credentials = None
            if self.channel_security.needs_credentials():
                # Get the credentials for the channel (if any)
                creds = self.channel_security.get_composite_channel_credentials()

                if creds is not None:
                    # "Channels" are gRPC's wrappers for sockets.
                    if isinstance(creds, grpc.ChannelCredentials):
                        # Channel credentials holds all the access info,
                        # including call credentials (can be composite)
                        self.channel = grpc.secure_channel(host_and_port, creds,
                                                           options=options)
                    elif isinstance(creds, grpc.CallCredentials):
                        # We are using an insecure channel, but we will be
                        # sending specific call credentials with each RPC call.
                        self.channel = grpc.insecure_channel(host_and_port,
                                                             options=options)
                        self.call_credentials = creds
                else:
                    self.logger.error("Didn't get credentials for %s", self.service_name)
                    self.close_channel_and_reset_token()
                    raise ValueError("No creds from auth domain")
            else:
                self.channel = grpc.insecure_channel(host_and_port,
                                                     options=options)

            grpc.channel_ready_future(self.channel).result(
                timeout=self.connect_timeout_seconds)

        except grpc.FutureTimeoutError:

            # Log the problem, but let the caller figure out what to do
            # with the failure.
            msg = "Failed to connect to %s on %s. Timeout error after %d seconds."
            self.logger.error(msg, self.service_name, host_and_port,
                              self.connect_timeout_seconds)
            # We do not necessarily want to reset the token in this case
            self.close_channel()
            return None

        self.logger.info("Connected to %s on %s.", self.service_name,
                         host_and_port)

        # Create the service stub that we will return from this method
        # with the successfully connected channel.
        stub_instance = self.service_stub(self.channel)
        return stub_instance

    @staticmethod
    def _is_shut_down_refusal(rpc_error):
        """
        :param rpc_exception: an RPCError
        :return: True if the RPCError can be determined to be a service
                shutdown refusal. False otherwise.
        """

        # Innocent until proven guilty
        is_refusal = False

        # This is to match the string in server_lifetime.py
        search_for = "Service refusing"
        err_str = str(rpc_error)
        if search_for in err_str:
            is_refusal = True

        return is_refusal
