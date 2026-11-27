# HealthSpeak AI – Backend API Testing Guide

## 1. Overview

This document explains how to run and test the HealthSpeak AI backend APIs using FastAPI Swagger UI.

## 2. Technologies

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Uvicorn

## 3. Start the Backend

From the `backend` directory, run:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend URL: http://127.0.0.1:8000

Swagger documentation: http://127.0.0.1:8000/docs

## 4. API Categories

| Category | Purpose |
|---|---|
| Health | Backend and database health checks |
| Authentication | Login, logout and password reset |
| Users | User profile and preferences |
| Patients | Patient registration, profile and consent |
| Intake | Conversations, messages and intake processing |
| Departments | Department and routing rule management |
| Visits | Queue, appointments and doctor schedules |
| Kiosks | Kiosk management and heartbeat |
| AI | AI service status |
| Admin | User and system management |

## 5. Important API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend health |
| GET | `/api/health/db` | Check database connection |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/users/me` | Get current user |
| PATCH | `/api/users/me/preferences` | Update preferences |
| POST | `/api/patients/register` | Register patient |
| GET | `/api/patients/me` | Get patient profile |
| GET | `/api/intakes` | List intake records |
| GET | `/api/departments` | List departments |
| GET | `/api/queue` | View queue |
| GET | `/api/appointments` | View appointments |
| GET | `/api/ai/status` | Check AI service status |

Note: Some endpoints require authentication and specific user roles.

## 6. Testing with Swagger UI

1. Start the backend server.
2. Open http://127.0.0.1:8000/docs.
3. Select an API endpoint.
4. Click **Try it out**.
5. Enter the required request data.
6. Click **Execute**.
7. Check the response code and response body.

## 7. Login API Example

Endpoint: `POST /api/auth/login`

Example request:

```json
{
  "identifier": "admin@example.com",
  "password": "YOUR_DEMO_PASSWORD"
}
```

A successful login returns HTTP `200 OK` and authentication response data.

Never share access tokens or real passwords.

## 8. Common HTTP Status Codes

| Status | Meaning |
|---|---|
| 200 | Request successful |
| 201 | Resource created |
| 202 | Request accepted |
| 204 | Successful request with no response body |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Resource not found |
| 422 | Validation error |
| 500 | Internal server error |

## 9. Testing Checklist

- [ ] Backend server starts successfully.
- [ ] Health API returns a successful response.
- [ ] Database health API works.
- [ ] Admin login works.
- [ ] Authenticated user endpoint works.
- [ ] Role-based access is checked.
- [ ] Invalid request data is tested.

## 10. Important Notes

- Use synthetic demo accounts for local testing.
- Do not commit `.env` files or expose credentials.
- Do not share authentication tokens.
- Review draft department routing rules with clinicians before production use.

---

**Document purpose:** Provide a practical reference for testing HealthSpeak AI backend APIs during development.