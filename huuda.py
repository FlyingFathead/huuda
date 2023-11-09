# huuda // python edition // v0.004 // nov 9 2023
# FlyingFathead (refactoring w/ ChaosWhisperer)
# https://github.com/FlyingFathead

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

# remove non-latin1 chars
def strip_non_latin1(text):
    return text.encode('ISO-8859-1', 'ignore').decode('ISO-8859-1')

def replace_text(input_text, replacement_dict, replace_english):
    replaced_text = input_text  # Initialize with the original text
    if replace_english:
        # Sort keys by length, in descending order
        for word in sorted(replacement_dict.keys(), key=len, reverse=True):
            info = replacement_dict[word]
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

    # Before encoding the text in the text_to_speech function
    text = strip_non_latin1(text)

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
parser.add_argument('--text', '-t', '--t', type=str, required=False, help="Text to speak")
parser.add_argument('--replacement_file', type=str, help="JSON file with word replacements")
parser.add_argument('--english', '--eng', '--en', '--e', '--finglish', dest='replace_english', action='store_true',
                    help="Replace words when set (default is not to replace)")
# Add a new argument for input file with multiple flags
parser.add_argument('--inputfile', '--file', '-f', dest='inputfile', type=str, help="Text file to read text from")

args = parser.parse_args()

if not args.text and not args.inputfile:
    print("Error: Either --text or --inputfile (or: --f) must be provided.")
    exit(1)

# If --inputfile is specified, read from the file
if args.inputfile:
    try:
        with open(args.inputfile, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: File {args.inputfile} not found.")
        exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        exit(1)
else:
    text = args.text  # Read from command line argument

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

text_to_speech(text, args.voice, replacement_dict, blast_mode=args.blast, replace_english=args.replace_english)
