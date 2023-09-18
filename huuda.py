import os
import subprocess
import json
import argparse
import re
import tempfile

# Set your default replacement file here
DEFAULT_REPLACEMENT_FILE = "wordreplacement.json"

def is_file_empty(file_path):
    return os.path.getsize(file_path) == 0

def load_replacement_dict(json_file):
    if is_file_empty(json_file):
        print("Error: The JSON replacement file is empty.")
        return {}
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def replace_text(input_text, replacement_dict, replace_english):
    replaced_text = input_text  # Initialize with the original text
    if replace_english:
        for word, info in replacement_dict.items():
            replacement = info['replacement']
            flags = re.IGNORECASE if info['case_insensitive'] else 0
            escaped_word = re.escape(word)
            replaced_text, count = re.subn(escaped_word, replacement, replaced_text, flags=flags)
            if count > 0:
                print(f"Replaced '{word}' with '{replacement}'")  # Debugging line
    return replaced_text

def text_to_speech(text, voice, replacement_dict, blast_mode=False, replace_english=False):
    text = replace_text(text, replacement_dict, replace_english)
    print(f"Input text after replacement: '{text}'")  # Debugging line
    if not text.strip():
        print("Error: The text to be spoken is empty.")
        return

    # Encode the text to ISO-8859-1 (latin1)
    text = text.encode("ISO-8859-1")

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_text_file, \
         tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file, \
         tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_norm_file:

        with open(temp_text_file.name, 'wb') as f:
            f.write(text)

        result = subprocess.run(["text2wave", "-o", temp_audio_file.name, "-eval", voice, temp_text_file.name],
                                capture_output=True, text=True)
        if result.returncode != 0 or is_file_empty(temp_audio_file.name):
            print("text2wave failed:", result.stderr)
            return

        sox_options = ["-v", "40"] if blast_mode else []
        result = subprocess.run(["sox"] + sox_options + [temp_audio_file.name, temp_audio_norm_file.name, "--norm"],
                                capture_output=True, text=True)
        if result.returncode != 0 or is_file_empty(temp_audio_norm_file.name):
            print("sox failed:", result.stderr)
            return

        result = subprocess.run(["play", temp_audio_norm_file.name], capture_output=True, text=True)
        if result.returncode != 0:
            print("play failed:", result.stderr)

parser = argparse.ArgumentParser(description="Text-to-speech utility")
parser.add_argument('--blast', action='store_true', help="Enable blast mode to increase volume")
parser.add_argument('--voice', type=str, default="(voice_hy_fi_mv_diphone)", help="Voice for text-to-speech")
parser.add_argument('--text', type=str, required=True, help="Text to speak")
parser.add_argument('--replacement_file', type=str, help="JSON file with word replacements")
parser.add_argument('--english', '--eng', '--en', '--e', '--finglish', dest='replace_english', action='store_true',
                    help="Replace words when set (default is not to replace)")

args = parser.parse_args()

if not args.replace_english:
    print("English word replacement is disabled.")
    replacement_dict = {}
else:
    if args.replacement_file and not is_file_empty(args.replacement_file):
        replacement_dict = load_replacement_dict(args.replacement_file)
    else:
        if os.path.exists(DEFAULT_REPLACEMENT_FILE) and not is_file_empty(DEFAULT_REPLACEMENT_FILE):
            replacement_dict = load_replacement_dict(DEFAULT_REPLACEMENT_FILE)
        else:
            print("No valid replacement file provided. English word replacement is disabled.")
            replacement_dict = {}

text_to_speech(args.text, args.voice, replacement_dict, blast_mode=args.blast, replace_english=args.replace_english)
