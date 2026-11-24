import os
import shutil
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Dict

from .database import init_db, SessionLocal
from .models import RawFile, ProcessedFile, JobLog
from .myntra_matching import MyntraMatcher

app = FastAPI(title="Excel Matcher API")

# Security
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")  # Should be set in environment
ALGORITHM = "HS256"

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        # You can add more validation here (e.g., expiration)
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize DB tables on startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Ensure upload folder exists
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

@app.post("/process", summary="Upload raw Excel and run matcher")
async def process_excel(
    raw_file: UploadFile = File(...),
    info: Dict = {},
    user: dict = Depends(get_current_user),
    db: SessionLocal = Depends(get_db),
):
    # Save uploaded file
    upload_path = os.path.join("uploads", raw_file.filename)
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(raw_file.file, buffer)

    # Record raw file
    raw_record = RawFile(filename=raw_file.filename, path=upload_path)
    db.add(raw_record)
    db.commit()
    db.refresh(raw_record)

    # Log job start
    job_log = JobLog(raw_file_id=raw_record.id, status="pending", message="Job started")
    db.add(job_log)
    db.commit()
    db.refresh(job_log)

    output_path = os.path.join("outputs", f"processed_{raw_file.filename}")

    try:
        matcher = MyntraMatcher(name="API")
        # The matcher expects a dict for info; the endpoint receives a JSON body but FastAPI will parse query params.
        matcher.matching(upload_path, output_path, info)
    except ValueError as ve:
        # Missing column error expected
        job_log.status = "error"
        job_log.message = str(ve)
        db.commit()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        job_log.status = "error"
        job_log.message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail="Internal server error")

    # Record processed file
    processed_record = ProcessedFile(raw_file_id=raw_record.id, output_path=output_path)
    db.add(processed_record)
    job_log.status = "success"
    job_log.message = "Processing completed"
    db.commit()

    return FileResponse(output_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=os.path.basename(output_path))
