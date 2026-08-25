# IT Helpdesk System with AI Assistant

A full-featured IT helpdesk ticketing system built with FastAPI, PostgreSQL (Neon), and WebSockets.

## Features
- User registration & JWT authentication
- Ticket creation, viewing, and management
- Role-based access control (Staff, IT Support, Admin)
- Real-time WebSocket updates
- AI-powered assistant (RAG - optional)
- Dark mode Claude-inspired UI

## Tech Stack
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** HTML, CSS, JavaScript (no framework)
- **Deployment:** Render/Railway

## Live Demo
[https://helpdesk-api.onrender.com](https://helpdesk-api.onrender.com)

## Local Setup

1. Clone the repository
2. Create a `.env` file with your database URL
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn main:app --reload`
5. Open: `http://localhost:8000`

## Deploy
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/lemayian23/Help-Desk-Ticketing-System-With-AI-Assistant)

## License
MIT