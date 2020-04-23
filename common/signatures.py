import hmac

from base64 import b64encode
from typing import Any, Callable, List
from urllib import parse


def new_signature(
        key: bytes,
        method: str,
        canonical_URI: str,
        query: str = "",
        signature_headers: List[str] = [],
        header_recoverer: Callable[[str], Any] = None) -> str:
    """Creates a signature following the scheme SECCHIWARE-HMAC-256.

    Algorithm
    ---------
    1-  Creates an empty string.
    2-  Appends the method in lowercase followed by a newline character ('\\n').
    3-  Appends the canonical URI (path from host without a query string)
        followed by a newline character ('\\n').
    4-  If there is a query string, appends it URL-encoded (space=%20) followed
        by a newline character ('\\n').
    5-  For every header specified, appends the following expression:
        "{header_name}: {header_value}\\n", where header_name is the key of the
        header in lowercase and header_value is its corresponding value. For the
        last header the trailing newline character is omitted.
    6-  Calculates the digest of the generated string using HMAC-SHA256 and
        encodes it in base 64 to obtain the signature.

    Parameters
    ----------
    key: bytes
        The key used to generate the signature.
    method: str
        The method of the HTTP request to sign. It gets converted to lowercase.
    canonicar_URI: str
        The path from host of the request without a query string.
    query: str, optional
        The query part of the request (the string after "?").
    signature_headers: List[str], optional
        A list with the keys of the headers to include in the signature, if
        any.
    header_recoverer: Callable, optional
        If signature_headers is given, a function that recieves a header key
        and returns its corresponding value must be provided.

    Raises
    ------
    TypeError
        If "header_recoverer" is None but "signature_headers" is not empty.
    KeyError
        If a given header key is not found through the "header_recoverer"
        function.

    Returns
    -------
    str
        A base 64 encoded digest generated using the function arguments.
    """

    signature_str = f"{method.lower()}\n{canonical_URI}\n"
    if query:
        # Canonical query string should be URL-encoded (space=%20)
        signature_str = f"{signature_str}{parse.quote(query)}\n"

    if signature_headers:
        if header_recoverer is None:
            raise TypeError(
                "'header_recoverer' is None but 'signature_headers' is not "
                "empty.")
        for h in signature_headers:
            h = h.lower()
            header_value = header_recoverer(h)
            if header_value is None:
                raise KeyError(h)
            signature_str = f"{signature_str}{h}: {header_value}\n"

    signature_str = signature_str.rstrip()
    hasher = hmac.new(key, signature_str.encode(), "sha256")
    return b64encode(hasher.digest()).decode()

def new_authorization_header(
        key_id: str,
        signature: str,
        signature_headers: List[str] = []) -> str:
    """Generates the value of an Authorization HTTP header following the
    scheme SECCHIWARE-HMAC-256.

    Format:
        SECCHIWARE-HMAC-256 keyId={kid},[headers={hdrs}],signature={sgn}

    Where:
        kid:    an opaque string identifier used to find the necessary
                credentials to validate the signature.
        hdrs:   an arbitrarily ordered list of the names in lowercase of the
                headers whose values were used to generate the signature,
                separated by semicolons (";").
        sgn:    a base 64 encoded string of the HMAC-SHA256 digest generated
                with the necessary credentials following the algorithm
                explained in the function "new_signature".

    Parameters
    ----------
    key_id: str
        Corresponds to the "kid" parameter of the explained format.
    signature: str
        Corresponds to the "sgn" parameter of the explained format.
    signature_headers: List[str], optional
        The arbitrarily ordered list of headers used to generate the signature.
        Its values are used to compose the "hdrs" parameter of the format.

    Returns
    -------
    str
        A string of the format previously explained.
    """
    authorization_header = f"SECCHIWARE-HMAC-256 keyId={key_id},"
    if signature_headers:
        signed_headers = ";".join(h.lower() for h in signature_headers)
        authorization_header = f"{authorization_header}headers={signed_headers},"

    authorization_header = f"{authorization_header}signature={signature}"
    return authorization_header

def verify_authorization_header(
        authorization_header: str,
        key_recoverer: Callable,
        header_recoverer: Callable,
        method: str,
        canonical_URI: str,
        query: str = "",
        mandatory_headers: List[str] = []) -> bool:
    if not authorization_header.startswith("SECCHIWARE-HMAC-256"):
        raise ValueError("Invalid signature algorithm.")

    parameters = authorization_header.split(" ", 1)[1].split(",")

    if not parameters[0].startswith("keyId="):
        raise ValueError("Missing 'keyId' authorization parameter.")
    key = key_recoverer(parameters[0].split("=", 1)[1])
    if key is None:
        raise ValueError("No key matches the given keyId.")

    if not parameters[1].startswith("headers="):
        final_param = 1
        # Can raise ValueError
        signature = new_signature(
            key,
            method,
            canonical_URI,
            query)
    else:
        final_param = 2
        signature_headers = parameters[1].split("=", 1)[1].split(";")
        not_present = {h.lower() for h in mandatory_headers}\
            - {*signature_headers}
        if not_present:
            raise ValueError(f"Mandatory header/s not specified: {','.join(not_present)}")
        try:
            # Can raise ValueError or KeyError
            signature = new_signature(
                key,
                method,
                canonical_URI,
                query,
                signature_headers,
                header_recoverer)
        except KeyError as e:
            raise ValueError(f"{str(e)} header specified but not present.")

    if not parameters[final_param].startswith("signature="):
        raise ValueError("Missing 'signature' authorization parameter.")
    given_signature = parameters[final_param].split("=", 1)[1]

    return signature == given_signature