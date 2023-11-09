import json

def update_json_file(filename, original_word, replacement_word):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    except json.JSONDecodeError:
        print("Error: Invalid JSON format.")
        return

    data[original_word] = {
        "replacement": replacement_word,
        "case_insensitive": True
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    filename = "wordreplacement.json"  # Or your specific JSON filename
    original_word = input("Enter the original word: ")
    replacement_word = input("Enter the replacement word: ")
    
    update_json_file(filename, original_word, replacement_word)