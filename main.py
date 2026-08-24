from fastapi import FastAPI, Request, WebSocket, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import your modules
from database import (
    engine, SessionLocal, Base,
    User, Ticket, TicketMessage, TicketSolution, AuditLog,
    TicketStatus, TicketPriority, TicketCategory, UserRole
)
from auth import (
    get_db, get_current_user, require_role,
    authenticate_user, create_access_token, get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize app
app = FastAPI(
    title="IT Helpdesk System",
    description="AI-Powered IT Support Ticketing System",
    version="1.0.0"
)

# Set up templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role
    }

@app.post("/register")
async def register(
    email: str,
    full_name: str,
    password: str,
    department: str = None,
    phone: str = None,
    db: Session = Depends(get_db)
):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(password)
    new_user = User(
        email=email,
        full_name=full_name,
        department=department,
        phone=phone,
        hashed_password=hashed_password,
        role=UserRole.STAFF
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log the action
    audit_log = AuditLog(
        user_id=new_user.id,
        action="registered",
        entity_type="user",
        entity_id=new_user.id,
        details=json.dumps({"email": email, "full_name": full_name})
    )
    db.add(audit_log)
    db.commit()

    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name
    }

# ============================================
# TICKET ENDPOINTS
# ============================================

@app.post("/tickets/")
async def create_ticket(
    title: str,
    description: str,
    category: str = "other",
    priority: str = "medium",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate category
    try:
        category_enum = TicketCategory(category.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    # Validate priority
    try:
        priority_enum = TicketPriority(priority.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid priority")

    # Create ticket
    ticket = Ticket(
        title=title,
        description=description,
        category=category_enum,
        priority=priority_enum,
        submitted_by=current_user.id
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Log the action
    audit_log = AuditLog(
        user_id=current_user.id,
        action="created",
        entity_type="ticket",
        entity_id=ticket.id,
        details=json.dumps({"title": title, "category": category})
    )
    db.add(audit_log)
    db.commit()

    return {
        "message": "Ticket created successfully",
        "ticket_id": ticket.id,
        "status": ticket.status.value
    }

@app.get("/tickets/")
async def get_tickets(
    status: str = None,
    category: str = None,
    assigned_to: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Ticket)

    # Filter by status
    if status:
        query = query.filter(Ticket.status == status)

    # Filter by category
    if category:
        query = query.filter(Ticket.category == category)

    # Filter by assignee
    if assigned_to:
        query = query.filter(Ticket.assigned_to == assigned_to)

    # If user is staff, only show their tickets
    if current_user.role == UserRole.STAFF:
        query = query.filter(Ticket.submitted_by == current_user.id)

    tickets = query.order_by(Ticket.created_at.desc()).all()

    result = []
    for ticket in tickets:
        result.append({
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "category": ticket.category.value,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "submitted_by": ticket.submitted_by,
            "submitter_name": ticket.submitter.full_name if ticket.submitter else None,
            "assigned_to": ticket.assigned_to,
            "assignee_name": ticket.assignee.full_name if ticket.assignee else None,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None
        })

    return result

@app.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check permission
    if current_user.role == UserRole.STAFF and ticket.submitted_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this ticket")

    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category.value,
        "priority": ticket.priority.value,
        "status": ticket.status.value,
        "submitted_by": ticket.submitted_by,
        "submitter_name": ticket.submitter.full_name if ticket.submitter else None,
        "assigned_to": ticket.assigned_to,
        "assignee_name": ticket.assignee.full_name if ticket.assignee else None,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "messages": [
            {
                "id": msg.id,
                "message": msg.message,
                "user_id": msg.user_id,
                "user_name": msg.user.full_name if msg.user else None,
                "is_internal": msg.is_internal,
                "created_at": msg.created_at.isoformat()
            }
            for msg in ticket.messages
        ]
    }

@app.put("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    status: str = None,
    priority: str = None,
    assigned_to: int = None,
    current_user: User = Depends(require_role(["it_support", "admin"])),
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Update fields
    if status:
        try:
            ticket.status = TicketStatus(status.lower())
            if status.lower() == "resolved":
                ticket.resolved_at = datetime.utcnow()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")

    if priority:
        try:
            ticket.priority = TicketPriority(priority.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid priority")

    if assigned_to:
        # Verify user exists
        assignee = db.query(User).filter(User.id == assigned_to).first()
        if not assignee:
            raise HTTPException(status_code=404, detail="User not found")
        ticket.assigned_to = assigned_to

    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)

    # Log the action
    audit_log = AuditLog(
        user_id=current_user.id,
        action="updated",
        entity_type="ticket",
        entity_id=ticket.id,
        details=json.dumps({
            "status": status,
            "priority": priority,
            "assigned_to": assigned_to
        })
    )
    db.add(audit_log)
    db.commit()

    return {"message": "Ticket updated successfully", "ticket_id": ticket.id}

@app.post("/tickets/{ticket_id}/messages")
async def add_message(
    ticket_id: int,
    message: str,
    is_internal: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check permission
    if current_user.role == UserRole.STAFF and ticket.submitted_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to comment on this ticket")

    # Create message
    new_message = TicketMessage(
        ticket_id=ticket_id,
        user_id=current_user.id,
        message=message,
        is_internal=is_internal
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "message": "Message added",
        "message_id": new_message.id,
        "created_at": new_message.created_at.isoformat()
    }

# ============================================
# USER ENDPOINTS
# ============================================

@app.get("/users/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "department": current_user.department,
        "phone": current_user.phone,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat()
    }

@app.get("/users/")
async def get_users(
    current_user: User = Depends(require_role(["admin", "it_support"])),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role.value,
            "is_active": user.is_active
        }
        for user in users
    ]

# ============================================
# WEB INTERFACE
# ============================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ============================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"User {user_id}: {data}")
    except Exception as e:
        manager.disconnect(websocket)

# ============================================
# STARTUP EVENTS
# ============================================

@app.on_event("startup")
async def startup_event():
    print(f"🚀 Server started : {datetime.now()}")

@app.on_event("shutdown")
async def shutdown_event():
    print(f"🛑 Server Shutdown : {datetime.now()}")

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)