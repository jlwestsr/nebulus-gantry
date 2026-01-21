# flake8: noqa: E501
from fastapi import APIRouter, Request, Form, Response, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from ..database import SessionLocal
from ..auth import (
    create_user,
    get_user_count,
    get_user,
    verify_password,
    create_access_token,
    verify_token,
)

import logging

logger = logging.getLogger("uvicorn")

router = APIRouter()


def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    username = verify_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    db = SessionLocal()
    user = get_user(db, username)
    db.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


@router.get("/me")
async def read_users_me(user=Depends(get_current_user)):
    return {
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
    }




def get_login_html(error: str = None):
    error_html = ""
    if error:
        error_html = f"""
            <div class="error-message">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="error-icon"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                <span>{error}</span>
            </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html class="dark">
    <head>
        <title>Nebulus - Login</title>
        <link rel="stylesheet" href="/public/style.css">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
        <style>
            body {{
                display: flex;
                align-items: center;
                justify-content: center;
                background: var(--bg-primary);
                height: 100vh;
            }}
            .auth-card {{
                background: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 40px;
                width: 400px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                text-align: center;
            }}
            .auth-title {{
                font-size: 2rem;
                font-weight: 600;
                color: var(--text-primary);
                margin-bottom: 30px;
            }}
            .auth-form {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}
            .input-group {{
                text-align: left;
            }}
            .input-group label {{
                display: block;
                color: var(--text-secondary);
                font-size: 0.9rem;
                margin-bottom: 8px;
            }}
            .auth-input {{
                width: 100%;
                padding: 12px;
                background: var(--bg-primary);
                border: 1px solid var(--border-color);
                border-radius: 6px;
                color: var(--text-primary);
                font-size: 1rem;
                outline: none;
                transition: border-color 0.2s;
                box-sizing: border-box;
            }}
            .auth-input:focus {{
                border-color: var(--accent-color);
            }}
            .btn-auth {{
                background: var(--accent-color);
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-size: 1rem;
                font-weight: 500;
                cursor: pointer;
                transition: opacity 0.2s;
                margin-top: 10px;
            }}
            .btn-auth:hover {{
                opacity: 0.9;
            }}
            .auth-link {{
                color: var(--text-secondary);
                text-decoration: none;
                font-size: 0.9rem;
                transition: color 0.2s;
                display: inline-block;
            }}
            .auth-link:hover {{
                color: var(--accent-color);
            }}
            .error-message {{
                background-color: rgba(255, 68, 68, 0.1);
                color: #ffffff;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 20px;
                font-size: 0.9rem;
                border: 1px solid rgba(255, 68, 68, 0.3);
                text-align: left; /* Keep explicit text align */
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .error-icon {{
                flex-shrink: 0;
                color: #ff4444;
            }}
        </style>
    </head>
    <body>
        <div class="auth-card">
            <h2 class="auth-title">Nebulus</h2>
            {error_html}
            <form action="/login" method="post" class="auth-form">
                <div class="input-group">
                    <label>Email / Username</label>
                    <input type="text" name="username" class="auth-input" required autofocus>
                </div>
                <div class="input-group">
                    <label>Password</label>
                    <input type="password" name="password" class="auth-input" required>
                </div>
                <button type="submit" class="btn-auth">Sign In</button>
                <div style="margin-top: 20px;">
                    <a href="/register" class="auth-link">Need an account? Register here</a>
                </div>
            </form>
        </div>
        <script>
            document.querySelectorAll('.auth-input').forEach(input => {{
                input.addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter') {{
                        e.preventDefault();
                        document.querySelector('form').submit();
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Serve the login form."""
    return get_login_html()


@router.post("/login")
def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    """Handle login submission and set cookie."""

    db = SessionLocal()
    try:
        user = get_user(db, username)

        if not user or not verify_password(password, user.hashed_password):
            # Return the login page with an error message
            return HTMLResponse(get_login_html("Invalid credentials"), status_code=401)

        access_token = create_access_token(data={
            "identifier": user.username,
            "display_name": user.username,
            "metadata": {"username": user.username, "role": user.role or "user"}
        })
        
        # Populate Chainlit session
        user_data = {"identifier": user.username, "metadata": {"username": user.username}}
        request.session["user"] = user_data
        # Some versions of Chainlit or Starlette sessions might use different keys
        request.session["_cl_user"] = user_data 
        
        
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="access_token", value=access_token, httponly=True
        )
        response.set_cookie(
            key="token", value=access_token, httponly=True
        )
        return response
    finally:
        db.close()


@router.get("/logout")
def logout(response: Response):
    """Clear session cookie and redirect to login."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


def get_register_html(error: str = None):
    error_html = ""
    if error:
        error_html = f"""
            <div class="error-message">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="error-icon"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                <span>{error}</span>
            </div>
        """
    return f"""
    <!DOCTYPE html>
    <html class="dark">
    <head>
        <title>Nebulus - Register</title>
        <link rel="stylesheet" href="/public/style.css">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
        <style>
             body {{
                display: flex;
                align-items: center;
                justify-content: center;
                background: var(--bg-primary);
                height: 100vh;
            }}
            .auth-card {{
                background: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 40px;
                width: 400px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                text-align: center;
            }}
            .auth-title {{
                font-size: 2rem;
                font-weight: 600;
                color: var(--text-primary);
                margin-bottom: 10px;
            }}
            .auth-subtitle {{
                color: var(--text-secondary);
                font-size: 0.9rem;
                margin-bottom: 30px;
            }}
            .auth-form {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}
            .input-group {{
                text-align: left;
            }}
            .input-group label {{
                display: block;
                color: var(--text-secondary);
                font-size: 0.9rem;
                margin-bottom: 8px;
            }}
            .auth-input {{
                width: 100%;
                padding: 12px;
                background: var(--bg-primary);
                border: 1px solid var(--border-color);
                border-radius: 6px;
                color: var(--text-primary);
                font-size: 1rem;
                outline: none;
                transition: border-color 0.2s;
                box-sizing: border-box;
            }}
            .auth-input:focus {{
                border-color: var(--accent-color);
            }}
            .btn-auth {{
                background: var(--accent-color);
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-size: 1rem;
                font-weight: 500;
                cursor: pointer;
                transition: opacity 0.2s;
                margin-top: 10px;
            }}
            .btn-auth:hover {{
                opacity: 0.9;
            }}
            .error-message {{
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.2);
                color: #ef4444;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 0.9rem;
                text-align: left;
            }}
        </style>
    </head>
    <body class="bg-primary text-primary">
        <div class="auth-card">
            <h2 class="auth-title">Welcome</h2>
            <p class="auth-subtitle">Create your account to get started.</p>
            {error_html}
            <form action="/register" method="post" class="auth-form">
                <div class="input-group">
                    <label>Full Name</label>
                    <input type="text" name="full_name" class="auth-input" required>
                </div>
                <div class="input-group">
                    <label>Email</label>
                    <input type="email" name="email" class="auth-input" required>
                </div>
                <div class="input-group">
                    <label>Password</label>
                    <input type="password" name="password" class="auth-input" required>
                </div>
                <div class="input-group">
                    <label>Confirm Password</label>
                    <input type="password" name="confirm_password" class="auth-input" required>
                </div>
                <button type="submit" class="btn-auth">Create Account</button>
            </form>
        </div>
        <script>
            document.querySelectorAll('.auth-input').forEach(input => {{
                input.addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter') {{
                        e.preventDefault();
                        document.querySelector('form').submit();
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Serve the registration form."""
    return get_register_html()


@router.post("/register")
def register_user(
    response: Response,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Handle registration form submission."""

    if password != confirm_password:
        return HTMLResponse(get_register_html("Passwords do not match"), status_code=400)

    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = get_user(db, email)
        if existing_user:
            return HTMLResponse(get_register_html("Email is not available"), status_code=400)

        if get_user_count(db) == 0:
            role = "admin"
        else:
            role = "user"

        user = create_user(db, full_name, email, password, role=role)



        # Redirect to login page
        return RedirectResponse(url="/login", status_code=303)
    except Exception as e:
        return HTMLResponse(get_register_html(f"Error: {str(e)}"), status_code=500)
    finally:
        db.close()
