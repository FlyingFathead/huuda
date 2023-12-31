# Huuda

Huuda is a command-line text-to-speech (TTS) utility that not only speaks Finnish from input text or text files from the command line using the public domain `festvox` libraries, but is also designed to humorously twist spoken output by applying Finnish phonetics to English text, resulting in a "Finglish" accent. It's perfect for anyone looking for a light-hearted way to hear text read aloud, whether for entertainment, testing TTS engines, or just for the joy of hearing Finnish-inflected English.

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

These tools are commonly available in UNIX-like environments. Ensure you have Python installed, then set up Huuda with:

```bash
# For Debian-based systems, use:
sudo apt-get install festvox-suopuhe-lj festvox-suopuhe-mv sox play
```

## Usage

Run `huuda.py` with the necessary arguments:

```bash
python huuda.py --voice <voice_option> --text "Your text here"
python huuda.py --file yourfile.txt
```

Or, for English/Finglish
```bash
python huuda.py --finglish --text "It's very nice here."
```

# Options include:

`--english`, `--eng`, `--en`, `--e`, `--finglish` to speak in English/Finglish instead of Finnish
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

This project is freely available under the "Go for it" ethos, akin to The Unlicense or WTFPL. Use, modify, and distribute as you please. Enjoy!

# Acknowledgments

Thank you to all contributors and users who have made Huuda a fun project to work on! Special shoutout to ChaosWhisperer for code refactoring help.
