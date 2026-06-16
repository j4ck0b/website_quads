#!/usr/bin/env python3
import os
from PIL import Image

def make_square_icon(src_path, target_size, padding_pct=0.08):
    # Open the logo and convert to RGBA
    img = Image.open(src_path).convert('RGBA')
    
    # Get the bounding box of non-transparent content
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    w, h = img.size
    
    # Calculate the max dimension allowed for the logo within the square
    max_dim = int(target_size * (1 - 2 * padding_pct))
    
    # Calculate scale maintaining aspect ratio
    if w > h:
        new_w = max_dim
        new_h = int(h * (max_dim / w))
    else:
        new_h = max_dim
        new_w = int(w * (max_dim / h))
        
    # Prevent resizing to 0
    new_w = max(1, new_w)
    new_h = max(1, new_h)
    
    # Resize logo
    resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
    resized_logo = img.resize((new_w, new_h), resample_filter)
    
    # Create new transparent square canvas
    square = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 0))
    
    # Center the logo on the canvas
    x = (target_size - new_w) // 2
    y = (target_size - new_h) // 2
    square.paste(resized_logo, (x, y), resized_logo)
    
    return square

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, "multimedia", "prime_quads_logo.png")
    
    if not os.path.exists(logo_path):
        print(f"Error: Logo file not found at {logo_path}")
        return
        
    print(f"Loading source logo from {logo_path}...")
    
    # 1. Generate favicon.png (192x192) - standard for Google multiple of 48px square
    print("Generating favicon.png (192x192)...")
    fav_png = make_square_icon(logo_path, 192, padding_pct=0.08)
    fav_png.save(os.path.join(base_dir, "favicon.png"), "PNG")
    
    # 2. Generate favicon-512.png (512x512) - high-resolution backup / app icon
    print("Generating favicon-512.png (512x512)...")
    fav_512 = make_square_icon(logo_path, 512, padding_pct=0.08)
    fav_512.save(os.path.join(base_dir, "favicon-512.png"), "PNG")
    
    # 3. Generate favicon.ico containing 16x16, 32x32, 48x48 layers
    print("Generating favicon.ico (multi-layer)...")
    ico_16 = make_square_icon(logo_path, 16, padding_pct=0.0)
    ico_32 = make_square_icon(logo_path, 32, padding_pct=0.0)
    ico_48 = make_square_icon(logo_path, 48, padding_pct=0.0)
    
    ico_path = os.path.join(base_dir, "favicon.ico")
    ico_16.save(
        ico_path, 
        format="ICO", 
        append_images=[ico_32, ico_48], 
        sizes=[(16, 16), (32, 32), (48, 48)]
    )
    
    print("All favicon assets generated successfully!")

if __name__ == "__main__":
    main()
