# Huuda

Huuda is a command-line text-to-speech (TTS) utility designed to humorously twist spoken output by applying Finnish phonetics to English text, resulting in a "Finglish" accent. It's perfect for anyone looking for a light-hearted way to hear text read aloud, whether for entertainment, testing TTS engines, or just for the joy of hearing Finnish-inflected English.

## Features

- Convert text to speech with a Finnish accent applied to English words.
- Customize the TTS voice and volume.
- Use a word replacement feature to modify text before speech synthesis.
- Support for input text via command line or file.

## Installation

To use Huuda, you need to have Python installed on your system as well as the following dependencies:

- `text2wave` for text-to-speech synthesis.
- `sox` for audio processing.
- `play` for audio playback.

These tools are commonly available in UNIX-like environments.

## Usage

Run `huuda.py` with the necessary arguments:

```bash
python huuda.py --voice <voice_option> --text "Your text here"
python huuda.py --file yourfile.txt
```

# Options include:

`--blast` to increase the volume.
`--voice` to set the TTS voice.
`--text` or `-t`to provide text directly.
`--file` or `-f` to specify a text file for input.
`--replacement_file` to specify a custom word replacement file separately.

# Word Replacement Management

- Use list_converter.py to convert a list of sed-style replacement commands into the JSON format expected by Huuda.

- Run word_adder.py to interactively add new word replacements to your JSON file.

# Contributing

Contributions to Huuda are welcome! Feel free to fork the repository, make your changes, and submit a pull request.

# License

Go for it.

# Acknowledgments

Thank you to all contributors and users who have made Huuda a fun project to work on!
Special thanks to ChaosWhisperer for code refactoring help 
