from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import create_tables, get_db
from .routers import auth, data, admin
from .routers.log import router as log_router
from .routers.dvc_remote import router as dvc_remote_router
from .auth import get_current_user_for_template
from .config import config

app = FastAPI(title="RINT Data Manager", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors.get('allowed_origins', []),
    allow_credentials=True,
    allow_methods=config.cors.get('allowed_methods', []),
    allow_headers=config.cors.get('allowed_headers', []),
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(dvc_remote_router, prefix="/dvc", tags=["dvc_remote"])
app.include_router(log_router, prefix="/api/log", tags=["log"])


@app.on_event("startup")
def startup_event():
    import logging
    import logging.handlers
    from pathlib import Path
    from .config import config
    
    # Setup logging configuration
    logging_config = config.logging
    log_file = logging_config.get('file', 'log/app.log')
    log_level = logging_config.get('level', 'INFO')
    log_format = logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Ensure log directory exists
    if log_file:
        log_path = Path(log_file)
        if log_path.suffix:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    if log_level:
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    else:
        root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=200 * 1024 * 1024,  # 200MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Log that logging has been set up
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")
    
    create_tables()


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_for_template(request, db)
    print(f"Current user in root: {current_user}")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_for_template(request, db)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_for_template(request, db)
    return templates.TemplateResponse("register.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/register-admin", response_class=HTMLResponse)
async def register_admin_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_for_template(request, db)
    return templates.TemplateResponse("register-admin.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_for_template(request, db)
    print(f"Current user in dashboard: {current_user}")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_for_template(request, db)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/usage", response_class=HTMLResponse)
async def usage_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_for_template(request, db)
    return templates.TemplateResponse("usage.html", {
        "request": request,
        "current_user": current_user
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,
                host=config.server.get('host', '0.0.0.0'),
                port=config.server.get('port', 8000),
                reload=config.server.get('reload', True),
                log_config="../uvicorn_log_config.json")
