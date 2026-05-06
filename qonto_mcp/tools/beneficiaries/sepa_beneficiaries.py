import uuid
from typing import List, Optional

import requests
from requests.exceptions import RequestException

import qonto_mcp
from qonto_mcp import mcp


@mcp.tool()
def create_qonto_sepa_beneficiary(
    name: str,
    iban: str,
    bic: Optional[str] = None,
    email: Optional[str] = None,
    activity_tag: Optional[str] = None,
):
    """
    Creates a new SEPA beneficiary in the organization's address book.

    The new beneficiary lands in `status="pending"` until validated by the
    first SCA-protected transfer or a successful trust action.

    Args:
        name: Beneficiary display name (required).
        iban: Beneficiary IBAN, ISO 13616 (required).
        bic: Optional BIC/SWIFT code; usually inferred from the IBAN.
        email: Optional contact email for the beneficiary.
        activity_tag: Optional category tag (e.g. "utility", "supplier").

    Returns:
        The Qonto API response containing the created beneficiary, including
        `id`, `status` ("pending" | "validated" | "declined") and `trusted`.

    Example:
        create_qonto_sepa_beneficiary(
            name="Acme SARL",
            iban="FR7630003035409876543210982",
            activity_tag="supplier",
        )
    """
    if not name:
        raise ValueError("`name` is required.")
    if not iban:
        raise ValueError("`iban` is required.")

    payload = {"name": name, "iban": iban}
    if bic:
        payload["bic"] = bic
    if email:
        payload["email"] = email
    if activity_tag:
        payload["activity_tag"] = activity_tag

    url = f"{qonto_mcp.thirdparty_host}/v2/sepa/beneficiaries"
    headers = {**qonto_mcp.headers, "X-Qonto-Idempotency-Key": str(uuid.uuid4())}

    try:
        response = requests.post(url, headers=headers, json={"beneficiary": payload})
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        raise RuntimeError(qonto_mcp.format_qonto_error("create SEPA beneficiary", e))


@mcp.tool()
def trust_qonto_sepa_beneficiaries(beneficiary_ids: List[str]):
    """
    Marks one or more SEPA beneficiaries as trusted, allowing future transfers
    to them without per-transfer SCA.

    ⚠️ Per Qonto's documentation, this endpoint is "only available for our
    Embed partners" and requires the `beneficiary.trust` scope. On a standard
    API key, expect HTTP 403 — in that case, beneficiaries can still be used
    to draft multi-transfer requests, which carry their own approval flow.

    Args:
        beneficiary_ids: List of beneficiary UUIDs (1–400 items).

    Returns:
        The Qonto API response with the updated `beneficiaries` array.

    Example:
        trust_qonto_sepa_beneficiaries(
            beneficiary_ids=["e72f6e43-0f27-4415-8781-ad648a89b47f"]
        )
    """
    if not beneficiary_ids:
        raise ValueError("`beneficiary_ids` must contain at least one UUID.")
    if len(beneficiary_ids) > 400:
        raise ValueError(
            f"`beneficiary_ids` contains {len(beneficiary_ids)} items; "
            "the API accepts at most 400."
        )

    url = f"{qonto_mcp.thirdparty_host}/v2/sepa/beneficiaries/trust"
    body = {"ids": beneficiary_ids}

    try:
        response = requests.patch(url, headers=qonto_mcp.headers, json=body)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        raise RuntimeError(qonto_mcp.format_qonto_error("trust SEPA beneficiaries", e))


@mcp.tool()
def update_qonto_sepa_beneficiary(
    beneficiary_id: str,
    name: str,
    email: Optional[str] = None,
    activity_tag: Optional[str] = None,
):
    """
    Updates editable fields of an existing SEPA beneficiary.

    Only `name`, `email`, and `activity_tag` are editable. To change the
    `iban` or `bic`, create a new beneficiary instead — those fields define
    the beneficiary's identity.

    Args:
        beneficiary_id: UUID of the beneficiary to update.
        name: New display name (required by the API even on partial updates).
        email: Optional new contact email.
        activity_tag: Optional new category tag.

    Returns:
        The Qonto API response containing the updated beneficiary.

    Example:
        update_qonto_sepa_beneficiary(
            beneficiary_id="e72f6e43-0f27-4415-8781-ad648a89b47f",
            name="Acme SARL",
            activity_tag="utility",
        )
    """
    if not beneficiary_id:
        raise ValueError("`beneficiary_id` is required.")
    if not name:
        raise ValueError("`name` is required.")

    payload = {"name": name}
    if email is not None:
        payload["email"] = email
    if activity_tag is not None:
        payload["activity_tag"] = activity_tag

    url = f"{qonto_mcp.thirdparty_host}/v2/sepa/beneficiaries/{beneficiary_id}"

    try:
        response = requests.patch(
            url, headers=qonto_mcp.headers, json={"beneficiary": payload}
        )
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        raise RuntimeError(qonto_mcp.format_qonto_error("update SEPA beneficiary", e))
