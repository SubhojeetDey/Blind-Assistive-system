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

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl='/user/Login/',
    scheme_name="userAuth"
)

driver_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl='/driver/Login/',
    scheme_name="driverAuth"
)

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

@app.post('/driver/Signup/',tags=['Auth'],status_code=200)
async def createUser(req:schemas.User,user_agent:Request,db:db_dependency):
    user = db.query(models.Driver).filter(models.Driver.username==req.username).first()
    if user:
        raise HTTPException(status_code=400,detail="Username is already used.")
    new_user = models.Driver(
        username=req.username,
        password=auths.hashed_password(req.password),
        email=req.email,
        firstname=req.firstname,
        lastname=req.lastname,
        address=req.address,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "detail":"User created."
    }

@app.post('/driver/Login/',tags=['Auth'],response_model=schemas.Token)
async def loginUser(request:Annotated[OAuth2PasswordRequestForm,Depends()],user_agent:Request,db:db_dependency):
    user = auths.authenticate_driver(username=request.username,password=request.password,db=db)
    ref_time = datetime.utcnow() - timedelta(minutes=5)
    if user is not False:
        token = auths.create_access_token(user.user_id,user.username,timedelta(minutes=5))
        return schemas.Token(
            access_token=token,
            token_type='bearer'
        )
    else:
        raise HTTPException(status_code=400,detail="Invalid Username or Password.")

@app.post('/create/ride/{device_id}&current_location={current_location}',tags=['Ride'])
def create_ride(
    current_location: str,
    device_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.device_id==device_id).first()
    if user is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    new_ride = models.Ride(
        current_location=current_location,
        user_id=user.user_id
    )
    db.add(new_ride)
    db.commit()
    db.refresh(new_ride)
    return {
        "message": "Ride created successfully",
        "ride_id": new_ride.id
    }

@app.post('/driver/accept/ride/{ride_id}',tags=['Ride'])
def accept_ride(
    ride_id: int,
    token: str = Depends(driver_oauth2_scheme),
    db: Session = Depends(get_db)
):
    username,user_id = auths.verify_token(token)
    driver = db.query(models.Driver).filter(models.Driver.user_id==user_id).first()
    if driver is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    ride = db.query(models.Ride).filter(models.Ride.id==ride_id).first()
    if ride is None:
        raise HTTPException(status_code=404,detail="Ride not found.")
    if ride.driver_id is not None:
        raise HTTPException(status_code=400,detail="Ride already accepted.")
    ride.driver_id = user_id
    ride.status = "Accepted"
    db.commit()
    db.refresh(ride)
    return {
        "message": "Ride accepted successfully"
    }

@app.get('/driver/rides/',tags=['Ride'])
def get_driver_rides(
    token: str = Depends(driver_oauth2_scheme),
    db: Session = Depends(get_db)
):
    username,user_id = auths.verify_token(token)
    driver = db.query(models.Driver).filter(models.Driver.user_id==user_id).first()
    if driver is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    rides = db.query(models.Ride).filter(
        models.Ride.driver_id == None,
        models.Ride.status == None
    ).all()

    ride_requests = []
    for ride in rides:
        if ride.user is None:
            continue
        ride_requests.append({
            "user": {
                "username": ride.user.username,
                "firstname": ride.user.firstname,
                "lastname": ride.user.lastname,
                "phone_number": ride.user.phone_number,
            },
            "current_location": ride.current_location
        })

    return ride_requests

@app.delete('/user/delete/ride/',tags=['Ride'])
def delete_ride(
    device_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.device_id==device_id).first()
    if user is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    ride = db.query(models.Ride).filter(models.Ride.user_id==user.user_id,models.Ride.status==None).first()
    if ride is None:
        raise HTTPException(status_code=404,detail="Ride not found.")
    db.delete(ride)
    db.commit()
    return {
        "message": "Ride deleted successfully"
    }

@app.post('/update/Location/{device_id}&current_location={current_location}',tags=['User'])
def update_location(
    current_location: str,
    device_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.device_id==device_id).first()
    if user is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    user.current_location = current_location
    db.commit()
    db.refresh(user)
    return {
        "message": "Location updated successfully"
    }

@app.get('/get/current/location/{device_id}',tags=['User'])
def get_current_location(
    device_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.device_id==device_id).first()
    if user is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    return {
        "current_location": user.current_location
    }

@app.get('/get/user/details/',tags=['User'])
def get_all_user_details(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    username,user_id = auths.verify_token(token)
    user = db.query(models.User).filter(models.User.user_id==user_id).first()
    if user is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    return {
        "username": user.username,
        "email": user.email,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "phone_number": user.phone_number,
        "address": user.address,
        "current_location": user.current_location
    }

@app.get('/get/current_location/',tags=['Gaurdians'],response_model=List[schemas.User_req])
def get_current_location(
    db:db_dependency,
    token:str = Depends(oauth2_scheme)
):
    username,user_id = auths.verify_token(token)
    gaurdian = db.query(models.User).filter(models.User.user_id == user_id).first()
    if gaurdian is None:
        raise HTTPException(status_code=404,detail="Gaurdian not found.")
    user = gaurdian.children
    return user

@app.post('/create/notification/{device_id}&message={message}',tags=['Notification'])
def create_notification(
    device_id: str,
    message: str,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.device_id==device_id).first()
    if user is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    new_notification = models.Notifications(
        message=message,
        user_id=user.user_id
    )
    db.add(new_notification)
    db.commit()
    db.refresh(new_notification)
    return {
        "message": "Notification created successfully"
    }

@app.get('/get/notifications/',tags=['Notification'])
def get_notifications(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    username,user_id = auths.verify_token(token)
    user = db.query(models.User).filter(models.User.user_id==user_id).first()
    if user is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    id = user.children[0].user_id if user.children else None
    notifications = db.query(models.Notifications).filter(models.Notifications.user_id==user_id).all()
    return [
        {
            "message": notification.message,
            "created_at": notification.created_at
        }
        for notification in notifications
    ]

@app.get('/get/driver/details/',tags=['Driver'])
def get_driver_details(
    token: str = Depends(driver_oauth2_scheme),
    db: Session = Depends(get_db)
):
    username,user_id = auths.verify_token(token)
    driver = db.query(models.Driver).filter(models.Driver.user_id==user_id).first()
    if driver is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    return {
        "username": driver.username,
        "email": driver.email,
        "firstname": driver.firstname,
        "lastname": driver.lastname,
        "address": driver.address
    }

@app.get('/get/guardian/getallusers',tags=['Gaurdians'])
def get_all_users(
     token: str = Depends(oauth2_scheme),
     db: Session = Depends(get_db)
):
    username,user_id = auths.verify_token(token)
    gaurdian = db.query(models.User).filter(models.User.user_id == user_id).first()
    if gaurdian is None:
        raise HTTPException(status_code=404,detail="Gaurdian not found.")
    users = db.query(models.User).all()
    return [
        {
            "username": user.username,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "phone_number": user.phone_number,
            "current_location": user.current_location
        }
        for user in users
    ]

@app.post('/get/ride/finished/',tags=['Ride'])
def finish_ride(
    token: str = Depends(driver_oauth2_scheme),
    db: Session = Depends(get_db)
):
    username,user_id = auths.verify_token(token)
    driver = db.query(models.Driver).filter(models.Driver.user_id==user_id).first()
    if driver is None:
        raise HTTPException(status_code=401,detail="Unauthorized.")
    ride = db.query(models.Ride).filter(models.Ride.driver_id==user_id,models.Ride.status=="Accepted").first()
    if ride is None:
        raise HTTPException(status_code=404,detail="Ride not found.")
    if ride.driver_id != user_id:
        raise HTTPException(status_code=403,detail="Forbidden.")
    ride.status = "Finished"
    new_notification = models.Notifications(
        message="Your ride has been marked as finished.",
        user_id=ride.user_id
    )
    db.add(new_notification)    
    db.commit()
    db.refresh(ride)
    return {
        "message": "Ride marked as finished"
    }