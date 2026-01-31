# Quick Start Guide

## Installation

1. Install Python 3.8 or higher

2. Install dependencies:
```bash
cd bambu-filament-tool
pip install -r requirements.txt
```

## Running the Tool

```bash
python src/main.py
```

## Using the Application

1. **Enter Filament Information:**
   - Manufacturer: Brand name (e.g., "Overture", "Polymaker", "eSun")
   - Material Type: Select from PLA, PETG, ABS, or TPU
   - Material Name: Specific product name (e.g., "Matte PLA", "PolyTerra")
   - Color: Optional color specification

2. **Generate Profile:**
   - Click [GENERATE PROFILE] button
   - The tool will:
     - Search for filament data (currently uses defaults)
     - Generate unique IDs for Bambu Studio
     - Create a complete profile based on material type

3. **Save Profile:**
   - Click [SAVE PROFILE] button
   - Choose save location:
     - Default: `%APPDATA%\BambuStudio\user\filament`
     - Or any custom location

4. **Import to Bambu Studio:**
   - Copy the saved .json file to:
     - Windows: `C:\Users\<YourName>\AppData\Roaming\BambuStudio\user\<DeviceID>\filament`
   - Restart Bambu Studio
   - The profile should appear in the filament list

## Example Usage

**Creating an Overture PLA Profile:**

1. Manufacturer: `Overture`
2. Material Type: `PLA`
3. Material Name: `Matte PLA Pro`
4. Color: `Black` (optional)
5. Click [GENERATE PROFILE]
6. Click [SAVE PROFILE]
7. Save to Bambu Studio filament directory

## Configuration

Edit `config/settings.json` to customize:
- Web scraper settings
- Default output paths
- Material type mappings
- Cache behavior

## Current Limitations

This is an initial version with:
- **Manual data entry focus:** Web scraping not fully implemented yet
- **Template-based generation:** Uses base templates for each material type
- **Common materials only:** PLA, PETG, ABS, TPU supported

## Future Enhancements

- Full web scraping from 3dfilamentprofiles.com
- Bambu Lab Wiki integration
- Community profile database
- Advanced parameter tuning
- Multi-material support

## Troubleshooting

**Profile doesn't appear in Bambu Studio:**
- Ensure the file is in the correct directory
- Check the JSON is valid
- Restart Bambu Studio
- Check that `instantiation` is set to `"true"`

**Generation fails:**
- Check all required fields are filled
- Verify material type is supported
- Check logs in `logs/` directory

## Need Help?

Check the logs in the `logs/` directory for detailed error information.
