import json

# Message types
JOIN_LOBBY = "join_lobby"
CREATE_GAME = "create_game"
MAKE_MOVE = "make_move"
GAME_STATE = "game_state"
CHAT_MESSAGE = "chat_message"
PLAYER_ASSIGNED = "player_assigned"
GAME_OVER = "game_over"
SPECTATE_GAME = "spectate_game"
TIME_UPDATE = "time_update"
ERROR = "error"
LIST_GAMES = "list_games"
GAMES_LIST = "games_list"
SPECTATOR_JOINED = "spectator_joined"

def create_message(msg_type, data):
    """Create a message packet that can be sent over the socket"""
    message = {
        "type": msg_type,
        "data": data
    }
    return json.dumps(message).encode()

def parse_message(message):
    """Parse a message received from the socket"""
    try:
        decoded = message.decode()
        data = json.loads(decoded)
        return data["type"], data["data"]
    except Exception as e:
        print(f"Error parsing message: {e}")
        return ERROR, {"error": "Invalid message format"}
