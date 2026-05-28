from fastapi import FastAPI,Depends,HTTPException,Request,UploadFile,File,Form
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select,func
from fastapi.middleware.cors import CORSMiddleware
import models,schemas,auths
from typing_extensions import Annotated,List,Optional
from database import Base,engine,get_db
from datetime import datetime,timedelta


app = FastAPI()

# Allow all origins (⚠️ not recommended for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all domains
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

Base.metadata.create_all(engine)

db_dependency = Annotated[Session,Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/user/Login/')

# app.mount("/media", StaticFiles(directory="media"), name="media")

@app.post('/user/Signup/',tags=['Auth'],status_code=200)
async def createUser(req:schemas.User,user_agent:Request,db:db_dependency):
    user = db.query(models.User).filter(models.User.username==req.username).first()
    if user:
        raise HTTPException(status_code=400,detail="Username is already used.")
    new_user = models.User(
        username=req.username,
        password=auths.hashed_password(req.password),
        email=req.email,
        firstname=req.firstname,
        lastname=req.lastname,
        address=req.address,
        device_id=req.device_id,
    )
    new_log = models.Log(
        status="Account created.",
        user_agent=str(user_agent.headers.get("user-agent"))
    )
    new_user.logs.append(new_log)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "detail":"User created."
    }

@app.post('/user/Login/',tags=['Auth'],response_model=schemas.Token)
async def loginUser(request:Annotated[OAuth2PasswordRequestForm,Depends()],user_agent:Request,db:db_dependency):
    user = auths.authenticate_user(username=request.username,password=request.password,db=db)
    ref_time = datetime.utcnow() - timedelta(minutes=5)
    if user is not False:
        latest_log = db.query(models.Log).filter(
            models.Log.user_id == user.user_id
        ).order_by(models.Log.id.desc()).first()
        if latest_log and latest_log.created_at > ref_time and latest_log.status=="Logged in":
            raise HTTPException(status_code=400,detail="Login Session not expired")
        token = auths.create_access_token(user.user_id,user.username,timedelta(minutes=5))
        new_log = models.Log(
            status="Logged in",
            user_id=user.user_id,
            user_agent=str(user_agent.headers.get("user-agent")),
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return schemas.Token(
            access_token=token,
            token_type='bearer'
        )
    else:
        raise HTTPException(status_code=400,detail="Invalid Username or Password.")

@app.post('/user/logout/',tags=['Auth'],status_code=200)
async def logout_user(token:str,user_agent:Request,db:db_dependency):
    username,user_id = auths.verify_token(token)
    user = db.query(models.User).filter(models.User.user_id==user_id).first()
    if user is not None:
        logout_request = models.Log(
            status="Logged out",
            user_agent=str(user_agent.headers.get("user-agent"))
        )
        user.logs.append(logout_request)
        db.add(logout_request)
        db.commit()
        db.refresh(logout_request)
        return {"detail":"Signed out"}
    raise HTTPException(status_code=400,detail="Invalid request.")

@app.post('/add/gaurdians/{gaurdian_name}',tags=['Gaurdians'])
def add_guardian(
    guardian_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    username,user_id = auths.verify_token(token)
    user = db.query(models.User).filter(models.User.user_id==user_id).first()
    if user is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    guardian = db.query(models.User).filter(
        models.User.username == guardian_id
    ).first()
    if not user or not guardian:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.guardians.append(guardian)

    db.commit()

    return {
        "message": "Guardian added successfully"
    }