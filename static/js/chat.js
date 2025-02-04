// Redirect to home if the page is refreshed
if (performance.navigation.type === 1) {
    window.location.href = '/';
}

// Initialize client ID using the current timestamp
const client_id = Date.now().toString();
let currentChatId = 'group'; // Default chat ID is 'group'
const chats = new Map(); // Map to store chat messages
const unreadMessages = new Map(); // Map to store unread messages count

/**
 * Get the current timestamp in UTC+1 (Europe/Rome) timezone.
 * @returns {string} The formatted timestamp string.
 */
function getUTCTimestamp() {
    const options = {
        timeZone: 'Europe/Rome',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };

    const now = new Date();
    const [date, time] = now.toLocaleString('it-IT', options).split(',');
    const [day, month, year] = date.split('/');
    return `${year}-${month}-${day}${time}`;
}

// Initialize WebSocket connection
const ws = new WebSocket(`wss://${window.location.host}/ws/${client_id}`);

/**
 * Initialize a chat with the given chat ID.
 * @param {string} chatId - The ID of the chat to initialize.
 */
function initChat(chatId) {
    if (!chats.has(chatId)) {
        chats.set(chatId, []);
    }
}

/**
 * Update the list of online users in the sidebar.
 * @param {Array} users - The list of online users.
 */
function updateOnlineUsers(users) {
    const usersList = document.getElementById('users-list');
    usersList.innerHTML = ''; // Clear the existing list

    users.forEach(user => {
        if (user.client_id !== client_id) {
            const userElement = document.createElement('div');
            userElement.className = 'user-item';
            userElement.innerHTML = `
                ${user.username}
                <button onclick="startPrivateChat('${user.client_id}', '${user.username}')">
                    Private Message
                </button>
            `;
            usersList.appendChild(userElement);
        }
    });
}

/**
 * Start a private chat with the specified user.
 * @param {string} receiverId - The client ID of the user to chat with.
 * @param {string} username - The username of the user to chat with.
 * @param {boolean} [autoOpen=true] - Whether to automatically open the chat.
 * @returns {string} The ID of the private chat.
 */
function startPrivateChat(receiverId, username, autoOpen = true) {
    const chatId = `${Math.min(client_id, receiverId)}_${Math.max(client_id, receiverId)}`;
    initChat(chatId);

    // Create a new chat item if it doesn't already exist
    if (!document.querySelector(`[data-chat-id="${chatId}"]`)) {
        const chatElement = document.createElement('div');
        chatElement.className = 'chat-item';
        chatElement.setAttribute('data-chat-id', chatId);
        chatElement.innerHTML = `
            <span class="chat-name">Chat with ${username}</span>
            <span class="notification-badge" style="display: none;"></span>
        `;
        chatElement.onclick = () => switchChat(chatId, `Chat with ${username}`);
        document.getElementById('private-chats').appendChild(chatElement);
    }

    if (autoOpen) {
        switchChat(chatId, `Chat with ${username}`);
    }
    return chatId;
}

/**
 * Switches the current chat to the specified chat ID and updates the UI.
 * @param {string} chatId - The ID of the chat to switch to.
 * @param {string} chatName - The name of the chat to display in the header.
 */
function switchChat(chatId, chatName) {
    currentChatId = chatId;

    // Remove 'active' class from all chat items
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
    });

    // Add 'active' class to the selected chat item
    const chatElement = document.querySelector(`[data-chat-id="${chatId}"]`);
    if (chatElement) {
        chatElement.classList.add('active');

        // Hide the notification badge
        const notificationBadge = chatElement.querySelector('.notification-badge');
        if (notificationBadge) {
            notificationBadge.style.display = 'none';
        }
        unreadMessages.set(chatId, 0);
    }

    // Update the chat header with the new chat name
    document.getElementById('current-chat-header').innerHTML = `<h2>${chatName}</h2>`;

    // Initialize the chat if it doesn't exist and display its messages
    if (!chats.has(chatId)) {
        initChat(chatId);
    }
    displayMessages(chats.get(chatId));

    // Focus on the message input field
    document.getElementById('messageText').focus();
}

/**
 * Shows a notification for the specified chat ID if it is not the current chat.
 * @param {string} chatId - The ID of the chat for which to show the notification.
 */
function showNotification(chatId) {
    if (chatId !== currentChatId) {
        const chatElement = document.querySelector(`[data-chat-id="${chatId}"]`);
        if (chatElement) {
            const badge = chatElement.querySelector('.notification-badge');
            if (badge) {
                badge.style.display = 'block';
            }
            unreadMessages.set(chatId, (unreadMessages.get(chatId) || 0) + 1);
        }
    }
}

/**
 * Displays the messages for the specified chat.
 * @param {Array} messages - The list of messages to display.
 */
function displayMessages(messages) {
    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML = ''; // Clear existing messages

    // Add each message to the messages container
    messages.forEach(data => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${data.type === 'system' ? 'system' : (data.is_self ? 'sent' : 'received')}`;
        messageDiv.innerHTML = `
            <div class="message-content">
                ${data.type === 'system' ? `<p>${data.message}</p>` : `<span class="sender">${data.is_self ? 'You' : data.sender_username}</span><p>${data.message}</p>`}
                <span class="timestamp">${data.timestamp}</span>
            </div>
        `;
        messagesDiv.appendChild(messageDiv);
    });

    // Scroll to the bottom of the messages container
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// WebSocket connection opened
ws.onopen = function() {
    initChat('group');
    const systemMessage = {
        type: 'system',
        message: `Welcome ${username} to the chat`,
        timestamp: getUTCTimestamp()
    };
    chats.get('group').push(systemMessage);
    displayMessages(chats.get('group'));
};

// WebSocket message received
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);

    if (data.type === "error") {
        if (data.message === "Session already active from another device") {
            showErrorDialog("Duplicate Session", "Your account is already active in another session. You will be logged out.");
            ws.close();
            setTimeout(() => {
                window.location.href = "/logout";
            }, 2000);
            return;
        }
    }

    if (data.type === 'online_users') {
        updateOnlineUsers(data.users);
    } else {
        const chatId = data.type === 'private_message' ? data.chat_id : 'group';
        initChat(chatId);
        const chatMessages = chats.get(chatId);
        data.timestamp = data.timestamp || getUTCTimestamp();
        chatMessages.push(data);

        if (data.type === 'private_message' && !data.is_self) {
            const senderId = chatId.split('_').find(id => id !== client_id);
            startPrivateChat(senderId, data.sender_username, false);
            showNotification(chatId);
        } else if (data.type === 'group_message' && chatId !== currentChatId) {
            showNotification('group');
        }

        if (currentChatId === chatId) {
            displayMessages(chatMessages);
        }
    }
};

/**
 * Handles the WebSocket onclose event.
 * @param {CloseEvent} event - The WebSocket close event.
 */
ws.onclose = function(event) {
    console.log("WebSocket closed:", event.code, event.reason);

    if (event.code === 1008) {
        if (event.reason === "Session already active") {
            showErrorDialog("Duplicate Session", "Your account is already active in another session. You will be logged out.");
        } else {
            showErrorDialog("Authentication Error", "An authentication error occurred. You will be redirected to the login page.");
        }
    } else if (!event.wasClean) {
        showErrorDialog("Connection Lost", "The connection was interrupted. You will be redirected to the login page.");
    }

    // Redirect to logout after showing the error dialog
    setTimeout(() => {
        window.location.href = "/logout";
    }, 2000);
};

/**
 * Displays an error dialog with the specified title and message.
 * @param {string} title - The title of the error dialog.
 * @param {string} message - The message of the error dialog.
 */
function showErrorDialog(title, message) {
    // Remove any existing error dialog
    const existingDialog = document.querySelector('.error-dialog-overlay');
    if (existingDialog) {
        existingDialog.remove();
    }

    // Create the error dialog overlay
    const dialogOverlay = document.createElement('div');
    dialogOverlay.className = 'error-dialog-overlay';

    // Create the error dialog box
    const dialogBox = document.createElement('div');
    dialogBox.className = 'error-dialog';
    dialogBox.innerHTML = `
        <h3>${title}</h3>
        <p>${message}</p>
        <div class="progress-bar"></div>
    `;
    dialogOverlay.appendChild(dialogBox);
    document.body.appendChild(dialogOverlay);

    // Animate the progress bar
    requestAnimationFrame(() => {
        const progressBar = dialogBox.querySelector('.progress-bar');
        progressBar.style.width = '0';
    });
}

/**
 * Sends a message through the WebSocket connection.
 */
function sendMessage() {
    const input = document.getElementById('messageText');
    const message = input.value.trim();

    if (message) {
        const isPrivateChat = currentChatId !== 'group';

        // Send a private message
        if (isPrivateChat) {
            const [id1, id2] = currentChatId.split('_');
            const receiverId = id1 === client_id ? id2 : id1;
            ws.send(JSON.stringify({
                type: 'private_message',
                receiver_id: receiverId,
                message: message
            }));
        } else {
            // Send a group message
            ws.send(JSON.stringify({
                type: 'group_message',
                message: message
            }));

            // Add the message to the group chat
            const messageData = {
                type: 'group_message',
                sender: 'You',
                message: message,
                timestamp: getUTCTimestamp(),
                is_self: true
            };
            chats.get('group').push(messageData);
            displayMessages(chats.get('group'));
        }

        // Clear the input field and focus it
        input.value = '';
        input.focus();
    }
}

// Add an event listener for the Enter key to send a message
document.getElementById('messageText').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Ensure the WebSocket connection is closed before the window unloads
window.onbeforeunload = function() {
    ws.close();
};