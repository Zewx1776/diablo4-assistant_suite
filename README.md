# Diablo 4 Masterwork Upgrade Assistant

This Python script assists with upgrading Masterwork items in Diablo 4, specifically targeting user-defined affixes with enhanced flexibility and accuracy.

## Features

- User-friendly GUI for configuration and control
- Transparent region selector for easy and accurate scan area selection
- Enhanced flexible matching algorithm for improved affix recognition
- Supports partial word matching and special character handling
- Configurable target phrases and maximum upgrade count

## Installation Instructions

1. Download the latest release of D4Assistant.exe from the releases page

2. Install Tesseract OCR:
   - Download and install Tesseract OCR v5.3.1 from [GitHub](https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.1.20230401/tesseract-ocr-w64-setup-5.3.1.20230401.exe)
   - Install to the default location (C:\Program Files\Tesseract-OCR)
   - Important: The application requires Tesseract OCR to be installed in the default location

3. Run D4Assistant.exe

## Usage

1. Use the GUI to set up button positions and the scan region:
   - Click "Get" next to each button to set its position
   - For the scan region, click "Get" and then use the transparent overlay to click and drag the desired scan area
2. Enter the target phrase (affix) and maximum count
3. Save the configuration
4. Start the process

## Important Notes

- The 'P' key serves as a kill switch to stop the process. You can also use the "Stop Process" button in the GUI.
- A wider scan area may increase the likelihood of false positives. It's recommended to keep the scan region focused.
- The configuration is saved in `upgrade_config.json` and will be loaded automatically on subsequent runs.
- This script is designed to work with any affix or combination of affixes. Adjust the target phrase as needed.
- Longer, more specific target phrases are recommended to reduce false positives.
- The script's performance may vary depending on your system and game settings.

## Configuration

The `upgrade_config.json` file contains the coordinates for various buttons, the scan region, target phrase, and max count. The configuration can be set and saved through the GUI.

## Flexible Matching Algorithm

The matching algorithm offers:
- Case-insensitive matching
- Space normalization
- Partial word matching (minimum 3 characters)
- Special character preservation
- Flexible word order matching
- All-word matching requirement

This allows for more robust recognition of affixes, even with OCR imperfections or variations in text formatting.
