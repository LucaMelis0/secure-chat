# **Secure Group Chat Webserver**
A secure webserver application that provides real-time group chat and private messaging.<br>
This project is built with Python, FastAPI, HTML, and CSS in order to achieve a group chat experience with secure authentication and SSL encryption.

## **Table of Contents**

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Firewall Configuration (Optional)](#firewall-configuration-optional)
- [Project Structure](#project-structure)
- [Dependencies](#dependencies)

### **Features**
- **Secure Communication**: SSL encryption using self-generated certificates.
- **Group Chat & Private Messaging**: Real-time messaging for groups and direct user-to-user private messages.
- **User Authentication**: Registration and login using secure password hashing (bcrypt).
- **Session Management**: FastAPI session handling for secure user sessions.
- **Database Integration**: SQLite database for managing user credentials.

### Architecture Overview
This project consists of the following key components:

1. **Certificate Generation** (`generate_certificates.py`)
Generates SSL certificates and private keys using the `cryptography` library. The generated certificates secure the communication between clients and the server.

2. **Database Management** (`database.py`)
Handles the SQLite database operations including initialization, user creation, password verification, and user deletion. It uses `bcrypt` for secure password hashing.

3. **FastAPI Server** (`main.py`)
Implements the core functionality of the chat application using FastAPI.
It supports:
  - User authentication (login and registration).
  - Session management with secure cookies.
  - Real-time communication via WebSockets for both group and private messaging.
  - Broadcasting of system messages and online user updates.

### Prerequisites
Before running the project, make sure you have the following installed:

  - **Python 3.8+**
  - **pip** (Python package installer)
  - **Virtual Environment Software** (Optional)

### Installation
1. Clone the Repository:
  ```
  git clone https://github.com/LucaMelis0/secure-chat.git
  cd secure-chat
  ```
2. (Optional) **Create a Virtual Environment:**
   <br>On Linux/macOS:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
   On Windows:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
4. **Generate SSL Certificates:**
   <br>This will create the `cert.pem` certificate and the `key.pem` key file.
   ```
   python generate_certificates.py
   ```
   If this is correctly working, you will see some details printed in the terminal, like the validity of the certificate and the creation timestamp.
5. **Initialize the Database:**
   <br>This will run the database initialization script to set up the SQLite database and create required tables:
   ```
   python database.py
   ```

### Usage
After completing the installation steps, start the FastAPI server:
  ```
  python main.py
  ```
  The server will run on https://localhost:5000 with SSL enabled. Open the URL in your browser to access the chat application.

### Firewall Configuration (Optional)
If you plan to allow external devices (like your smartphone) to connect to your server, Windows Firewall might block incoming connections by default.
To allow connections on port 5000, follow these steps:
  1. Press **Win + R**, type `wf.msc`, and press Enter.
  2. Click on **Inbound Rules** in the left pane, and then on New Rule.
  3. Configure the Rule:
     - **Rule Type**: Port
     - **Protocol**: TCP
     - **Port**: 5000
     - **Action**: Allow the connection
     - **Profile**: Choose the appropriate profiles (Domain, Private, Public) based on your network setup. For a home network, typically select Private.
     - **Name**: The name you want to give to the rule

Once this is done, in order to connect to the server using another device, you need to follow those steps:
  1. Make sure your device is connected to the same local network of the server.
  2. Press **Win + R**, type `cmd` and press Enter.
  3. Type `ipconfig` in the terminal and press Enter.
  4. Look for the **IPv4 Address** under your active network adapter. This is your local IP address.<br>
  
The address you just found is the address you need to connect to with your device.
For example, if the ip address is 192.168.1.5, you will need to type `https://192.168.1.5:5000` in your browser to connect to the server.

### Project Structure
  ```
  .
  ├── generate_certificates.py   # Generates SSL certificates for secure communications.
  ├── database.py                # Manages user authentication and database operations.
  ├── main.py                    # FastAPI server handling authentication, sessions, and WebSocket messaging.
  ├── requirements.txt           # List of project dependencies.
  ├── static/                    # Contains CSS, JavaScript, and other static assets.
  ├── templates/                 # Contains HTML templates (e.g., index.html, auth.html, chat.html).
  └── README.md                  # Project documentation.

  ```

### Dependencies
Key dependencies include:
  - **cryptography**: For generating and handling SSL certificates.
  - **bcrypt**: For secure password hashing.
  - **FastAPI**: For creating the webserver and handling WebSockets endpoints.
  - **uvicorn**: Server used to run FastAPI.
  - **sqlite3**: Python's built-in module for managing SQLite database.
  - **Jinja2**: Templating engine for rendering HTML pages.<br>
  
  For the complete list, refer to the [requirements.txt](requirements.txt) file.
