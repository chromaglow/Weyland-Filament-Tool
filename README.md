# 🧬 Bambu Studio Filament Profile Generator

<div align="center">

**Building Better Profiles... One Filament at a Time**

A powerful tool to research 3D printer filament settings and generate complete Bambu Studio-compatible profiles.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/chromaglow/Weyland-Filament-Tool)

</div>

---

## ✨ Features

- 🎯 **Easy Profile Generation** - Simple GUI to create Bambu Studio filament profiles
- 🎨 **DOS-Style Interface** - Retro green-on-black terminal aesthetic
- 🧪 **Template-Based** - Built-in templates for PLA, PETG, ABS, and TPU
- 🔢 **Unique ID Generation** - Automatic filament_id and setting_id creation
- 💾 **Direct Export** - Save profiles ready for Bambu Studio import
- 🔧 **Extensible Architecture** - Ready for web scraping and advanced features

## 🚀 Quick Start

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/chromaglow/Weyland-Filament-Tool.git
cd bambu-filament-tool
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
# Windows
run.bat

# Linux/macOS
python src/main.py
```

## 📖 Usage

1. **Enter Filament Information**
   - Manufacturer (e.g., "Overture", "PolyMaker")
   - Material Type (PLA, PETG, ABS, TPU)
   - Material Name (e.g., "Matte PLA Pro")
   - Color (optional)

2. **Generate Profile**
   - Click `[GENERATE PROFILE]`
   - Review the JSON output

3. **Save and Import**
   - Click `[SAVE PROFILE]`
   - Save to Bambu Studio filament directory:
     - Windows: `%APPDATA%\BambuStudio\user\<DeviceID>\filament`
   - Restart Bambu Studio to see your new profile!

## 📂 Project Structure

```
bambu-filament-tool/
├── src/
│   ├── main.py                 # Application entry point
│   ├── data/
│   │   └── models.py           # Data models
│   ├── generator/
│   │   ├── profile_builder.py  # Profile generation logic
│   │   ├── templates.py        # Template management
│   │   └── id_generator.py     # ID generation
│   ├── scrapers/
│   │   ├── base_scraper.py     # Base scraper class
│   │   └── filament_profiles_scraper.py
│   ├── ui/
│   │   └── main_window.py      # Main GUI
│   └── utils/
│       ├── config.py           # Configuration
│       └── logger.py           # Logging
├── resources/
│   └── templates/              # JSON templates
│       ├── generic_pla.json
│       ├── generic_petg.json
│       ├── generic_abs.json
│       └── generic_tpu.json
├── config/
│   └── settings.json           # Application settings
├── requirements.txt
├── setup.py
└── README.md
```

## 🎯 Supported Materials

| Material | Filament ID | Status |
|----------|-------------|--------|
| PLA | GFL00-GFL99 | ✅ Supported |
| PETG | GFG00-GFG99 | ✅ Supported |
| ABS | GFA00-GFA99 | ✅ Supported |
| TPU | GFU00-GFU99 | ✅ Supported |
| PA (Nylon) | GFN00-GFN99 | 🔜 Coming Soon |
| PC | GFC00-GFC99 | 🔜 Coming Soon |
| ASA | GFS00-GFS99 | 🔜 Coming Soon |

## 🔧 Configuration

Edit `config/settings.json` to customize:

```json
{
  "scraper": {
    "user_agent": "BambuFilamentTool/1.0",
    "rate_limit_delay": 1.0,
    "timeout": 10
  },
  "output": {
    "default_path": "%APPDATA%/BambuStudio/user/filament",
    "format": "json"
  }
}
```

## 📊 Example Output

```json
{
  "name": "Overture PLA Pro Black",
  "from": "User",
  "inherits": "Generic PLA",
  "version": "1.6.0.2",
  "filament_settings_id": ["Overture PLA Pro Black"],
  "filament_id": "GFL00",
  "setting_id": "GFSL00_Overture_01",
  "instantiation": "true",
  "nozzle_temperature": ["220"],
  "hot_plate_temp": ["65"],
  "filament_flow_ratio": ["1.0"],
  "enable_pressure_advance": ["1"]
}
```

## 🌐 Data Sources

- [3D Filament Profiles](https://3dfilamentprofiles.com/) - Community database
- [Bambu Lab Wiki](https://wiki.bambulab.com/) - Official documentation
- Community GitHub repositories

## 🛣️ Roadmap

### Version 0.2.0
- [ ] Full web scraping implementation
- [ ] Manual settings editor
- [ ] Profile validation
- [ ] Database caching

### Version 0.3.0
- [ ] Additional materials (PA, PC, ASA)
- [ ] Multi-material support
- [ ] Community profile sharing
- [ ] OrcaSlicer support

## 🐛 Troubleshooting

**Profile doesn't appear in Bambu Studio?**
- Verify file location is correct
- Check JSON is valid
- Ensure `instantiation` is `"true"`
- Restart Bambu Studio

**Generation fails?**
- Check all required fields are filled
- Verify material type is supported
- Check `logs/` directory for errors

## 📝 Documentation

- [Quick Start Guide](QUICK_START.md)
- [Project Status](PROJECT_STATUS.md)
- [Configuration Guide](config/settings.json)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Bambu Lab for their excellent 3D printers and studio software
- The 3D printing community for sharing filament data
- All contributors and users of this tool

## 📧 Contact

Project Link: [https://github.com/chromaglow/Weyland-Filament-Tool](https://github.com/chromaglow/Weyland-Filament-Tool)

---

<div align="center">

**🏢 Weyland-Yutani Corporation**

*Building Better Worlds... One Profile at a Time*

</div>
