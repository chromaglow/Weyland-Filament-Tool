"""
Data models for filament profiles and settings
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class MaterialSettings:
    """Material-specific print settings"""

    # Temperature settings
    nozzle_temperature: Optional[int] = None
    nozzle_temperature_initial_layer: Optional[int] = None
    bed_temperature: Optional[int] = None
    cool_plate_temp: Optional[int] = None
    eng_plate_temp: Optional[int] = None
    hot_plate_temp: Optional[int] = None
    textured_plate_temp: Optional[int] = None

    # Flow and speed settings
    filament_flow_ratio: Optional[float] = None
    filament_max_volumetric_speed: Optional[int] = None
    filament_shrink: Optional[str] = None

    # Pressure advance
    enable_pressure_advance: Optional[str] = None
    pressure_advance: Optional[float] = None

    # Retraction settings
    filament_retraction_length: Optional[List[float]] = None
    filament_retraction_speed: Optional[List[int]] = None
    filament_deretraction_speed: Optional[List[int]] = None

    # Cooling settings
    fan_cooling_layer_time: Optional[int] = None
    filament_cooling_moves: Optional[int] = None
    filament_cooling_initial_speed: Optional[int] = None
    filament_cooling_final_speed: Optional[int] = None

    # Compatibility
    compatible_printers: Optional[List[str]] = None

    # Additional properties
    additional_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = {}

        for key, value in self.__dict__.items():
            if key == 'additional_settings':
                result.update(value)
            elif value is not None:
                # Convert lists to JSON array format if needed
                if isinstance(value, list):
                    result[key] = [str(v) for v in value]
                else:
                    result[key] = str(value) if not isinstance(value, (int, float, bool)) else value

        return result


@dataclass
class FilamentProfile:
    """Complete filament profile for Bambu Studio"""

    # Required fields
    name: str
    material_type: str  # PLA, PETG, ABS, TPU, etc.
    manufacturer: Optional[str] = None

    # Bambu Studio specific fields
    from_source: str = "User"
    inherits: Optional[str] = None
    version: str = "1.6.0.2"
    filament_settings_id: Optional[List[str]] = None
    filament_id: Optional[str] = None
    setting_id: Optional[str] = None
    instantiation: str = "true"

    # Material settings
    settings: MaterialSettings = field(default_factory=MaterialSettings)

    # Metadata
    color: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    source_urls: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Initialize computed fields"""
        if self.filament_settings_id is None:
            self.filament_settings_id = [self.name]

        if self.inherits is None:
            self.inherits = f"Generic {self.material_type}"

    def to_bambu_json(self) -> Dict[str, Any]:
        """
        Convert to Bambu Studio JSON format
        """
        result = {
            "name": self.name,
            "from": self.from_source,
            "inherits": self.inherits,
            "version": self.version,
            "filament_settings_id": self.filament_settings_id,
        }

        # Add optional Bambu fields
        if self.filament_id:
            result["filament_id"] = self.filament_id
        if self.setting_id:
            result["setting_id"] = self.setting_id
        if self.instantiation:
            result["instantiation"] = self.instantiation

        # Merge material settings
        result.update(self.settings.to_dict())

        return result

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate the profile for completeness
        Returns: (is_valid, list_of_errors)
        """
        errors = []

        if not self.name:
            errors.append("Profile name is required")

        if not self.material_type:
            errors.append("Material type is required")

        if not self.inherits:
            errors.append("Base profile (inherits) is required")

        # Check temperature settings
        if self.settings.nozzle_temperature is None:
            errors.append("Nozzle temperature is required")

        if self.settings.bed_temperature is None:
            errors.append("Bed temperature is required")

        return (len(errors) == 0, errors)


@dataclass
class ScrapedData:
    """Raw data scraped from web sources"""

    source: str  # Name of the source (e.g., "3dfilamentprofiles.com")
    url: str
    manufacturer: Optional[str] = None
    material_type: Optional[str] = None
    material_name: Optional[str] = None
    color: Optional[str] = None

    # Extracted settings
    temperatures: Dict[str, int] = field(default_factory=dict)
    speeds: Dict[str, int] = field(default_factory=dict)
    flow_settings: Dict[str, float] = field(default_factory=dict)
    other_settings: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0  # 0-1 scale of data reliability

    def to_material_settings(self) -> MaterialSettings:
        """Convert scraped data to MaterialSettings"""
        settings = MaterialSettings()

        # Map temperatures
        if "nozzle" in self.temperatures:
            settings.nozzle_temperature = self.temperatures["nozzle"]
        if "nozzle_first_layer" in self.temperatures:
            settings.nozzle_temperature_initial_layer = self.temperatures["nozzle_first_layer"]
        if "bed" in self.temperatures:
            settings.bed_temperature = self.temperatures["bed"]

        # Map flow settings
        if "flow_ratio" in self.flow_settings:
            settings.filament_flow_ratio = self.flow_settings["flow_ratio"]
        if "max_volumetric_speed" in self.speeds:
            settings.filament_max_volumetric_speed = self.speeds["max_volumetric_speed"]

        # Map other settings
        settings.additional_settings = self.other_settings.copy()

        return settings
