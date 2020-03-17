import hmac

from base64 import b64encode
from typing import Callable, List
from urllib import parse


def new_signature(
        key: bytes,
        method: str,
        canonical_URI: str,
        query: str = "",
        signature_headers: List[str] = [],
        header_recoverer: Callable = None) -> str:
    signature_str = f"{method.lower()}\n{canonical_URI}\n"
    if query:
        # Canonical query string should be URL-encoded (space=%20)
        signature_str = f"{signature_str}{parse.quote(query)}\n"

    if signature_headers:
        if header_recoverer is None:
            raise TypeError("'header_recoverer' is None but 'signature_headers' is not empty.")
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
        keyID: str,
        signature: str,
        signature_headers: List[str] = []) -> str:
    authorization_header = f"SECCHIWARE-HMAC-256 keyId={keyID},"
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
        raise ValueError("No key mathes the given keyID.")

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