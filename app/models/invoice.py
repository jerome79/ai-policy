from decimal import Decimal

from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    description: str
    amount: Decimal = Field(ge=0)


class InvoiceWorkflowInput(BaseModel):
    invoice_id: str
    vendor_id: str
    amount: Decimal = Field(ge=0)
    currency: str = "USD"
    requestor_id: str
    line_items: list[InvoiceLineItem] = Field(default_factory=list)


class InvoiceProcessingOutput(BaseModel):
    invoice_id: str
    status: str
    summary: str
