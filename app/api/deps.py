from fastapi import Depends
from supabase.client import Client
# from typing import Optional, Any
# from app.config import configs
from app.db.supabase_client import supabase
from app.repository.staff_repo import StaffRepository
from app.repository.product_repo import ProductRepository
from app.repository.cart_repo import CartRepository
from app.repository.fullfillment_repo import FulfillmentRepository
from app.repository.gcash_repo import GCashRepository
from app.db.supabase_client import supabase
from supabase import Client
from app.repository.orders_repo import OrderRepository
from app.service.order_service import OrderService



def get_supabase():
    """Returns the globally initialized supabase client."""
    return supabase

# Helper to provide the repository instance
def get_staff_repository(supabase_client: Client = Depends(get_supabase)) -> StaffRepository:
    return StaffRepository(supabase_client)


def get_order_service(supabase: Client = Depends(get_supabase)) -> OrderService:
    return OrderService(
        order_repo=OrderRepository(supabase),
        prod_repo=ProductRepository(supabase),
        cart_repo=CartRepository(supabase),
        fulfillment_repo=FulfillmentRepository(supabase),
        gcash_repo=GCashRepository(supabase),
    )


def get_order_repository(supabase: Client = Depends(get_supabase)) -> OrderRepository:
    """Provides an instance of the OrderRepository with the database connection injected."""
    return OrderRepository(supabase)