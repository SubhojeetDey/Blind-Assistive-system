from pydantic import BaseModel,Field,EmailStr
from typing_extensions import Dict,Any

class User(BaseModel):
    username:str
    password:str
    email:str
    firstname:str
    phone_number:str
    lastname:str
    address:str
    device_id:str|None = None

    class Config:
        from_attributes = True

class User_req(BaseModel):
    username:str
    firstname:str
    lastname:str
    phone_number:str|None
    current_location:str|None

    class Config:
        from_attributes = True
    
class Token(BaseModel):
    access_token:str
    token_type:str

    class Config:
        from_attributes = True

class rideRequest(BaseModel):
    user:User_req
    current_location:str

    class Config:
        from_attributes = True