import sqlite3
import bcrypt
from contextlib import contextmanager
import logging
from typing import Optional, Tuple
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_NAME = 'chat_users.db'

@contextmanager
def get_db():
    """Context manager for database connection."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize the database by creating the users table if it doesn't exist."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Create the users table with uniqueness and not null constraints
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            conn.commit()
            logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Error initializing the database: {e}")
        raise

def hash_password(password: str) -> str:
    """
    Generate a secure hash of the password using bcrypt.

    Args:
        password: The plaintext password to hash

    Returns:
        str: The hashed password encoded in utf-8
    """
    try:
        # Generate a random salt and hash the password
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing the password: {e}")
        raise

def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify if a password matches its hash.

    Args:
        password: The plaintext password to verify
        stored_hash: The hash stored in the database

    Returns:
        bool: True if the password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception as e:
        logger.error(f"Error verifying the password: {e}")
        return False

def create_user(username: str, password: str) -> bool:
    """
    Create a new user in the database.

    Args:
        username: The chosen username
        password: The plaintext password to be hashed

    Returns:
        bool: True if creation is successful, False if the username already exists
    """
    try:
        # Check minimum requirements
        if not username or len(username) < 3:
            logger.warning("Username too short or invalid")
            return False

        if not password or len(password) < 6:
            logger.warning("Password too short or invalid")
            return False

        # Generate password hash
        password_hash = hash_password(password)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)',
                (username, password_hash, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            logger.info(f"User {username} created successfully")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Username {username} already exists")
        return False
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False

def verify_user(username: str, password: str) -> bool:
    """
    Verify user credentials and update the last login timestamp.

    Args:
        username: The username to verify
        password: The plaintext password to verify

    Returns:
        bool: True if credentials are valid, False otherwise
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT password_hash FROM users WHERE username = ?',
                (username,)
            )
            result = cursor.fetchone()

            if result is None:
                logger.warning(f"Login attempt failed: user {username} not found")
                return False

            stored_hash = result[0]
            is_valid = verify_password(password, stored_hash)

            if is_valid:
                # Update the last login timestamp
                cursor.execute(
                    'UPDATE users SET last_login = ? WHERE username = ?',
                    (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), username)
                )
                conn.commit()
                logger.info(f"Login successful for user {username}")
            else:
                logger.warning(f"Login attempt failed for user {username}: invalid password")

            return is_valid
    except Exception as e:
        logger.error(f"Error verifying user: {e}")
        return False

def get_user_info(username: str) -> Optional[Tuple[int, str, str, str]]:
    """
    Retrieve user information from the database.

    Args:
        username: The username to search for

    Returns:
        Optional[Tuple[int, str, str, str]]: Tuple with (id, username, created_at, last_login) or None if not found
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, username, created_at, last_login FROM users WHERE username = ?',
                (username,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error retrieving user information: {e}")
        return None

def delete_user(username: str, password: str) -> bool:
    """
    Delete a user from the database if the credentials are correct.

    Args:
        username: The username to delete
        password: The user's password for confirmation

    Returns:
        bool: True if deletion is successful, False otherwise
    """
    try:
        if verify_user(username, password):
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users WHERE username = ?', (username,))
                conn.commit()
                logger.info(f"User {username} deleted successfully")
                return True
        return False
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False

# Initialize the database if it doesn't exist
if __name__ == '__main__':
    if not os.path.exists(DATABASE_NAME):
        init_db()