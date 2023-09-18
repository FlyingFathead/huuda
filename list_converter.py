import json
import re
import sys

def unescape_string(s):
    s = re.sub(r'\\,', ',', s)
    s = re.sub(r'\\.', '.', s)
    return s

def parse_sed_to_json(infile):
    replacement_dict = {}
    
    # Compile the regex pattern to match sed commands
    pattern = re.compile(r'sed -i "s/(.*?)/(.*?)/(gI|g|I)" "\$spk"')
    
    # Read each line from the infile
    with open(infile, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            # Extract the original string, replacement string, and flags
            original, replacement, flags = match.groups()
            
            # Unescape the strings
            original = unescape_string(original)
            replacement = unescape_string(replacement)
            
            # Handle case insensitivity and global replacement
            case_insensitive = 'I' in flags
            global_replace = 'g' in flags
            
            # Add to the dictionary
            replacement_dict[original] = {
                "replacement": replacement,
                "case_insensitive": case_insensitive,
                "global": global_replace
            }
    
    # Write to a JSON file
    json_file = infile.split('.')[0] + '.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(replacement_dict, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: list_converter.py <infile>")
    else:
        infile = sys.argv[1]
        parse_sed_to_json(infile)