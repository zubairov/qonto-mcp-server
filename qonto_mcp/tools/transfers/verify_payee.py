from typing import Dict, List

import requests
from requests.exceptions import RequestException

import qonto_mcp
from qonto_mcp import mcp


@mcp.tool()
def verify_qonto_sepa_payee(iban: str, beneficiary_name: str):
    """
    Verifies that a SEPA IBAN belongs to the claimed account holder
    (Verification of Payee / VoP). Use this defensively before drafting a
    transfer to catch typos or fraud-style IBAN swaps.

    The response includes a `match_result` enum and, when applicable, the
    actual name on file at the receiving bank. A `proof_token` (valid 23h)
    is also returned; it is informational here — the multi-transfer-request
    endpoint does not currently consume it.

    Args:
        iban: IBAN of the beneficiary account to verify.
        beneficiary_name: Expected name of the beneficiary (1–140 chars).

    Returns:
        Qonto API response with fields:
            - match_result: one of MATCH_RESULT_MATCH, MATCH_RESULT_CLOSE_MATCH,
              MATCH_RESULT_NO_MATCH, MATCH_RESULT_NOT_POSSIBLE,
              MATCH_RESULT_UNSPECIFIED
            - matched_name: the actual name on file (close-match cases)
            - proof_token.token: opaque token, valid 23h

    Example:
        verify_qonto_sepa_payee(
            iban="FR7630003035409876543210982",
            beneficiary_name="Acme SARL",
        )
    """
    if not iban:
        raise ValueError("`iban` is required.")
    if not beneficiary_name:
        raise ValueError("`beneficiary_name` is required.")
    if len(beneficiary_name) > 140:
        raise ValueError("`beneficiary_name` must be 140 characters or fewer.")

    url = f"{qonto_mcp.thirdparty_host}/v2/sepa/verify_payee"
    body = {"iban": iban, "beneficiary_name": beneficiary_name}

    try:
        response = requests.post(url, headers=qonto_mcp.headers, json=body)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        raise RuntimeError(f"Failed to verify SEPA payee: {str(e)}")


@mcp.tool()
def bulk_verify_qonto_sepa_payees(payees: List[Dict[str, str]]):
    """
    Verifies up to 400 SEPA payees in a single call. Each payee is checked
    for IBAN/name match independently; the response array preserves the `id`
    you provide so results can be correlated back to the input.

    Note: per Qonto, "rate limits will apply to verifications that are not
    followed by a transfer initiation" — use this before drafting transfers,
    not as a generic IBAN-lookup utility.

    Args:
        payees: List (1–400) of dicts, each with:
            - id (str, required): Caller-chosen unique identifier for the item.
              Echoed in the response so you can correlate results.
            - iban (str, required): Beneficiary IBAN.
            - beneficiary_name (str, required, 1–140 chars): Expected name.

    Returns:
        Qonto API response with fields:
            - proof_token.token: opaque token, valid 23h, tied to this exact
              set of payees
            - requests: array of per-payee results, each with `id`,
              `beneficiary_name`, `iban`, and either a `response` (with
              `match_result` and optional `matched_name`) or an `error`
              (with `code`).

    Example:
        bulk_verify_qonto_sepa_payees(payees=[
            {"id": "row-1", "iban": "FR76...", "beneficiary_name": "Acme SARL"},
            {"id": "row-2", "iban": "DE89...", "beneficiary_name": "Beta GmbH"},
        ])
    """
    if not payees:
        raise ValueError("`payees` must contain at least one entry.")
    if len(payees) > 400:
        raise ValueError(
            f"`payees` contains {len(payees)} items; the API accepts at most 400."
        )
    seen_ids = set()
    for i, p in enumerate(payees):
        for field in ("id", "iban", "beneficiary_name"):
            if not p.get(field):
                raise ValueError(
                    f"payees[{i}] is missing required field `{field}`."
                )
        if p["id"] in seen_ids:
            raise ValueError(f"Duplicate id in payees: {p['id']!r}.")
        seen_ids.add(p["id"])

    url = f"{qonto_mcp.thirdparty_host}/v2/sepa/bulk_verify_payee"
    body = {"requests": payees}

    try:
        response = requests.post(url, headers=qonto_mcp.headers, json=body)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        raise RuntimeError(f"Failed to bulk-verify SEPA payees: {str(e)}")
