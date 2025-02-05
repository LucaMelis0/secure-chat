import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from database import create_user, verify_user


def generate_secret_key(timestamp: str, app_id: str = "chat_app_v1") -> str:
    """
    Generate a secret key based on the timestamp and app_id.
    The key remains consistent for the application but is unique for each installation.
    """
    base = f"{timestamp}_{app_id}_{secrets.token_hex(16)}"
    hash_obj = hashlib.sha256(base.encode())
    return hash_obj.hexdigest()


# Constants
SECRET_KEY = generate_secret_key(timestamp=datetime.now().strftime("%Y%m%d-%H%M%S"))
TEMPLATES_DIR = "templates"
STATIC_DIR = "static"
UTC_OFFSET = 1  # hours

# App initialization
app = FastAPI(title="Chat Application")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Type definitions
ClientId = str
Username = str
ChatId = str


class ChatState:
    """Global state management for the chat application"""

    def __init__(self):
        self.active_users: Dict[Username, ClientId] = {}
        self.active_connections: Dict[ClientId, Dict] = {}
        self.private_chats: Dict[ChatId, Set[ClientId]] = {}

    def add_user(self, username: Username, client_id: ClientId) -> None:
        """Add a user to the active users list"""
        self.active_users[username] = client_id

    def remove_user(self, username: Username) -> None:
        """Remove a user from the active users list"""
        self.active_users.pop(username, None)

    def is_user_active(self, username: Username) -> bool:
        """Check if a user is currently active"""
        return username in self.active_users


chat_state = ChatState()


class ConnectionManager:
    """Manage WebSocket connections and messages"""

    def __init__(self):
        self.state = chat_state

    @staticmethod
    def get_timestamp() -> str:
        """Returns current UTC timestamp with offset"""
        current_time = datetime.utcnow() + timedelta(hours=UTC_OFFSET)
        return current_time.strftime('%Y-%m-%d %H:%M:%S')

    def create_message(self, type_: str, **kwargs) -> str:
        """Creates a standardized message format"""
        message = {'type': type_, 'timestamp': self.get_timestamp(), **kwargs}
        return json.dumps(message)

    async def connect(self, websocket: WebSocket, client_id: ClientId, username: Username) -> bool:
        """Handle new WebSocket connection"""
        if self.state.is_user_active(username) and self.state.active_users[username] != client_id:
            await websocket.close()
            return False

        await websocket.accept()
        self.state.active_connections[client_id] = {'ws': websocket, 'username': username}
        self.state.add_user(username, client_id)

        await self.broadcast_system_message(f"{username} has joined the chat")
        await self.broadcast_online_users()
        return True

    def disconnect(self, client_id: ClientId) -> Username | None:
        """Handle WebSocket disconnection"""
        if client_id not in self.state.active_connections:
            return None

        connection = self.state.active_connections[client_id]
        username = connection['username']

        self.state.remove_user(username)
        del self.state.active_connections[client_id]

        # Clean up private chats
        for chat_id in list(self.state.private_chats.keys()):
            if client_id in self.state.private_chats[chat_id]:
                del self.state.private_chats[chat_id]

        return username

    async def broadcast_system_message(self, message: str) -> None:
        """Broadcast a system message to all connected clients"""
        system_message = self.create_message('system', message=message)
        await self.broadcast_message(system_message)

    async def broadcast_message(self, message: str) -> None:
        """Broadcast a message to all connected clients"""
        for connection in self.state.active_connections.values():
            await connection['ws'].send_text(message)

    async def broadcast_online_users(self) -> None:
        """Broadcast the list of online users to all connected clients"""
        online_users = [
            {'client_id': cid, 'username': data['username']}
            for cid, data in self.state.active_connections.items()
        ]
        users_message = self.create_message('online_users', users=online_users)
        await self.broadcast_message(users_message)

    async def send_private_message(self, sender_id: ClientId, receiver_id: ClientId, message: str) -> None:
        """Send a private message from one client to another"""
        if sender_id not in self.state.active_connections or receiver_id not in self.state.active_connections:
            return

        # Create a chat ID based on the sender and receiver IDs to group messages
        chat_id = f"{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
        if chat_id not in self.state.private_chats:
            self.state.private_chats[chat_id] = {sender_id, receiver_id}

        sender = self.state.active_connections[sender_id]
        receiver = self.state.active_connections[receiver_id]

        # Create message data
        message_data = self.create_message(
            'private_message',
            chat_id=chat_id,
            sender_username=sender['username'],
            message=message
        )

        # Send to receiver
        await receiver['ws'].send_text(message_data)

        # Send copy to sender with is_self flag
        sender_message = json.loads(message_data)
        sender_message['is_self'] = True
        await sender['ws'].send_text(json.dumps(sender_message))

    async def broadcast_group_message(self, sender_id: ClientId, message: str) -> None:
        """Broadcast a group message from one client to all other clients"""
        if sender_id not in self.state.active_connections:
            return

        sender = self.state.active_connections[sender_id]

        # Create message data
        group_message = self.create_message(
            'group_message',
            chat_id='group',
            sender_username=sender['username'],
            message=message
        )

        # Broadcast to all clients except the sender
        for client_id, connection in self.state.active_connections.items():
            if client_id != sender_id:
                await connection['ws'].send_text(group_message)


manager = ConnectionManager()


# Authentication middleware
async def verify_session(request: Request) -> bool:
    """Verify if the session is authenticated"""
    return request.session.get("authenticated", False)


# Route handlers
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the index page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/auth", response_class=HTMLResponse)
async def auth(request: Request):
    """Render the authentication page"""
    username = request.session.get("username")

    # Redirect to chat if already authenticated
    if username and chat_state.is_user_active(username):
        return templates.TemplateResponse(
            "auth.html",
            {"request": request, "error": "User already connected from another device"}
        )
    if await verify_session(request):
        return RedirectResponse(url="/chat")

    # Otherwise, render the auth page
    return templates.TemplateResponse("auth.html", {"request": request})


@app.post("/login")
async def login(request: Request):
    """Handle user login"""
    form = await request.form()
    username = form.get("username")
    password = form.get("password")

    # Verify user credentials: if not valid, return error
    if not verify_user(username, password):
        return templates.TemplateResponse(
            "auth.html",
            {"request": request, "error": "Invalid credentials"}
        )

    # Check if user is already connected: in that case, prevent login
    if chat_state.is_user_active(username):
        return templates.TemplateResponse(
            "auth.html",
            {"request": request, "error": "User already connected from another device"}
        )

    # If the user is correctly authenticated, set session data and redirect to chat
    request.session["authenticated"] = True
    request.session["username"] = username
    return RedirectResponse(url="/chat", status_code=303)


@app.post("/register")
async def register(request: Request):
    """Handle user registration"""
    form = await request.form()
    success = create_user(form.get("username"), form.get("password"))
    message = "Registration successful" if success else "Username already exists"
    return templates.TemplateResponse("auth.html", {"request": request, "error": message})


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    """Render the chat page if authenticated"""
    if not await verify_session(request):
        return RedirectResponse(url="/auth")

    # Render the chat page with session data
    username = request.session.get("username")
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "username": username,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )


@app.get("/logout")
async def logout(request: Request):
    """Handle user logout"""
    username = request.session.get("username")
    if username and chat_state.is_user_active(username):
        chat_state.remove_user(username)
    request.session.clear()
    return RedirectResponse(url="/")


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    Handle WebSocket connections for chat functionality. The following actions are supported:
    - Connect: Add user to active users and broadcast system message
    - Disconnect: Remove user from active users and broadcast system message
    - Private message: Send a private message to another user
    - Group message: Broadcast a message to all connected users
    """
    try:
        # Check if the user is authenticated
        username = websocket.session.get("username")
        if not username:
            await websocket.close(code=1008, reason="Not authenticated")
            return

        if chat_state.is_user_active(username) and chat_state.active_users[username] != client_id:
            await websocket.close(code=1008, reason="Session already active")
            return

        if not await manager.connect(websocket, client_id, username):
            return

        try:
            # Handle incoming messages
            while True:
                data = await websocket.receive_json()
                if data['type'] == 'private_message':
                    await manager.send_private_message(client_id, data['receiver_id'], data['message'])
                elif data['type'] == 'group_message':
                    await manager.broadcast_group_message(client_id, data['message'])
        except WebSocketDisconnect:
            # Handle disconnection
            username = manager.disconnect(client_id)
            if username:
                await manager.broadcast_system_message(f"{username} has left the chat")
                await manager.broadcast_online_users()

    except Exception as e:
        print(f"WebSocket connection error: {str(e)}")
        await websocket.close(code=1011)


if __name__ == "__main__":
    # Run the application with Uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )