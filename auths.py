from pwdlib import PasswordHash
from jose import jwt
from typing_extensions import Annotated
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi import HTTPException,Depends
from datetime import datetime,timedelta
import models

pwd_context = PasswordHash.recommended()


SECRET_KEY = "By!Yb-$z6AexKQmjR[w&]Ibs]h[U?nt!"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/Login/')

def hashed_password(password:str):
    return pwd_context.hash(password)

def verify_password(plain_password:str,hashed_password:str):
    return pwd_context.verify(plain_password,hashed_password)

def authenticate_user(username:str,password:str,db:Session):
    user = db.query(models.User).filter(models.User.username == str(username)).first()
    if not verify_password(password,user.password):
        return False
    if user is None:
        return False
    return user

def create_access_token(user_id:str,username:str,expires:timedelta):
    try:
        payload = {'sub':username,'id':user_id}
        expires_delta = datetime.utcnow() + expires
        payload.update({'exp':expires_delta})
        token = jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)
        return token
    except:
        return None

def get_current_user(token:Annotated[str,Depends(oauth2_scheme)]):
    credential_exception = HTTPException(
        status_code=400,
        detail="Invalid token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        decoded = jwt.decode(token,SECRET_KEY,algorithm=ALGORITHM)
        username = decoded.get("sub")
        if username is None:
            raise credential_exception
    except:
        raise credentianl_exception
    user = db.query(models.User).filter(models.User.username==str(username))
    if user is None:
        raise credential_exception
    return user

def verify_token(token:str=Depends(oauth2_scheme)):
    try:
        decoded = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username = decoded.get("sub")
        user_id = decoded.get("id")
        return username,user_id
    except Exception as e:
        raise HTTPException(status_code=401,detail=str(e))

def verify_user(user_id:str,db:Session):
    user = db.query(models.User).filter(models.User.user_id==user_id).first()
    if user is None:
        raise HTTPException(status_code=404,detail="User not Found.")
    return user