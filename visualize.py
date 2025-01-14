import json
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import textwrap
import glob
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

def get_json_files(directory):
    """Get all JSON files from the directory"""
    return glob.glob(os.path.join(directory, "*.json"))

def read_json(json_path):
    """Read and parse the JSON file"""
    with open(json_path, 'r') as f:
        data = json.load(f)
        return data

def load_and_resize_image(image_path, target_height=224):
    """Load an image and resize it maintaining aspect ratio"""
    img = cv2.imread(image_path)
    if img is None:
        logging.warning(f"Could not load image: {image_path}")
        # Create a blank image if the file cannot be read
        img = np.zeros((target_height, target_height, 3), dtype=np.uint8)
        cv2.putText(img, "Image Not Found", (10, target_height//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    else:
        # Calculate new width to maintain aspect ratio
        aspect_ratio = img.shape[1] / img.shape[0]
        new_width = int(target_height * aspect_ratio)
        img = cv2.resize(img, (new_width, target_height))
    return img

def concatenate_images(images):
    """Concatenate multiple images horizontally"""
    if not images:
        return None
    # Find max height
    max_height = max(img.shape[0] for img in images)
    # Resize all images to have the same height
    resized_images = []
    for img in images:
        if img.shape[0] != max_height:
            aspect_ratio = img.shape[1] / img.shape[0]
            new_width = int(max_height * aspect_ratio)
            img_resized = cv2.resize(img, (new_width, max_height))
            resized_images.append(img_resized)
        else:
            resized_images.append(img)
    # Concatenate horizontally
    return np.hstack(resized_images)

def create_text_image(question_text, options, correct_answer_option, target_width=600):
    """Create an image with question text and options"""
    # Ensure all inputs are strings
    question_text = str(question_text)
    options = [str(opt) for opt in options]
    correct_answer_option = str(correct_answer_option)
    
    # Create a new PIL Image with white background
    font_size = 24
    padding = 20
    # Approximate height
    num_lines = len(textwrap.wrap(question_text, width=50))
    num_lines += sum(len(textwrap.wrap(opt, width=50)) for opt in options)
    height = (font_size + 5) * num_lines + padding * 2 + 100  # Additional space for answer

    img = Image.new('RGB', (target_width, height), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Wrap question text
    wrapped_question = textwrap.wrap(f"Q: {question_text}", width=50)

    y_position = padding

    # Draw question
    for line in wrapped_question:
        draw.text((padding, y_position), line, font=font, fill='black')
        y_position += font_size + 5

    y_position += 20  # Add space between question and options

    # Draw options
    option_letters = ['A', 'B', 'C', 'D']
    for letter, option in zip(option_letters, options):
        # Highlight the correct option
        color = 'black'
        if letter == correct_answer_option:
            color = 'blue'
        option_text = f"{letter}. {option}"
        wrapped_option = textwrap.wrap(option_text, width=50)
        for line in wrapped_option:
            draw.text((padding, y_position), line, font=font, fill=color)
            y_position += font_size + 5
        y_position += 10

    # Add correct answer information
    y_position += 10
    draw.text((padding, y_position), f"Correct Answer: {correct_answer_option}", font=font, fill='blue')
    y_position += font_size + 5

    # Convert PIL Image to OpenCV format
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def process_question(question_data, output_dir, question_id):
    """Process a single question"""
    # Load images
    images = []
    for img_path in question_data["image_paths"]:
        img = load_and_resize_image(img_path)
        if img is not None:
            images.append(img)

    if not images:
        logging.warning(f"No valid images found for question {question_id}")
        return

    combined_images = concatenate_images(images)

    # Ensure the data is in the correct format
    question_text = question_data.get("question_text", "")
    options = question_data.get("options", [])
    correct_answer_option = question_data.get("correct_answer_option", "")

    # Create text image
    text_image = create_text_image(
        question_text,
        options,
        correct_answer_option
    )

    # Combine images and text
    final_height = max(combined_images.shape[0], text_image.shape[0])

    # Resize both images to match height
    combined_images = cv2.resize(combined_images,
                                (int(combined_images.shape[1] * final_height / combined_images.shape[0]),
                                 final_height))
    text_image = cv2.resize(text_image,
                            (int(text_image.shape[1] * final_height / text_image.shape[0]),
                             final_height))

    # Concatenate horizontally
    final_image = np.hstack([combined_images, text_image])

    # Save image
    output_path = os.path.join(output_dir, f"question_{question_id}.png")
    cv2.imwrite(output_path, final_image)

def process_single_json(json_path, base_output_dir):
    """Process a single JSON file"""
    # Create output directory based on JSON filename
    json_name = os.path.basename(json_path).replace('.json', '')
    output_dir = os.path.join(base_output_dir, json_name)
    os.makedirs(output_dir, exist_ok=True)

    # Read JSON data
    data = read_json(json_path)
    questions = data.get("questions", {})

    for question_id, question_data in questions.items():
        process_question(question_data, output_dir, question_id)

def process_all_jsons(input_dir, base_output_dir):
    """Process all JSON files in the directory"""
    json_files = get_json_files(input_dir)
    logging.info(f"Found {len(json_files)} JSON files to process")

    for json_file in json_files:
        json_name = os.path.basename(json_file).replace('.json', '')
        logging.info(f"Processing {json_name}")
        process_single_json(json_file, base_output_dir)
        logging.info(f"Completed {json_name}")
        
def main():
    input_dir = "./benchmark/"  # Replace with your input directory path
    output_dir = "./visualization"  # Replace with your output directory path

    os.makedirs(output_dir, exist_ok=True)

    process_all_jsons(input_dir, output_dir)
    logging.info("Processing Complete!")

if __name__ == "__main__":
    main()
