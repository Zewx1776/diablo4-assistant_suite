# Diablo 4 Assistant Tools

A collection of automation tools to assist with various Diablo 4 tasks.

## Features

- Kurast Helper: Automates portal detection and tribute interactions (wip for opening undercity portal and placing tribute)
- Barter Assistant: Helps with restocking items at vendors
- Enchant Helper: Assists with enchanting items
- Masterwork Assistant: Helps with upgrading Masterwork items

## Installation Instructions

1. Download the latest release of D4Assistant.exe from the releases page

2. Install Tesseract OCR:
   - Download and install Tesseract OCR v5.3.1 from [GitHub](https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.1.20230401/tesseract-ocr-w64-setup-5.3.1.20230401.exe)
   - Install to the default location (C:\Program Files\Tesseract-OCR)
   - Important: The application requires Tesseract OCR to be installed in the default location

3. Run D4Assistant.exe

## Tool-Specific Instructions

### Kurast Helper
1. Set the portal scan region using the "Get" button
2. Capture a reference image of the portal you want to detect
3. Set the tribute spot location (where to right-click)
4. Set the portal button location
5. Adjust confidence and delay settings as needed
6. Save configuration and start the process

### Barter Assistant
1. Set the restock button location
2. Configure up to 8 scan regions for item detection
3. Enter target words (comma-separated) to look for in items
4. Save configuration and start the process
5. The tool will automatically restock items matching the target words

### Enchant Helper
1. Set button locations:
   - Enchant button
   - Replace button
   - Close button
2. Configure scan regions and corresponding buttons
3. Enter target affixes (comma-separated)
4. Adjust timing delays:
   - Click delay
   - Enchant delay
   - Replace delay
   - Loop delay
5. Save configuration and start the process

### Masterwork Assistant
1. Configure button positions:
   - Upgrade button
   - Skip button
   - Close button
   - Reset button
   - Confirm button
2. Set the scan region for affix detection
3. Enter target affix and maximum upgrade count
4. Save configuration and start the process

## Important Notes

- The 'P' key serves as a universal kill switch to stop any running process
- All tools can be configured and controlled through their respective GUIs
- Configurations are saved automatically and will be loaded on subsequent runs
- Each tool has its own configuration file for independent settings
- The launcher allows you to switch between tools and customize the theme
- Wider scan regions may increase false positives; keep regions focused
- Performance may vary depending on system specifications and game settings

## Configuration Files

- `kurast_config.json`: Kurast Helper settings
- `restock_config.json`: Barter Assistant settings
- `enchant_config.json`: Enchant Helper settings
- `upgrade_config.json`: Masterwork Assistant settings
- `theme_config.json`: UI theme preferences

## Safety and Usage

- Test configurations with caution to ensure desired behavior
- Use appropriate delays to prevent game client issues
- Keep scan regions as specific as possible
- Monitor the process output window for status updates
- Use the stop button or 'P' key if the tool needs to be stopped immediately
