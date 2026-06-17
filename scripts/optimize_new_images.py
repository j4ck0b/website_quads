#!/usr/bin/env python3
import os
import subprocess
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MULTIMEDIA_DIR = os.path.join(BASE_DIR, "multimedia")
ORIGINALS_DIR = os.path.join(MULTIMEDIA_DIR, "originals")

def main():
    # 1. Create originals directory if it doesn't exist
    os.makedirs(ORIGINALS_DIR, exist_ok=True)

    # 2. Get the list of untracked files in multimedia
    try:
        # Run git status/ls-files to find untracked files in multimedia/
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "multimedia/"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        untracked_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except Exception as e:
        print(f"Error checking git untracked files: {e}")
        # Fallback to manual listing of files in multimedia/
        all_files = os.listdir(MULTIMEDIA_DIR)
        untracked_files = [os.path.join("multimedia", f) for f in all_files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.heic'))]

    if not untracked_files:
        print("No new untracked images found in multimedia/ directory.")
        return

    print(f"Found {len(untracked_files)} new images to process:")
    for f in untracked_files:
        print(f" - {f}")

    print("\nStarting optimization process...\n")

    summary = []

    for file_rel_path in untracked_files:
        file_path = os.path.join(BASE_DIR, file_rel_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        # Check if the file actually exists
        if not os.path.exists(file_path):
            continue

        # Skip files already in originals folder or not images
        if "originals/" in file_rel_path or ext_lower not in ['.jpg', '.jpeg', '.png', '.heic']:
            continue

        print(f"Processing: {filename} ({os.path.getsize(file_path) / (1024*1024):.2f} MB)")

        temp_jpg_created = False
        img_to_open = file_path

        # Handle HEIC files using macOS sips
        if ext_lower == '.heic':
            temp_jpg_path = os.path.join(MULTIMEDIA_DIR, f"{name}_temp.jpg")
            print(f" -> Converting HEIC to JPEG using sips...")
            try:
                subprocess.run(["sips", "-s", "format", "jpeg", file_path, "--out", temp_jpg_path], check=True, capture_output=True)
                img_to_open = temp_jpg_path
                temp_jpg_created = True
            except Exception as e:
                print(f" -> ERROR: Failed to convert HEIC {filename}: {e}")
                continue

        try:
            # Open the image
            with Image.open(img_to_open) as img:
                # Correct orientation using EXIF
                img = ImageOps.exif_transpose(img)
                
                width, height = img.size
                orientation = "portrait" if height > width else "landscape"
                aspect_ratio = width / height
                
                print(f" -> Dimensions: {width}x{height} ({orientation})")

                # Define output paths
                out_full_name = f"{name}_full.webp"
                out_thumb_name = f"{name}_thumb.webp"
                out_full_path = os.path.join(MULTIMEDIA_DIR, out_full_name)
                out_thumb_path = os.path.join(MULTIMEDIA_DIR, out_thumb_name)

                # Generate Full Size (max 1920px)
                if max(width, height) > 1920:
                    if orientation == "landscape":
                        new_w = 1920
                        new_h = int(1920 / aspect_ratio)
                    else:
                        new_h = 1920
                        new_w = int(1920 * aspect_ratio)
                    img_full = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                else:
                    img_full = img

                # Save Full Size WebP
                img_full.save(out_full_path, "WEBP", quality=82)
                full_size_kb = os.path.getsize(out_full_path) / 1024

                # Generate Thumbnail (max 800px)
                if max(width, height) > 800:
                    if orientation == "landscape":
                        new_w_t = 800
                        new_h_t = int(800 / aspect_ratio)
                    else:
                        new_h_t = 800
                        new_w_t = int(800 * aspect_ratio)
                    img_thumb = img.resize((new_w_t, new_h_t), Image.Resampling.LANCZOS)
                else:
                    img_thumb = img

                # Save Thumbnail WebP
                img_thumb.save(out_thumb_path, "WEBP", quality=80)
                thumb_size_kb = os.path.getsize(out_thumb_path) / 1024

                print(f" -> Optimized full: {out_full_name} ({full_size_kb:.1f} KB)")
                print(f" -> Optimized thumb: {out_thumb_name} ({thumb_size_kb:.1f} KB)")

                summary.append({
                    "original_name": filename,
                    "original_size_mb": os.path.getsize(file_path) / (1024*1024),
                    "orientation": orientation,
                    "width": width,
                    "height": height,
                    "full_name": out_full_name,
                    "full_size_kb": full_size_kb,
                    "thumb_name": out_thumb_name,
                    "thumb_size_kb": thumb_size_kb
                })

        except Exception as e:
            print(f" -> ERROR processing image {filename}: {e}")
            if temp_jpg_created and os.path.exists(temp_jpg_path):
                os.remove(temp_jpg_path)
            continue

        # Clean up temporary JPEG
        if temp_jpg_created and os.path.exists(temp_jpg_path):
            os.remove(temp_jpg_path)

        # Move the original file to originals folder
        dest_original_path = os.path.join(ORIGINALS_DIR, filename)
        try:
            os.rename(file_path, dest_original_path)
            print(f" -> Moved original to multimedia/originals/")
        except Exception as e:
            print(f" -> ERROR moving original file {filename}: {e}")

    # Write summary report
    print("\n==================================================")
    print("Optimization Complete!")
    print(f"Processed {len(summary)} images.")
    print("==================================================")
    
    # We can print markdown formatting to easily copy-paste or write to a report
    for item in summary:
        print(f"| {item['original_name']} | {item['orientation']} | {item['width']}x{item['height']} | {item['original_size_mb']:.2f} MB | {item['full_name']} ({item['full_size_kb']:.1f} KB) | {item['thumb_name']} ({item['thumb_size_kb']:.1f} KB) |")

if __name__ == "__main__":
    main()
