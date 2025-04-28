from enum import IntEnum

class HttpCode(IntEnum):
    """HTTP status codes, compatible with Flask"""
    # Informational
    CONTINUE = 101                          # continue processing
    SWITCH_PROTOCOL = 102                   # switch protocol
    PROCESSING = 103                        # tell the client that the server is processing the request, but no response is available yet
    EARLY_HINTS = 103                       # allow to start the preloading of resources before the server has finished processing the request

    # Success
    OK = 200                                # request was successful, significant response depends on the method:
                                            # - GET: the resource has been fetched and is transmitted in the message body
                                            # - HEAD: the entity headers are in the message body
                                            # - PUt & POST: the result of the action is transmitted in the message body
                                            # - TRACE: the message body contains the request message as received by the server
    CREATED = 201                           # request was successful and a new resource was created (Usually for POST and PUT requests)
    ACCEPTED = 202                          # request was accepted for processing, but the processing has not been completed
    NON_AUTHORITATIVE_INFORMATION = 203     # request was successful, but the returned information is from a third-party source
    NO_CONTENT = 204                        # request was successful, but no content is returned (headers may still be useful)
    RESET_CONTENT = 205                     # request was successful, but the client should reset the document view
    PARTIAL_CONTENT = 206                   # request was successful, but only a part of the resource is returned (used for range requests)

    # Redirection
    MULTIPLE_CHOICES = 300                  # client must take additional action to complete the request
    MOVED_PERMANENTLY = 301                 # resource has been moved permanently to a new location
    FOUND = 302                             # resource has been found, but the location has been temporarily moved
    SEE_OTHER = 303                         # resource can be found under a different URI and should be retrieved using a GET method
    NOT_MODIFIED = 304                      # resource has not been modified since the last request, and the client should use the cached copy
    TEMPORARY_REDIRECT = 307                # resource has been temporarily moved to another URI, but the client should continue to use same method to access it
    PERMANENT_REDIRECT = 308                # resource has been permanently moved to another URI, and the client should use the new URI for all future requests

    # Client Error
    BAD_REQUEST = 400                       # server could not understand the request due to invalid syntax
    UNAUTHORIZED = 401                      # client must authenticate itself to get the requested response
    FORBIDDEN = 403                         # client does not have permission to access the requested resource
    NOT_FOUND = 404                         # server cannot find the requested resource. (May be used to hide the existence of a resource; in this case, it replace 403 Forbidden)
    METHOD_NOT_ALLOWED = 405                # request method is not supported for the requested resource
    NOT_ACCEPTABLE = 406                    # server cannot generate a response that the client will accept
    PROXY_AUTHENTICATION_REQUIRED = 407     # client must authenticate itself with the proxy (similar to 401 Unauthorized)
    REQUEST_TIMEOUT = 408                   # server timed out waiting for the request
    CONFLICT = 409                          # request could not be processed because of conflict in the request
    GONE = 410                              # requested resource is no longer available and will not be available again
    LENGTH_REQUIRED = 411                   # server requires a content-length header
    PRECONDITION_FAILED = 412               # one or more conditions in the request header fields evaluated to false
    PAYLOAD_TOO_LARGE = 413                 # request is larger than the server is willing or able to process
    IM_A_TEAPOT = 418                       # server refuses to brew coffee because it is a teapot
    TOO_MANY_REQUESTS = 429                 # client has sent too many requests in a given amount of time

    # Server Error
    INTERNAL_SERVER_ERROR = 500             # server has encountered a situation it doesn't know how to handle (only if no other error code applies)
    NOT_IMPLEMENTED = 501                   # request method is not supported by the server and cannot be handled
    SERVICE_UNAVAILABLE = 503               # server is not ready to handle the request (commonly used for maintenance)
    HTTP_VERSION_NOT_SUPPORTED = 505        # server does not support the HTTP protocol version used in the request