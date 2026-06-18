import chess
import time

class ChessGame:
    def __init__(self, game_id, white_player=None, black_player=None, time_limit_mins=15):
        self.game_id = game_id
        self.board = chess.Board()
        self.white_player = white_player
        self.black_player = black_player
        self.spectators = []
        self.chat_history = []
        self.game_status = "waiting"  # waiting, active, completed
        
        # Time control (in seconds)
        self.time_limit = time_limit_mins * 60
        self.white_time_remaining = self.time_limit
        self.black_time_remaining = self.time_limit
        self.last_move_time = None
        
    def add_player(self, player_id):
        """Add a player to the game if a slot is available"""
        if self.white_player is None:
            self.white_player = player_id
            return "white"
        elif self.black_player is None:
            self.black_player = player_id
            self.game_status = "active"
            self.last_move_time = time.time()
            return "black"
        return None
        
    def add_spectator(self, spectator_id):
        """Add a spectator to the game"""
        if spectator_id not in self.spectators:
            self.spectators.append(spectator_id)
            return True
        return False
        
    def make_move(self, move_uci, player_id):
        """Attempt to make a move on the board"""
        # Check if it's the player's turn
        is_white_turn = self.board.turn == chess.WHITE
        if (is_white_turn and player_id != self.white_player) or \
           (not is_white_turn and player_id != self.black_player):
            return False, "Not your turn"
        
        # Update timer
        current_time = time.time()
        if self.last_move_time:
            elapsed = current_time - self.last_move_time
            if is_white_turn:
                self.white_time_remaining -= elapsed
                if self.white_time_remaining <= 0:
                    self.game_status = "completed"
                    return False, "White ran out of time"
            else:
                self.black_time_remaining -= elapsed
                if self.black_time_remaining <= 0:
                    self.game_status = "completed"
                    return False, "Black ran out of time"
        
        # Try to make the move
        try:
            move = chess.Move.from_uci(move_uci)
            if move in self.board.legal_moves:
                self.board.push(move)
                self.last_move_time = current_time
                
                # Check for game end conditions
                if self.board.is_checkmate():
                    self.game_status = "completed"
                    winner = "black" if is_white_turn else "white"
                    return True, f"Checkmate. {winner.capitalize()} wins!"
                
                if self.board.is_stalemate() or self.board.is_insufficient_material():
                    self.game_status = "completed"
                    return True, "Game drawn."
                
                return True, None
            else:
                return False, "Illegal move"
        except Exception as e:
            return False, str(e)
    
    def add_chat_message(self, sender_id, message):
        """Add a chat message to the game"""
        chat_entry = {
            "sender": sender_id,
            "message": message,
            "timestamp": time.time()
        }
        self.chat_history.append(chat_entry)
        return chat_entry
    
    def get_game_state(self):
        """Return the current state of the game"""
        return {
            "game_id": self.game_id,
            "board_fen": self.board.fen(),
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "white_player": self.white_player,
            "black_player": self.black_player,
            "white_time": self.white_time_remaining,
            "black_time": self.black_time_remaining,
            "status": self.game_status,
            "check": self.board.is_check(),
            "last_move": self.board.move_stack[-1].uci() if len(self.board.move_stack) > 0 else None
        }
