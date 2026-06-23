# FastAPI React Sample

Small fixture repository for AI Codebase Assistant MVP testing.

## Architecture

The frontend has a login page that calls the backend authentication API.
The backend exposes FastAPI routes, delegates credential verification to `AuthService`,
and uses `User` model data for authentication.

## Login Flow

1. `LoginPage.tsx` calls `authApi.login`.
2. `authApi.login` sends `POST /api/auth/login`.
3. `routes.py` receives the request and calls `AuthService.authenticate_user`.
4. `security.py` creates an access token when authentication succeeds.
