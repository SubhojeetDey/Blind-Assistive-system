from pydantic import BaseModel,Field,EmailStr
from typing_extensions import Dict,Any

class User(BaseModel):
    username:str
    password:str
    email:str
    firstname:str
    lastname:str
    address:str
    device_id:str

    class Config:
        from_attributes = True
    
class Token(BaseModel):
    access_token:str
    token_type:str

    class Config:
        from_attributes = True