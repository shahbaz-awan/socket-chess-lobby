# ♟️ Multiplayer Chess Game using Socket Programming

A real-time multiplayer chess game built with Python using socket programming. The system follows a client-server architecture where the server manages matchmaking, game sessions, and communication between clients. It also supports GUI-based interaction, chat messaging, spectator mode, and full chess logic with rule enforcement.

---

## 🧩 Features

- 🔗 **Client-Server Architecture**
- 🎮 **Lobby & Matchmaking System**
- 👥 **Real-time Multiplayer Gameplay**
- ⌛ **Turn-based Play with Time Enforcement**
- 💬 **In-Game Chat System**
- 👀 **Spectator Mode**
- ✅ **Legal Move Validation (Check, Checkmate, Stalemate)**

---

## 🖥️ System Design

### 🎯 Client Responsibilities
- Connect to the server via socket.
- Join a game lobby and wait for matchmaking.
- Send chess moves to the server.
- Receive opponent's moves and update the board.
- Display the chessboard with real-time updates.
- Chat with opponent and spectators.

### 🧠 Server Responsibilities
- Listen for incoming connections from clients.
- Handle matchmaking and assign player colors.
- Validate all chess moves.
- Manage game states and synchronize updates.
- Support real-time chat system and spectator updates.
- Enforce turn-taking and countdown timers.

---

## 🔄 Data Flow

```text
Client connects → Joins lobby → Server matches players → Game starts
↓
Client makes move → Server validates → Broadcasts updated state
↓
Turns alternate → Game ends (checkmate/draw) → Players notified
```

---

## 🛠️ Installation

### 📦 Prerequisites
- Python 3.10+
- Required Library: `chess`

```bash
pip install chess
```

### 📂 Clone the Repository

```bash
git clone https://github.com/shahbaz-awan/socket-chess-lobby.git
cd socket-chess-lobby
```

### ▶️ Run the Server

```bash
python server.py
```

### 🎮 Run the Client

```bash
python client.py
```

---

## 🗂️ Project Structure

```
├── server.py             # Handles socket connections, matchmaking, game logic
├── client.py             # User interface and communication with server
├── game_logic.py         # Chess logic and move validation
├── communication.py      # Message formatting and socket communication
├── config.py             # Configurable constants and settings
└── __pycache__/          # Cached bytecode files
```

---

## 🚀 Future Enhancements

- GUI using Tkinter or PyQt
- Save/load game functionality
- Enhanced time control settings (e.g., blitz, bullet)
- WebSocket-based browser support

---

## 👨‍💻 Author

**M. Faizan**  
Software Engineer | Python Developer

---
