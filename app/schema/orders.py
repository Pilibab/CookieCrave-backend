from typing import List, Optional
from typing_extensions import TypedDict
from pydantic import EmailStr
from pydantic import BaseModel
from decimal import Decimal
from uuid import UUID


# ==========================================
# RAW DB SHAPES (TypedDict for dict access .get() or [])
# ==========================================

class RawCustomer(TypedDict):
    cust_id: str
    cust_firstname: str
    cust_lastname: str
    cust_email: str

class RawProduct(TypedDict):
    prod_id: int
    prod_name: str
    prod_price_per_item: float

class RawCartItem(TypedDict):
    quantity: int
    products: RawProduct

class RawOrder(TypedDict):
    ord_id: int
    ord_time: str
    total_amount: float
    order_status: str
    customers: RawCustomer
    cart: List[RawCartItem]


# ==========================================
# TARGET API RESPONSES (Pydantic Models)
# ==========================================

class CustomerTarget(TypedDict):
    cust_id: str
    customer_name: str
    email: EmailStr

class CartItemTarget(TypedDict):
    prod_id: int
    prod_name: str
    quantity: int
    prod_price_per_item: float
    subtotal: float

class OrderResponse(TypedDict):
    ord_id: int
    ord_time: str
    total_amount: float
    order_status: str
    customer: CustomerTarget
    cart_items: List[CartItemTarget]

class CreateOrderRequest(BaseModel):
    cust_id: UUID
    total_amount: Decimal
    ord_pay_meth: str           # "GCash" | "Cash"
    ord_f_type: str             # "Delivery" | "Pick_Up"
    prod_ids: List[int]
    reference_no: Optional[str] = None   # required only if GCash
    