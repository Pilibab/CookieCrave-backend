from typing import Any, List, Dict
# from uuid import UUID

from app.repository.orders_repo import OrderRepository
from app.repository.product_repo import ProductRepository
from app.repository.cart_repo import CartRepository # Don't forget to import this!
from app.repository.fullfillment_repo import FulfillmentRepository
from app.model.fullfillement import FulfillmentCreate
from app.model.order import OrderCreate
from app.model.gcash import GCashPaymentCreate
from app.repository.gcash_repo import GCashRepository
from app.schema.orders import RawOrder, OrderResponse, CartItemTarget

from collections import Counter
from pydantic import BaseModel, Field, TypeAdapter
from datetime import datetime
from typing import List

class BillItemDetail(BaseModel):
    product: str = Field(..., description="The name of the cookie product")
    quantity: int = Field(..., description="The number of units ordered")
    prod_price: float = Field(..., description="The unit price of the product")
    subtotal: float = Field(..., description="The combined line total price (quantity * price)")

class FinalBillResponse(BaseModel):
    order_no: int = Field(..., description="The unique database tracking primary ID of the order")
    date: datetime = Field(..., description="The timestamp when the order was created")
    total: float = Field(..., description="The calculated absolute grand total amount of the invoice")
    items: List[BillItemDetail] = Field(..., description="Collection of items itemized in the cart")

    class Config:
        # Allows Pydantic to read standard database attributes or ORM instances directly
        from_attributes = True
class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        prod_repo: ProductRepository,
        cart_repo: CartRepository,
        fulfillment_repo: FulfillmentRepository,
        gcash_repo: GCashRepository
    ):
        self.order_repo = order_repo
        self.prod_repo = prod_repo
        self.cart_repo = cart_repo
        self.fulfillment_repo = fulfillment_repo
        self.gcash_repo = gcash_repo

    # ? wont it be better to fetch also or ensure that the returned query 
    # ? contains cust_id that way we ensure that the grabbed query is made by the customer
    def get_final_bill(self, order_id: int) -> FinalBillResponse:
        # 1. Fetch data
        order = self.order_repo.get_by_id(order_id)
        
        # Guard clause: Check if order exists before accessing attributes
        if not order:
            raise ValueError(f"Order with ID {order_id} not found.")

        items = self.cart_repo.get_items_by_order(order_id)
        
        bill_details: List[BillItemDetail] = []
        grand_total: float = 0.0

        # 2. Stitch the data together
        for item in items:
            product = self.prod_repo.get_by_id(item.prod_id)
            
            # Guard clause: Check if product exists in inventory
            if product is None:
                continue # Skip this item if product doesn't exist
            
            line_total = float(item.cart_quan * product.prod_price)
            grand_total += line_total
            
            bill_details.append(BillItemDetail(                
                product= product.prod_name,
                quantity= item.cart_quan,
                prod_price= product.prod_price,
                subtotal= line_total))

        return FinalBillResponse(
            order_no=order.ord_id,
            date=order.ord_time,
            total=grand_total,
            items=bill_details
        )

    def create_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        try:             
            fulfillment = self.fulfillment_repo.create(
                FulfillmentCreate(fulfillment_type=order_details["ord_f_type"])
            )

            order_to_create = OrderCreate(
                cust_id=order_details["cust_id"],
                total_amount=order_details["total_amount"],
                payment_method=order_details["ord_pay_meth"],
                fulfillment_id=fulfillment.fulfillment_id
            )

            new_order = self.order_repo.create(order_to_create)

            # populate cart
            ordered_prod = order_details["prod_ids"]
            prod_counts : Counter[int]  = Counter(ordered_prod)  # ← was commented out by mistake
            cart_items : list[dict[str, int]]  = [{"prod_id": pid, "cart_quan": qty} for pid, qty in prod_counts.items()]
            self.cart_repo.create_order_line(order_id=new_order.ord_id, items=cart_items)

            if order_details["ord_pay_meth"] == "GCash":
                reference_no = order_details.get("reference_no")
                if not reference_no:
                    raise ValueError("GCash payment requires a reference number.")
                data = GCashPaymentCreate(
                    ord_id=new_order.ord_id,
                    reference_no=reference_no,
                    amount=order_details["total_amount"]
                )
                self.gcash_repo.create(data)

            return {
                "status": "Success",
                "order_id": new_order.ord_id,
                "time": new_order.ord_time
            }
        
        except Exception as e:
            return {
                "status": "Failed",
                "error": str(e)
            }

    def get_admin_dashboard_orders(self, page: int = 1, page_size: int = 20):
        offset = (page - 1) * page_size
        # 1 Single repository call executes the optimized JOIN
        raw_rows = self.order_repo.get_orders_with_details(limit=page_size, offset=offset)
        
        # Group flat SQL rows into nested Order objects
        return self._format_orders_dto(raw_rows)
        # return raw_rows

    def _format_orders_dto(self, raw_rows: List[Dict[str, Any]]): 
        """
            format raw supabase response to what the frontend wants 
        """
        parsed_raw_orders: list[RawOrder] = TypeAdapter(list[RawOrder]).validate_python(raw_rows)

        formatted_orders : List[OrderResponse] = []

        for row in parsed_raw_orders:
            # get customer data 
            customer_data = row.get("customers") or {}

            formatted_items: List[CartItemTarget] = []
            for cart_item in row.get("cart", []):
                product_data = cart_item.get("products") or {}
                quantity = cart_item.get("quantity", 0)
                unit_price = float(product_data.get("prod_price_per_item", 0.0))

                # has the schema of CartItemTarget
                formatted_items.append({
                    "prod_id": product_data.get("prod_id"),
                    "prod_name": product_data.get("prod_name"),
                    "quantity": quantity,
                    "prod_price_per_item": unit_price,
                    "subtotal": quantity * unit_price,
                })

            # has the schema of OrderResponse
            formatted_orders.append({
                "ord_id": row.get("ord_id"),
                "ord_time": row.get("ord_time"),
                "total_amount": row.get("total_amount"),
                "order_status": row.get("order_status"),
                "customer": {
                    "cust_id": customer_data.get("cust_id"),
                    "customer_name": f"{customer_data.get('cust_firstname', '')} {customer_data.get('cust_lastname', '')}".strip(),
                    "email": customer_data.get("cust_email"),
                },
                "cart_items": formatted_items,
            })

        return formatted_orders


