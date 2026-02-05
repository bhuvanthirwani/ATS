
from fastapi import Header, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from src.db.session import get_db, CONFIG_PATH
from src.db.models import User
import json

# Load Config
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)
    SECRET_KEY = config.get("jwt_secret")
    ALGORITHM = config.get("algorithm", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # We use the 'sub' claim for user_id (as string) or username.
        # Let's assume sub is the ID string (from database ID).
        # However, to keep file system compatibility for now, we can use the username as the workspace folder name? 
        # Or better: "user_{id}". 
        
        # User requested Workspace ID workflow: "Registration ... username unique"
        # We will use the 'username' as the folder name / workspace ID for readability and simplicity? 
        # Or cleaner: "u_{id}". 
        
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username


# Alias for compatibility with existing endpoints calling get_current_workspace
# This ensures that all existing endpoints now require a valid JWT.
async def get_current_workspace(current_user: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    # Optional: Check if user exists in DB to be sure (token might be stale)
    # user = db.query(User).filter(User.username == current_user).first()
    # if not user: raise ...
    
    # We return the username as the Workspace ID 
    # Existing logic expects a string.
    return current_user

def get_current_user(username: str = Depends(get_current_user_id), db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


