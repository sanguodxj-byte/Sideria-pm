from PIL import Image
import os
from pathlib import Path

def convert():
    input_path = 'happy2.png'
    output_path = 'sideria-pm.ico'
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found")
        return
    
    img = Image.open(input_path)
    # Common sizes for Windows icons
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_path, sizes=icon_sizes)
    print(f"Successfully converted {input_path} to {output_path}")

if __name__ == "__main__":
    convert()
