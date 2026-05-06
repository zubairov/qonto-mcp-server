import uuid
from typing import Any, Dict, List, Optional

import requests
from requests.exceptions import RequestException

import qonto_mcp
from qonto_mcp import mcp


@mcp.tool()
def create_qonto_multi_transfer_request(
    note: str,
    transfers: List[Dict[str, Any]],
    scheduled_date: Optional[str] = None,
    debit_iban: Optional[str] = None,
):
    """
    Creates a multi-transfer request that lands in `pending` status, awaiting
    manual approval by a teammate with review permissions in the Qonto app.

    No money moves until a human approves the request. Use this to let an
    automated workflow prepare and pre-configure transfers while keeping the
    final go/no-go decision in human hands.

    Args:
        note: Description of the request shown to the approver (required).
        transfers: List of transfers (1–400). Each item is a dict with:
            - amount (str, required): Decimal with up to 2 digits, e.g. "1234.56"
            - currency (str, required): ISO 4217; only "EUR" is accepted today
            - credit_iban (str, required): Beneficiary IBAN
            - credit_account_name (str, required, ≤140 chars): Beneficiary name
            - credit_account_currency (str, required): Only "EUR" today
            - reference (str, required, ≤140 chars): Transfer reference
            - attachment_ids (list[str], optional): UUIDs of pre-uploaded
              attachments to link to this transfer
        scheduled_date: Optional execution date in YYYY-MM-DD format. Defaults
            to the current date or next banking day.
        debit_iban: Optional IBAN of the account to debit. Defaults to the
            organization's primary account.

    Returns:
        The Qonto API response containing the created request, including its
        `id` (use with `get_request` to inspect later) and `status="pending"`.

    Example:
        create_qonto_multi_transfer_request(
            note="March supplier payments",
            transfers=[
                {
                    "amount": "1500.00",
                    "currency": "EUR",
                    "credit_iban": "FR7630003035409876543210982",
                    "credit_account_name": "Acme SARL",
                    "credit_account_currency": "EUR",
                    "reference": "Invoice 2026-03-001",
                }
            ],
            scheduled_date="2026-03-15",
        )
    """
    if not note:
        raise ValueError("`note` must be a non-empty description for the approver.")
    if not transfers:
        raise ValueError("`transfers` must contain at least one transfer.")
    if len(transfers) > 400:
        raise ValueError(
            f"`transfers` contains {len(transfers)} items; the API accepts at most 400."
        )

    payload: Dict[str, Any] = {"note": note, "transfers": transfers}
    if scheduled_date:
        payload["scheduled_date"] = scheduled_date
    if debit_iban:
        payload["debit_iban"] = debit_iban

    body = {"request_multi_transfer": payload}

    url = f"{qonto_mcp.thirdparty_host}/v2/requests/multi_transfers"
    headers = {**qonto_mcp.headers, "X-Qonto-Idempotency-Key": str(uuid.uuid4())}

    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        raise RuntimeError(f"Failed to create multi-transfer request: {str(e)}")
