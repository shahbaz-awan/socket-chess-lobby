import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import chess
import time
import io
import os
from communication import *
from config import *

class ChessClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Multiplayer Chess Game")
        self.master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.master.resizable(False, False)
        
        # Socket and connection
        self.client_socket = None
        self.connected = False
        self.player_name = None
        self.player_color = None
        self.game_id = None
        self.buffer = b""
        
        # Game state variables
        self.board = chess.Board()
        self.status = "disconnected"  # disconnected, in_lobby, waiting, playing, spectating
        self.selected_square = None
        self.valid_moves = []
        self.white_time = DEFAULT_TIME_LIMIT * 60
        self.black_time = DEFAULT_TIME_LIMIT * 60
        
        # Piece images cache
        self.piece_images = {}
        self.load_piece_images()
        
        # Setup UI
        self.create_widgets()
        
        # Start in connection screen
        self.show_connection_screen()
    
    def load_piece_images(self):
        """Load chess piece images from the chess_pieces_bw folder"""
        # Define piece types and colors
        pieces = {'p': 'pawn', 'n': 'knight', 'b': 'bishop', 'r': 'rook', 'q': 'queen', 'k': 'king'}
        colors = {'b': 'black', 'w': 'white'}  # b for black pieces, w for white pieces
        backgrounds = {'light': 'light', 'dark': 'dark'}
        
        # Path to the chess pieces folder
        pieces_dir = os.path.join(os.path.dirname(__file__), "chess_pieces_bw")
        
        # Check if the directory exists
        if not os.path.exists(pieces_dir):
            print(f"Warning: Chess pieces directory not found at {pieces_dir}")
            print("Please run download_pieces.py first to download the chess piece images.")
            self.create_fallback_images()
            return
        
        # Load images for all pieces and backgrounds
        for color_key in colors:
            for piece_key in pieces:
                for bg_name in backgrounds:
                    # Construct the filename
                    filename = f"{color_key}_{piece_key}_{bg_name}.png"
                    file_path = os.path.join(pieces_dir, filename)
                    
                    # Check if the file exists
                    if os.path.exists(file_path):
                        try:
                            # Load the image
                            img = Image.open(file_path)
                            
                            # Convert to PhotoImage for Tkinter
                            photo_img = ImageTk.PhotoImage(img)
                            
                            # Store in the dictionary
                            # Map to the format used in the original code
                            # Original: 'p_light' for black pawn on light square
                            # New: map 'b_p_light' to 'p_light'
                            piece_code = piece_key.lower() if color_key == 'b' else piece_key.upper()
                            self.piece_images[f"{piece_code}_{bg_name}"] = photo_img
                            
                        except Exception as e:
                            print(f"Error loading image {file_path}: {e}")
                            self.create_fallback_image(piece_key, bg_name)
                    else:
                        print(f"Image file not found: {file_path}")
                        self.create_fallback_image(piece_key, bg_name)
    
    def create_fallback_images(self):
        """Create fallback images if the chess piece images are not found"""
        piece_chars = {
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔'
        }
        
        size = SQUARE_SIZE - 10
        background_colors = {"light": (240, 217, 181), "dark": (181, 136, 99)}
        
        for piece_code, unicode_char in piece_chars.items():
            for bg in background_colors:
                self.create_fallback_image(piece_code, bg)
    
    def create_fallback_image(self, piece_code, bg):
        """Create a fallback image for a specific piece and background"""
        size = SQUARE_SIZE - 10
        background_colors = {"light": (240, 217, 181), "dark": (181, 136, 99)}
        
        # Create a new image with the background color
        img = Image.new('RGB', (size, size), background_colors[bg])
        
        # Draw the piece code (letter) in the center
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        
        # Use a simple approach - just draw the letter
        font = ImageFont.load_default()
        
        # Center the text (using approximate positioning)
        draw.text((size//2-5, size//2-5), piece_code, fill="red", font=font)
        
        # Store the image
        self.piece_images[f"{piece_code}_{bg}"] = ImageTk.PhotoImage(img)
    
    def create_widgets(self):
        """Create and setup all UI widgets"""
        # Main frame split into left (board) and right (controls)
        self.main_frame = tk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left frame for the board
        self.board_frame = tk.Frame(self.main_frame, width=BOARD_SIZE, height=BOARD_SIZE)
        self.board_frame.pack(side=tk.LEFT, padx=PADDING, pady=PADDING)
        
        # Canvas for the chess board
        self.board_canvas = tk.Canvas(self.board_frame, width=BOARD_SIZE, height=BOARD_SIZE, bg='white')
        self.board_canvas.pack()
        self.board_canvas.bind("<Button-1>", self.on_board_click)
        
        # Right frame for controls and chat
        self.control_frame = tk.Frame(self.main_frame, width=CHAT_WIDTH)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=PADDING, pady=PADDING)
        
        # Game info section
        self.info_frame = tk.Frame(self.control_frame)
        self.info_frame.pack(fill=tk.X, pady=(0, PADDING))
        
        self.status_label = tk.Label(self.info_frame, text="Status: Disconnected", font=("Arial", 12, "bold"))
        self.status_label.pack(anchor="w", pady=5)
        
        self.opponent_label = tk.Label(self.info_frame, text="Opponent: -", font=("Arial", 10))
        self.opponent_label.pack(anchor="w", pady=2)
        
        self.turn_label = tk.Label(self.info_frame, text="Turn: -", font=("Arial", 10))
        self.turn_label.pack(anchor="w", pady=2)
        
        # Timer display
        self.timer_frame = tk.Frame(self.control_frame)
        self.timer_frame.pack(fill=tk.X, pady=(0, PADDING))
        
        self.white_time_label = tk.Label(self.timer_frame, text="White: 15:00", font=("Arial", 12))
        self.white_time_label.pack(side=tk.LEFT, padx=5)
        
        self.black_time_label = tk.Label(self.timer_frame, text="Black: 15:00", font=("Arial", 12))
        self.black_time_label.pack(side=tk.RIGHT, padx=5)
        
        # Chat section
        self.chat_frame = tk.Frame(self.control_frame)
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chat_label = tk.Label(self.chat_frame, text="Chat", font=("Arial", 12, "bold"))
        self.chat_label.pack(anchor="w", pady=(0, 5))
        
        self.chat_text = tk.Text(self.chat_frame, width=30, height=15)
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        self.chat_text.config(state=tk.DISABLED)
        
        self.chat_input_frame = tk.Frame(self.chat_frame)
        self.chat_input_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.chat_entry = tk.Entry(self.chat_input_frame, width=25)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.chat_entry.bind("<Return>", self.send_chat_message)
        
        self.chat_send_button = tk.Button(self.chat_input_frame, text="Send", command=self.send_chat_message)
        self.chat_send_button.pack(side=tk.RIGHT)
        
        # Connection screen widgets (initially hidden)
        self.connection_frame = tk.Frame(self.master, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        
        self.conn_label = tk.Label(self.connection_frame, text="Chess Game Connection", font=("Arial", 16, "bold"))
        self.conn_label.pack(pady=(50, 20))
        
        self.server_frame = tk.Frame(self.connection_frame)
        self.server_frame.pack(pady=10)
        
        tk.Label(self.server_frame, text="Server:").pack(side=tk.LEFT)
        self.server_entry = tk.Entry(self.server_frame, width=15)
        self.server_entry.insert(0, SERVER_HOST)
        self.server_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.server_frame, text="Port:").pack(side=tk.LEFT)
        self.port_entry = tk.Entry(self.server_frame, width=5)
        self.port_entry.insert(0, str(SERVER_PORT))
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        self.name_frame = tk.Frame(self.connection_frame)
        self.name_frame.pack(pady=10)
        
        tk.Label(self.name_frame, text="Your Name:").pack(side=tk.LEFT)
        self.name_entry = tk.Entry(self.name_frame, width=20)
        self.name_entry.pack(side=tk.LEFT, padx=5)
        
        self.buttons_frame = tk.Frame(self.connection_frame)
        self.buttons_frame.pack(pady=20)
        
        self.connect_button = tk.Button(self.buttons_frame, text="Connect & Join Lobby", command=self.connect_to_server)
        self.connect_button.pack(side=tk.LEFT, padx=5)
        
        self.create_game_button = tk.Button(self.buttons_frame, text="Create New Game", command=self.create_new_game)
        self.create_game_button.pack(side=tk.LEFT, padx=5)
        
        self.spectate_button = tk.Button(self.buttons_frame, text="Spectate Game", command=self.spectate_game)
        self.spectate_button.pack(side=tk.LEFT, padx=5)
    
    def show_connection_screen(self):
        """Display the connection screen"""
        self.main_frame.pack_forget()
        self.connection_frame.pack(fill=tk.BOTH, expand=True)
    
    def show_game_screen(self):
        """Display the game screen"""
        self.connection_frame.pack_forget()
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
    def connect_to_server(self):
        """Connect to the chess server"""
        host = self.server_entry.get()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return
        
        self.player_name = self.name_entry.get()
        if not self.player_name:
            messagebox.showerror("Error", "Please enter your name")
            return
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.connected = True
            
            # Start receiving thread
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Join lobby
            self.send_message(JOIN_LOBBY, {"player_name": self.player_name})
            
            # Update UI
            self.status = "in_lobby"
            self.status_label.config(text="Status: In Lobby")
            self.show_game_screen()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
    
    def create_new_game(self):
        """Create a new game as white"""
        # First connect if not already connected
        if not self.connected:
            self.connect_to_server()
            if not self.connected:
                return
        
        # Request to create a game
        self.send_message(CREATE_GAME, {"player_name": self.player_name})
        
        # Status will be updated when server confirms
        self.status = "waiting"
        self.status_label.config(text="Status: Waiting for opponent")
        self.show_game_screen()
    
    def spectate_game(self):
        """Join a game as a spectator"""
        if not self.connected:
            self.connect_to_server()
            if not self.connected:
                return
        
        # First, request the list of active games from the server
        self.send_message(LIST_GAMES, {})
        # Result will be handled in process_message
    
    def receive_messages(self):
        """Receive and process messages from the server"""
        self.client_socket.setblocking(True)
        
        try:
            while self.connected:
                try:
                    data = self.client_socket.recv(4096)
                    if not data:
                        break  # Server closed the connection
                    
                    self.buffer += data
                    
                    # Process complete messages
                    while b'\n' in self.buffer:
                        message, self.buffer = self.buffer.split(b'\n', 1)
                        self.process_message(message)
                        
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    break
                    
        except:
            pass
        finally:
            self.connected = False
            self.status = "disconnected"
            self.master.after(0, self.update_status)
    
    def process_message(self, message):
        """Process a received message"""
        try:
            msg_type, data = parse_message(message)
            
            # Update UI from main thread
            if msg_type == PLAYER_ASSIGNED:
                self.master.after(0, lambda: self.handle_player_assigned(data))
            
            elif msg_type == GAME_STATE:
                self.master.after(0, lambda: self.handle_game_state(data))
            
            elif msg_type == CHAT_MESSAGE:
                self.master.after(0, lambda: self.handle_chat_message(data))
            
            elif msg_type == GAME_OVER:
                self.master.after(0, lambda: self.handle_game_over(data))
            
            elif msg_type == TIME_UPDATE:
                self.master.after(0, lambda: self.handle_time_update(data))
            
            elif msg_type == GAMES_LIST:
                self.master.after(0, lambda: self.show_games_list_dialog(data.get("games", [])))
            
            elif msg_type == SPECTATOR_JOINED:
                # Update spectator info if needed
                pass
            
            elif msg_type == ERROR:
                self.master.after(0, lambda: messagebox.showinfo("Error", data.get("message", "Unknown error")))
                
        except Exception as e:
            print(f"Error processing message: {e}")
            
    def show_games_list_dialog(self, games):
        """Show a dialog with available games to spectate"""
        if not games:
            messagebox.showinfo("No Games", "There are no active games to spectate at the moment.")
            return
            
        # Create a dialog to display games
        games_dialog = tk.Toplevel(self.master)
        games_dialog.title("Select a Game to Spectate")
        games_dialog.geometry("500x300")
        games_dialog.transient(self.master)
        games_dialog.grab_set()
        
        # Create a frame for the games list
        games_frame = tk.Frame(games_dialog)
        games_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a treeview to display the games
        columns = ("Game ID", "White Player", "Black Player", "Status", "Spectators")
        tree = ttk.Treeview(games_frame, columns=columns, show="headings")
        
        # Set column headings
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        # Add games to the treeview
        for i, game in enumerate(games):
            game_id = game["game_id"]
            short_id = f"{game_id[:8]}..."
            tree.insert("", "end", iid=str(i), values=(
                short_id,
                game["white_player"],
                game["black_player"],
                game["status"],
                game["spectator_count"]
            ), tags=(game_id,))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(games_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create a frame for buttons
        button_frame = tk.Frame(games_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create a function to handle selection
        def on_select():
            selected = tree.selection()
            if selected:
                item_id = selected[0]
                game_id = tree.item(item_id, "tags")[0]
                games_dialog.destroy()
                # Join the selected game as a spectator
                self.send_message(SPECTATE_GAME, {"game_id": game_id})
                self.status = "spectating"
                self.status_label.config(text="Status: Spectating")
                self.show_game_screen()
        
        # Create a function to handle manual game ID entry
        def on_manual():
            game_id = manual_entry.get().strip()
            if game_id:
                games_dialog.destroy()
                self.send_message(SPECTATE_GAME, {"game_id": game_id})
                self.status = "spectating"
                self.status_label.config(text="Status: Spectating")
                self.show_game_screen()
        
        # Add select button
        select_button = tk.Button(button_frame, text="Spectate Selected Game", command=on_select)
        select_button.pack(side=tk.LEFT, padx=5)
        
        # Add a separator
        tk.Label(button_frame, text="OR").pack(side=tk.LEFT, padx=10)
        
        # Add manual game ID entry
        tk.Label(button_frame, text="Game ID:").pack(side=tk.LEFT)
        manual_entry = tk.Entry(button_frame, width=20)
        manual_entry.pack(side=tk.LEFT, padx=5)
        
        manual_button = tk.Button(button_frame, text="Join", command=on_manual)
        manual_button.pack(side=tk.LEFT, padx=5)
        
        # Add cancel button
        cancel_button = tk.Button(button_frame, text="Cancel", command=games_dialog.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Enable double-click to select
        tree.bind("<Double-1>", lambda e: on_select())
    
    def handle_player_assigned(self, data):
        """Handle player assignment from server"""
        self.player_color = data.get("color")
        self.game_id = data.get("game_id")
        
        if data.get("status") == "waiting":
            self.status = "waiting"
            self.status_label.config(text=f"Status: Waiting for opponent (Game ID: {self.game_id[:8]})")
        else:
            self.status = "playing"
            self.status_label.config(text=f"Status: Playing as {self.player_color}")
    
    def handle_game_state(self, data):
        """Update game state from server data"""
        # Update board
        self.board = chess.Board(data.get("board_fen"))
        
        # Update UI elements
        self.update_board_display()
        
        opponent = None
        if self.player_color == "white":
            self.opponent_label.config(text=f"Opponent (Black): {data.get('black_player', '-')}")
        elif self.player_color == "black":
            self.opponent_label.config(text=f"Opponent (White): {data.get('white_player', '-')}")
        else:  # Spectating
            self.opponent_label.config(text=f"White: {data.get('white_player', '-')} | Black: {data.get('black_player', '-')}")
        
        self.turn_label.config(text=f"Turn: {data.get('turn', '-').capitalize()}")
        
        if data.get('check'):
            self.turn_label.config(text=f"Turn: {data.get('turn', '-').capitalize()} (CHECK)")
        
        # Update timers
        self.white_time = data.get("white_time", self.white_time)
        self.black_time = data.get("black_time", self.black_time)
        self.update_time_display()
        
        # Update status if game ended
        if data.get("status") == "completed":
            self.status = "game_over"
            self.status_label.config(text="Status: Game Over")
    
    def handle_chat_message(self, data):
        """Add a chat message to the chat window"""
        sender = data.get("sender", "Unknown")
        message = data.get("message", "")
        
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"{sender}: {message}\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
    
    def handle_game_over(self, data):
        """Handle game over notification"""
        reason = data.get("reason", "Game Over")
        self.status = "game_over"
        self.status_label.config(text="Status: Game Over")
        
        messagebox.showinfo("Game Over", reason)
    
    def handle_time_update(self, data):
        """Update time display"""
        self.white_time = data.get("white_time", self.white_time)
        self.black_time = data.get("black_time", self.black_time)
        self.update_time_display()
    
    def update_status(self):
        """Update status display based on current state"""
        if not self.connected:
            self.status_label.config(text="Status: Disconnected")
            messagebox.showwarning("Disconnected", "Connection to server lost")
            self.show_connection_screen()
    
    def update_time_display(self):
        """Update the time displays"""
        white_mins = int(self.white_time // 60)
        white_secs = int(self.white_time % 60)
        black_mins = int(self.black_time // 60)
        black_secs = int(self.black_time % 60)
        
        self.white_time_label.config(text=f"White: {white_mins:02d}:{white_secs:02d}")
        self.black_time_label.config(text=f"Black: {black_mins:02d}:{black_secs:02d}")
    
    def update_board_display(self):
        """Render the chess board on the canvas"""
        # Get board orientation
        flipped = self.player_color == "black"
        
        # Clear the canvas
        self.board_canvas.delete("all")
        
        # Draw the chess board squares
        for rank in range(8):
            for file in range(8):
                # Determine square color (alternating light/dark)
                is_light = (rank + file) % 2 == 0
                color = "#F0D9B5" if is_light else "#B58863"  # Light/dark square colors
                
                # Calculate square position based on board orientation
                if flipped:
                    x1 = (7 - file) * SQUARE_SIZE
                    y1 = rank * SQUARE_SIZE
                else:
                    x1 = file * SQUARE_SIZE
                    y1 = (7 - rank) * SQUARE_SIZE
                    
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                
                # Draw square
                self.board_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
                
                # Get piece at this square, if any
                square = chess.square(file, rank)
                piece = self.board.piece_at(square)
                
                if piece:
                    # Get piece code (e.g., "P" for white pawn, "r" for black rook)
                    piece_code = piece.symbol()
                    
                    # Determine background color of square where piece sits
                    bg = "light" if is_light else "dark"
                    
                    # Draw piece on the square
                    img_key = f"{piece_code}_{bg}"
                    if img_key in self.piece_images:
                        self.board_canvas.create_image(
                            x1 + SQUARE_SIZE//2, 
                            y1 + SQUARE_SIZE//2, 
                            image=self.piece_images[img_key]
                        )
        
        # Highlight the selected square, if any
        if self.selected_square:
            file_idx = chess.square_file(self.selected_square)
            rank_idx = chess.square_rank(self.selected_square)
            
            # Adjust for flipped board
            if flipped:
                x = (7 - file_idx) * SQUARE_SIZE
                y = rank_idx * SQUARE_SIZE
            else:
                x = file_idx * SQUARE_SIZE
                y = (7 - rank_idx) * SQUARE_SIZE
                
            # Draw highlight rectangle
            self.board_canvas.create_rectangle(
                x, y, x + SQUARE_SIZE, y + SQUARE_SIZE,
                outline="blue", width=3
            )
            
            # Draw valid move indicators
            for move in self.valid_moves:
                target = move.to_square
                target_file = chess.square_file(target)
                target_rank = chess.square_rank(target)
                
                # Adjust for flipped board
                if flipped:
                    tx = (7 - target_file) * SQUARE_SIZE + SQUARE_SIZE//2
                    ty = target_rank * SQUARE_SIZE + SQUARE_SIZE//2
                else:
                    tx = target_file * SQUARE_SIZE + SQUARE_SIZE//2
                    ty = (7 - target_rank) * SQUARE_SIZE + SQUARE_SIZE//2
                
                # Draw circle for valid move
                self.board_canvas.create_oval(
                    tx - 5, ty - 5, tx + 5, ty + 5,
                    fill="green", outline="darkgreen"
                )
                
        # Highlight last move
        if len(self.board.move_stack) > 0:
            last_move = self.board.peek()
            from_square = last_move.from_square
            to_square = last_move.to_square
            
            # Get coordinates
            from_file = chess.square_file(from_square)
            from_rank = chess.square_rank(from_square)
            to_file = chess.square_file(to_square)
            to_rank = chess.square_rank(to_square)
            
            # Adjust for flipped board
            if flipped:
                from_x = (7 - from_file) * SQUARE_SIZE
                from_y = from_rank * SQUARE_SIZE
                to_x = (7 - to_file) * SQUARE_SIZE
                to_y = to_rank * SQUARE_SIZE
            else:
                from_x = from_file * SQUARE_SIZE
                from_y = (7 - from_rank) * SQUARE_SIZE
                to_x = to_file * SQUARE_SIZE
                to_y = (7 - to_rank) * SQUARE_SIZE
            
            # Highlight last move squares with semi-transparent yellow
            self.board_canvas.create_rectangle(
                from_x, from_y, from_x + SQUARE_SIZE, from_y + SQUARE_SIZE,
                outline="yellow", width=2
            )
            self.board_canvas.create_rectangle(
                to_x, to_y, to_x + SQUARE_SIZE, to_y + SQUARE_SIZE,
                outline="yellow", width=2
            )
    
    def on_board_click(self, event):
        """Handle clicks on the chess board"""
        # Ignore clicks if not playing or not our turn
        if self.status != "playing" or \
           (self.player_color == "white" and self.board.turn != chess.WHITE) or \
           (self.player_color == "black" and self.board.turn != chess.BLACK):
            return
        
        # Calculate square from click position
        square_size = BOARD_SIZE // 8
        file_idx = event.x // square_size
        rank_idx = event.y // square_size
        
        # Adjust for flipped board
        if self.player_color == "black":
            file_idx = 7 - file_idx
        else:
            rank_idx = 7 - rank_idx
        
        clicked_square = chess.square(file_idx, rank_idx)
        
        # If a square is already selected
        if self.selected_square is not None:
            # Try to make a move
            move = chess.Move(self.selected_square, clicked_square)
            
            # Check for promotion
            if self.board.piece_at(self.selected_square) and \
               self.board.piece_at(self.selected_square).piece_type == chess.PAWN and \
               ((self.board.turn == chess.WHITE and rank_idx == 7) or 
                (self.board.turn == chess.BLACK and rank_idx == 0)):
                move = chess.Move(self.selected_square, clicked_square, promotion=chess.QUEEN)
            
            # If move is valid, send it to server
            if move in self.board.legal_moves:
                self.send_move(move.uci())
                self.selected_square = None
                self.valid_moves = []
            # If clicking on another piece of same color, select that piece
            elif self.board.piece_at(clicked_square) and \
                 self.board.piece_at(clicked_square).color == self.board.turn:
                self.selected_square = clicked_square
                self.valid_moves = [move for move in self.board.legal_moves if move.from_square == clicked_square]
                self.update_board_display()
            # Otherwise deselect
            else:
                self.selected_square = None
                self.valid_moves = []
                self.update_board_display()
        else:
            # Select the square if it contains a piece of the correct color
            piece = self.board.piece_at(clicked_square)
            if piece and ((self.player_color == "white" and piece.color == chess.WHITE) or 
                         (self.player_color == "black" and piece.color == chess.BLACK)):
                self.selected_square = clicked_square
                self.valid_moves = [move for move in self.board.legal_moves if move.from_square == clicked_square]
                self.update_board_display()
    
    def send_move(self, move_uci):
        """Send a move to the server"""
        if not self.connected:
            messagebox.showwarning("Disconnected", "Not connected to server")
            return
        
        self.send_message(MAKE_MOVE, {"move": move_uci})
    
    def send_chat_message(self, event=None):
        """Send a chat message"""
        if not self.connected:
            messagebox.showwarning("Disconnected", "Not connected to server")
            return
        
        message = self.chat_entry.get()
        if message:
            self.send_message(CHAT_MESSAGE, {"message": message})
            self.chat_entry.delete(0, tk.END)
    
    def send_message(self, msg_type, data):
        """Send a message to the server"""
        if not self.connected:
            return
        
        try:
            message = create_message(msg_type, data)
            self.client_socket.sendall(message + b'\n')
        except Exception as e:
            print(f"Error sending message: {e}")
            self.connected = False
            self.update_status()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessClient(root)
    root.mainloop()
