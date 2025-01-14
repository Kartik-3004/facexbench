import os
import json
import sys
import re
from collections import defaultdict
import argparse

def extract_option_label(model_output, option_labels, options):
    # Remove any leading/trailing whitespace
    model_output_clean = model_output.strip()
    
    # Define regex patterns to match option labels
    label_patterns = [
        r'\b\(?([A-Za-z])\)?\b',         # Matches 'A', '(A)', etc.
        r'\bOption\s+([A-Za-z])\b',      # Matches 'Option A', etc.
        r'\b([A-Za-z])\.',               # Matches 'A.', etc.
        r'\b([A-Za-z]):',                # Matches 'A:', etc.
        r'\b([A-Za-z])\s+-',             # Matches 'A -', etc.
        r'\b\(([A-Za-z])\)',             # Matches '(A)', etc.
    ]
    
    model_output_start = model_output_clean
    for pattern in label_patterns:
        match = re.match(pattern, model_output_start)
        if match:
            label = match.group(1)
            if label in option_labels:
                return label

    # If not found at the beginning, search the entire text
    for pattern in label_patterns:
        matches = re.findall(pattern, model_output_clean)
        for label in matches:
            if label in option_labels:
                return label

    # If no label found, try to match the output to the option texts exactly
    for idx, option_text in enumerate(options):
        option_text_stripped = str(option_text).strip()
        if option_text_stripped == model_output_clean.strip():
            return option_labels[idx]
        elif option_text_stripped in model_output_clean:
            return option_labels[idx]
    
    return None

def main():
    parser = argparse.ArgumentParser(description="Process FacexBench results.")
    parser.add_argument('--model', type=str, required=True, help='Name of the model')
    parser.add_argument('--results_dir', type=str, required=True, help='Directory containing result JSON files')
    args = parser.parse_args()

    model_name = args.model
    results_dir = args.results_dir

    if not os.path.exists(results_dir):
        print(f"Directory {results_dir} does not exist.")
        sys.exit(1)

    categories_subcategories = {
        'bias_fairness': ['age', 'gender', 'race'],
        'attributes_expression': ['expression', 'attributes'],
        'face_localization': ['headpose', 'segmentation', 'crowd_counting'],
        'face_recognition': ['hr_fr', 'lr_fr', 'celebrity_identification'],
        'fas_deepfakes': ['fas', 'deepfakes'],
        "tools_use": ['tools_retrieval']
    }

    total_correct = 0
    total_questions = 0

    category_counts = defaultdict(lambda: {'correct': 0, 'total': 0})
    subcategory_counts = defaultdict(lambda: {'correct': 0, 'total': 0})
    num_images_counts = defaultdict(lambda: {'correct': 0, 'total': 0})

    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if file.endswith('.json'):
                json_path = os.path.join(root, file)
                with open(json_path, 'r') as f:
                    data = json.load(f)

                category = data.get('category', 'unknown')
                subcategory = data.get('sub-category', 'unknown')
                num_images = data.get('num_images', 'unknown')

                questions = data.get('questions', {})
                for q_id, q_data in questions.items():
                    total_questions += 1
                    category_counts[category]['total'] += 1
                    subcategory_counts[subcategory]['total'] += 1
                    num_images_counts[num_images]['total'] += 1

                    correct_answer_option = q_data.get('correct_answer_option')
                    prediction = q_data.get('prediction', '')

                    options_list = q_data.get('options', [])
                    num_options = len(options_list)

                    option_labels = [chr(ord('A') + i) for i in range(num_options)]

                    extracted_prediction = extract_option_label(prediction, option_labels, options_list)

                    q_data['prediction_answer_option'] = extracted_prediction

                    if extracted_prediction == correct_answer_option:
                        total_correct += 1
                        category_counts[category]['correct'] += 1
                        subcategory_counts[subcategory]['correct'] += 1
                        num_images_counts[num_images]['correct'] += 1

                # Write updated JSON
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)

    # Compute overall accuracy
    total_accuracy = (total_correct / total_questions) * 100 if total_questions > 0 else 0

    # Write results to file
    results_file = os.path.join(results_dir, 'results.txt')
    with open(results_file, 'w') as f:
        f.write(f"Model Name: {model_name} | Total Questions: {total_questions}\n")
        f.write(f"Total Accuracy: {total_accuracy:.2f}% ({total_correct}/{total_questions})\n\n")

        f.write("Category Accuracies:\n")
        for category, counts in category_counts.items():
            correct = counts['correct']
            total = counts['total']
            accuracy = (correct / total) * 100 if total > 0 else 0
            f.write(f"{category}: {accuracy:.2f}% ({correct}/{total})\n")

        f.write("\nSub-category Accuracies:\n")
        for subcategory, counts in subcategory_counts.items():
            correct = counts['correct']
            total = counts['total']
            accuracy = (correct / total) * 100 if total > 0 else 0
            f.write(f"{subcategory}: {accuracy:.2f}% ({correct}/{total})\n")

        f.write("\nNumber of Images Accuracies:\n")
        for num_images, counts in num_images_counts.items():
            correct = counts['correct']
            total = counts['total']
            accuracy = (correct / total) * 100 if total > 0 else 0
            f.write(f"{num_images}: {accuracy:.2f}% ({correct}/{total})\n")

if __name__ == '__main__':
    main()
