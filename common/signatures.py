import hmac

from base64 import b64encode
from typing import Callable, List
from urllib import parse


def new_signature(
        keyID: str,
        key_recoverer: Callable,
        method: str,
        canonical_URI: str,
        query: str = "",
        signature_headers: List[str] = [],
        header_recoverer: Callable = None) -> str:
    key = key_recoverer(keyID)
    if key is None:
        raise ValueError("No key mathes the given keyID.")
    signature_str = f"{method.lower()}\n{canonical_URI}\n"
    if query:
        # Canonical query string should be URL-encoded (space=%20)
        signature_str = f"{signature_str}{parse.quote(query)}\n"

    if signature_headers:
        if header_recoverer is None:
            raise TypeError("'header_recoverer' is None but 'signature_headers' is not empty.")
        for h in signature_headers:
            h = h.lower()
            # Can raise KeyError
            signature_str = f"{signature_str}{h}: {header_recoverer(h)}\n"

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
            query: str = "") -> bool:
    if not authorization_header.startswith("SECCHIWARE-HMAC-256"):
        raise ValueError("Invalid signature algorithm.")

    parameters = authorization_header.split(" ")[1].split(",")

    if not parameters[0].startswith("keyId="):
        raise ValueError("Missing 'keyId' authorization parameter.")
    keyID = parameters[0].split("=")[1]

    if not parameters[1].startswith("headers="):
        final_param = 1
        # Can raise ValueError or KeyError
        signature = new_signature(
            keyID,
            key_recoverer,
            method,
            canonical_URI,
            query)
    else:
        final_param = 2
        signature_headers = parameters[1].split("=")[1].split(";")
        # Can raise ValueError or KeyError
        signature = new_signature(
            keyID,
            key_recoverer,
            method,
            canonical_URI,
            query,
            signature_headers,
            header_recoverer)

    if not parameters[final_param].startswith("signature="):
        raise ValueError("Missing 'signature' authorization parameter.")
    given_signature = parameters[final_param].split("=")[1]

    return signature == given_signature