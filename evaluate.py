import os
import json
import argparse
from dotenv import load_dotenv
from vlmeval.config import supported_VLM


load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="VLM Evaluation Script")
    parser.add_argument('--model', type=str, required=True, help="Model name from the supported_VLM dictionary")
    parser.add_argument('--prepend_text', action='store_true', help='Include prepend text if available')
    args = parser.parse_args()

    model_name = args.model

    if model_name not in supported_VLM:
        print(f"Model '{model_name}' is not supported.")
        return

    json_dir = 'facexbench/benchmark'
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]

    output_dir = os.path.join('facexbench/results', model_name)
    os.makedirs(output_dir, exist_ok=True)

    processed_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    remaining_json_files = [f for f in json_files if f not in processed_files]

    if not remaining_json_files:
        print(f"All JSON files have already been evaluated for model '{model_name}'.")
        return

    print(f"Evaluating model: {model_name}")
    model = supported_VLM[model_name]()
    print("Model Loaded")

    for json_file in remaining_json_files:
        print(f"Processing JSON file: {json_file}")
        json_path = os.path.join(json_dir, json_file)
        with open(json_path, 'r') as f:
            data = json.load(f)

        correct_answers = 0
        total_questions = len(data['questions'])
        option_labels = ['A', 'B', 'C', 'D'] 

        for q_id, question in data['questions'].items():
            question_text = ''
            if data["category"] == "tools_use":
                question_text += data['context'] + '\n'

            if args.prepend_text and data.get('prepend_text'):
                question_text += data['prepend_text'] + '\n'

            question_text += question['question_text'] + '\n'

            if data.get('postpend_text'):
                question_text += data['postpend_text'] + '\n'

            options_text = ''
            for idx, option in enumerate(question['options']):
                if idx >= len(option_labels):
                    print(f"Warning: More options than labels available for question {q_id}")
                    break
                options_text += f"({option_labels[idx]}) {option}\n"

            question_text += options_text

            question_input = question['image_paths'] + [question_text]

            ret = model.generate(question_input, dataset="MCQ")

            model_output = ret.strip()
            options = question['options']
            model_answer = model_output
            question['prediction'] = model_answer

        output_path = os.path.join(output_dir, json_file)

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=4)

if __name__ == '__main__':
    main()
