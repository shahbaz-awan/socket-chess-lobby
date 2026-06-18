import socket
import threading
import time
import select
import uuid
import chess
from communication import *
from game_logic import ChessGame
from config import *

class ChessServer:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(MAX_PLAYERS_IN_LOBBY)
        
        self.clients = {}  # {client_id: (conn, addr, player_name)}
        self.lobby = []    # List of client_ids waiting for a game
        self.games = {}    # {game_id: ChessGame}
        self.client_game = {}  # {client_id: game_id}
        
        print(f"Server started on {self.host}:{self.port}")
        
    def start(self):
        """Start the server"""
        try:
            while True:
                client_socket, address = self.server_socket.accept()
                client_id = str(uuid.uuid4())
                self.clients[client_id] = (client_socket, address, None)
                
                print(f"New connection from {address}, assigned ID: {client_id}")
                
                # Start a new thread to handle this client
                client_thread = threading.Thread(target=self.handle_client, args=(client_id,))
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            self.server_socket.close()
    
    def handle_client(self, client_id):
        """Handle communication with a client"""
        client_socket = self.clients[client_id][0]
        
        try:
            # Set socket to non-blocking mode
            client_socket.setblocking(False)
            
            buffer = b""
            
            while True:
                # Try to receive data
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break  # Client disconnected
                    
                    buffer += data
                    
                    # Process complete messages
                    while b'\n' in buffer:
                        message, buffer = buffer.split(b'\n', 1)
                        self.process_message(client_id, message)
                        
                except socket.error:
                    # No data available, continue
                    pass
                
                # Update game timers and send updates
                self.update_games(client_id)
                
                time.sleep(0.1)  # Prevent CPU hogging
                
        except Exception as e:
            print(f"Error handling client {client_id}: {e}")
        finally:
            self.disconnect_client(client_id)
    
    def process_message(self, client_id, message):
        """Process a message received from a client"""
        msg_type, data = parse_message(message)
        
        if msg_type == JOIN_LOBBY:
            player_name = data.get("player_name", f"Player_{client_id[:5]}")
            self.clients[client_id] = (self.clients[client_id][0], self.clients[client_id][1], player_name)
            self.lobby.append(client_id)
            print(f"{player_name} joined the lobby")
            
            # Try to match players
            self.match_players()
            
        elif msg_type == LIST_GAMES:
            # Send list of active games to the client
            active_games = []
            for game_id, game in self.games.items():
                if game.game_status == "active" or game.game_status == "waiting":
                    white_name = self.clients[game.white_player][2] if game.white_player in self.clients else "Unknown"
                    black_name = self.clients[game.black_player][2] if game.black_player in self.clients else "Waiting..."
                    
                    active_games.append({
                        "game_id": game_id,
                        "white_player": white_name,
                        "black_player": black_name,
                        "status": game.game_status,
                        "spectator_count": len(game.spectators)
                    })
            
            self.send_message(client_id, GAMES_LIST, {"games": active_games})
            
        elif msg_type == CREATE_GAME:
            # Create a new game and add the client as the first player
            game_id = str(uuid.uuid4())
            self.games[game_id] = ChessGame(game_id, white_player=client_id)
            self.client_game[client_id] = game_id
            
            # Confirm game creation
            self.send_message(client_id, PLAYER_ASSIGNED, {
                "color": "white",
                "game_id": game_id,
                "status": "waiting"
            })
            
            print(f"New game {game_id} created by {self.clients[client_id][2]}")
            
        elif msg_type == SPECTATE_GAME:
            game_id = data.get("game_id")
            if game_id in self.games:
                game = self.games[game_id]
                spectator_name = self.clients[client_id][2]
                
                # Add the spectator to the game
                if game.add_spectator(client_id):
                    self.client_game[client_id] = game_id
                    
                    # Send current game state to the spectator
                    self.send_message(client_id, GAME_STATE, game.get_game_state())
                    
                    # Notify all players and other spectators that a new spectator joined
                    self.broadcast_to_game(game_id, SPECTATOR_JOINED, {
                        "spectator_name": spectator_name,
                        "spectator_count": len(game.spectators)
                    })
                    
                    # Also send a system chat message to notify everyone
                    chat_entry = game.add_chat_message("System", f"{spectator_name} joined as a spectator")
                    self.broadcast_to_game(game_id, CHAT_MESSAGE, chat_entry)
                    
                    print(f"{spectator_name} is now spectating game {game_id}")
                else:
                    # Already spectating this game
                    self.send_message(client_id, ERROR, {"message": "You are already spectating this game"})
            else:
                # Game not found
                self.send_message(client_id, ERROR, {"message": "Game not found. Please check the game ID."})
            
        elif msg_type == MAKE_MOVE:
            game_id = self.client_game.get(client_id)
            if game_id and game_id in self.games:
                game = self.games[game_id]
                move = data.get("move")
                
                success, message = game.make_move(move, client_id)
                
                # Send updated game state to all players and spectators
                game_state = game.get_game_state()
                
                if success:
                    self.broadcast_to_game(game_id, GAME_STATE, game_state)
                    
                    if game.game_status == "completed":
                        self.broadcast_to_game(game_id, GAME_OVER, {
                            "reason": message,
                            "game_state": game_state
                        })
                else:
                    # Send error only to the player who tried to make the invalid move
                    self.send_message(client_id, ERROR, {"message": message})
        
        elif msg_type == CHAT_MESSAGE:
            game_id = self.client_game.get(client_id)
            if game_id and game_id in self.games:
                game = self.games[game_id]
                message = data.get("message")
                sender_name = self.clients[client_id][2]
                
                chat_entry = game.add_chat_message(sender_name, message)
                
                # Broadcast chat message to everyone in the game
                self.broadcast_to_game(game_id, CHAT_MESSAGE, chat_entry)
    
    def match_players(self):
        """Match waiting players in the lobby"""
        while len(self.lobby) >= 2:
            white_player = self.lobby.pop(0)
            black_player = self.lobby.pop(0)
            
            # Create a new game
            game_id = str(uuid.uuid4())
            game = ChessGame(game_id, white_player=white_player, black_player=black_player)
            self.games[game_id] = game
            
            # Update client-game mappings
            self.client_game[white_player] = game_id
            self.client_game[black_player] = game_id
            
            # Notify players
            self.send_message(white_player, PLAYER_ASSIGNED, {
                "color": "white",
                "game_id": game_id,
                "status": "active"
            })
            
            self.send_message(black_player, PLAYER_ASSIGNED, {
                "color": "black",
                "game_id": game_id,
                "status": "active"
            })
            
            # Send initial game state
            game_state = game.get_game_state()
            self.broadcast_to_game(game_id, GAME_STATE, game_state)
            
            print(f"Matched players: {self.clients[white_player][2]} (White) vs {self.clients[black_player][2]} (Black) in game {game_id}")
    
    def update_games(self, client_id):
        """Update game timers and send updates to clients"""
        game_id = self.client_game.get(client_id)
        if not game_id or game_id not in self.games:
            return
            
        game = self.games[game_id]
        if game.game_status != "active":
            return
            
        # Update timers
        current_time = time.time()
        if game.last_move_time:
            elapsed = current_time - game.last_move_time
            if game.board.turn == chess.WHITE:
                if client_id == game.white_player:
                    game.white_time_remaining -= elapsed
                    game.last_move_time = current_time
                    
                    # Check for timeout
                    if game.white_time_remaining <= 0:
                        game.white_time_remaining = 0
                        game.game_status = "completed"
                        
                        # Notify players of game over
                        self.broadcast_to_game(game_id, GAME_OVER, {
                            "reason": "White ran out of time. Black wins!",
                            "game_state": game.get_game_state()
                        })
            else:
                if client_id == game.black_player:
                    game.black_time_remaining -= elapsed
                    game.last_move_time = current_time
                    
                    # Check for timeout
                    if game.black_time_remaining <= 0:
                        game.black_time_remaining = 0
                        game.game_status = "completed"
                        
                        # Notify players of game over
                        self.broadcast_to_game(game_id, GAME_OVER, {
                            "reason": "Black ran out of time. White wins!",
                            "game_state": game.get_game_state()
                        })
            
            # Send time updates every second
            if int(current_time) != int(current_time - elapsed):
                self.broadcast_to_game(game_id, TIME_UPDATE, {
                    "white_time": game.white_time_remaining,
                    "black_time": game.black_time_remaining
                })
    
    def broadcast_to_game(self, game_id, msg_type, data):
        """Send a message to all players and spectators in a game"""
        if game_id not in self.games:
            return
            
        game = self.games[game_id]
        recipients = [game.white_player, game.black_player] + game.spectators
        
        for client_id in recipients:
            if client_id and client_id in self.clients:
                self.send_message(client_id, msg_type, data)
    
    def send_message(self, client_id, msg_type, data):
        """Send a message to a specific client"""
        if client_id not in self.clients:
            return
            
        client_socket = self.clients[client_id][0]
        try:
            message = create_message(msg_type, data)
            client_socket.sendall(message + b'\n')
        except Exception as e:
            print(f"Error sending message to client {client_id}: {e}")
            self.disconnect_client(client_id)
    
    def disconnect_client(self, client_id):
        """Handle client disconnection"""
        if client_id not in self.clients:
            return
            
        print(f"Client {client_id} ({self.clients[client_id][2]}) disconnected")
        
        # Remove from lobby if present
        if client_id in self.lobby:
            self.lobby.remove(client_id)
        
        # Handle disconnection from a game
        game_id = self.client_game.get(client_id)
        if game_id and game_id in self.games:
            game = self.games[game_id]
            
            # If player is a spectator, just remove them
            if client_id in game.spectators:
                game.spectators.remove(client_id)
            else:
                # If player is white or black, end the game
                if game.game_status == "active":
                    game.game_status = "completed"
                    
                    # Determine winner
                    if client_id == game.white_player:
                        winner = "black"
                        reason = "White player disconnected. Black wins!"
                    else:
                        winner = "white"
                        reason = "Black player disconnected. White wins!"
                    
                    # Notify remaining players and spectators
                    self.broadcast_to_game(game_id, GAME_OVER, {
                        "reason": reason,
                        "game_state": game.get_game_state()
                    })
        
        # Close the socket and remove the client
        try:
            self.clients[client_id][0].close()
        except:
            pass
        
        del self.clients[client_id]
        if client_id in self.client_game:
            del self.client_game[client_id]

if __name__ == "__main__":
    server = ChessServer()
    server.start()
