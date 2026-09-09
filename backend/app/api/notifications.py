# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session
# from app.database.connection import get_db
# from app.database.models import PushSubscriptionModel

# router = APIRouter()

# @router.post("/subscribe")
# def save_subscription(data: dict, db: Session = Depends(get_db)):
#     # Save or update subscription data for the current user
#     sub = PushSubscriptionModel(user_id=data.get("user_id"), subscription_data=data)
#     db.add(sub)
#     db.commit()
#     return {"status": "subscribed"}