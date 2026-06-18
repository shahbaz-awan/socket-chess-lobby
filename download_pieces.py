import os
import requests
from PIL import Image
from io import BytesIO
import time
from config import SQUARE_SIZE

def download_chess_pieces():
    """Download chess piece images and save them to cache with black and white theme"""
    print("Downloading chess piece images with black and white theme...")
    
    # Define piece types and colors
    pieces = {'p': 'pawn', 'n': 'knight', 'b': 'bishop', 'r': 'rook', 'q': 'queen', 'k': 'king'}
    colors = {'w': 'white', 'b': 'black'}
    
    # Create a directory for cached images if it doesn't exist
    cache_dir = os.path.join(os.path.dirname(__file__), "chess_pieces_bw")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Define black and white square colors
    light_square = (255, 255, 255)  # White
    dark_square = (0, 0, 0)  # Black
    
    # Download images for all pieces and backgrounds
    for color_key, color_name in colors.items():
        for piece_key, piece_name in pieces.items():
            # Load for both light and dark squares
            for bg_name, bg_color in [("light", light_square), ("dark", dark_square)]:
                cache_path = os.path.join(cache_dir, f"{color_key}_{piece_key}_{bg_name}.png")
                
                if not os.path.exists(cache_path):
                    try:
                        # Download piece image from Chess.com
                        piece_url = f"https://images.chesscomfiles.com/chess-themes/pieces/neo/150/{color_key}{piece_key}.png"
                        response = requests.get(piece_url)
                        
                        if response.status_code == 200:
                            # Create a new image with the background color
                            piece_img = Image.open(BytesIO(response.content)).convert("RGBA")
                            img = Image.new("RGB", (SQUARE_SIZE, SQUARE_SIZE), bg_color)
                            
                            # Resize the piece image to fit the square
                            piece_size = int(SQUARE_SIZE * 0.85)
                            piece_img = piece_img.resize((piece_size, piece_size), Image.LANCZOS)
                            
                            # Center the piece on the background
                            position = ((SQUARE_SIZE - piece_size) // 2, (SQUARE_SIZE - piece_size) // 2)
                            img.paste(piece_img, position, piece_img)
                            
                            # Save to cache
                            img.save(cache_path)
                            print(f"Downloaded {color_name} {piece_name} piece on {bg_name} square")
                            time.sleep(0.1)  # To not flood the server with requests
                        else:
                            print(f"Failed to download {color_name} {piece_name} piece: HTTP {response.status_code}")
                    except Exception as e:
                        print(f"Error downloading {color_name} {piece_name} piece: {e}")

if __name__ == "__main__":
    download_chess_pieces()
    print("All piece images downloaded and cached in black and white theme!")
