import json
import os
import random
from PIL import Image, ImageDraw, ImageFont

def generate_placeholder_image(width, height, text, output_path):
    """Generates a placeholder image with a random background color and text."""
    # Generate a random pastel color
    bg_color = (
        random.randint(200, 255),
        random.randint(200, 255),
        random.randint(200, 255)
    )
    
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Use a basic font
    try:
        font = ImageFont.truetype("arial.ttf", size=20)
    except IOError:
        font = ImageFont.load_default()

    # Calculate text position
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2
    
    draw.text((text_x, text_y), text, fill=(0, 0, 0), font=font)
    
    img.save(output_path)

def main():
    """
    Reads the local test JSON, generates placeholder images,
    and creates a new JSON file with updated image URLs.
    """
    # Define paths
    source_json_path = 'kiosk_data.json' # Read from the data file
    output_json_path = 'kiosk_data.json' # Overwrite the same file
    images_dir = 'images'

    # Create images directory if it doesn't exist
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        print(f"Created directory: {images_dir}")

    # Load the source JSON data
    try:
        with open(source_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Source JSON file not found at {source_json_path}")
        return

    # Process place_images
    if 'place_images' in data:
        print(f"Generating {len(data['place_images'])} placeholder images...")
        for image_data in data['place_images']:
            img_id = image_data['image_id']
            width = image_data.get('width') or 640  # Use default if width is 0 or None
            height = image_data.get('height') or 480 # Use default if height is 0 or None
            
            filename = f"image_{img_id}.png"
            image_dir_path = os.path.join(images_dir)
            if not os.path.exists(image_dir_path):
                os.makedirs(image_dir_path)

            output_path = os.path.join(image_dir_path, filename)
            local_url = os.path.join('db-server', images_dir, filename).replace("\\", "/")

            # If a real image already exists, keep it and just point to the local path.
            if os.path.exists(output_path):
                image_data['url'] = local_url
                continue
            
            # Generate the placeholder image
            text = f"{width} x {height}"
            generate_placeholder_image(width, height, text, output_path)
            
            # Update the URL to the local path relative to the project root
            image_data['url'] = local_url
        print("Image generation complete.")

    # Write the updated data to the new JSON file
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully created {output_json_path} with updated image paths.")

if __name__ == '__main__':
    main()
