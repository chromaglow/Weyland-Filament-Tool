"""
Profile comparison and conflict resolution
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
from src.data.models import ScrapedData
from src.utils.logger import get_logger

logger = get_logger()


@dataclass
class SettingConflict:
    """Represents a conflict between multiple settings"""
    setting_name: str
    values: List[Tuple[Any, str, float]]  # (value, source, confidence)
    recommended_value: Any
    reason: str


@dataclass
class ComparisonResult:
    """Results of comparing multiple scraped profiles"""
    merged_data: ScrapedData
    conflicts: List[SettingConflict] = field(default_factory=list)
    sources_count: int = 0
    avg_confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProfileComparator:
    """Compare and merge multiple filament profiles"""

    def __init__(self):
        """Initialize comparator"""
        self.logger = get_logger()

    def compare_profiles(self, profiles: List[ScrapedData]) -> ComparisonResult:
        """
        Compare multiple profiles and intelligently merge them

        Args:
            profiles: List of ScrapedData from different sources

        Returns:
            ComparisonResult with merged data and conflicts
        """
        if not profiles:
            raise ValueError("No profiles to compare")

        if len(profiles) == 1:
            # Only one profile, no conflicts
            return ComparisonResult(
                merged_data=profiles[0],
                sources_count=1,
                avg_confidence=profiles[0].confidence,
                metadata={"single_source": True}
            )

        logger.info(f"Comparing {len(profiles)} profiles")

        # Initialize result
        result = ComparisonResult(
            merged_data=self._create_base_profile(profiles),
            sources_count=len(profiles),
            avg_confidence=sum(p.confidence for p in profiles) / len(profiles)
        )

        # Compare temperatures
        self._compare_temperatures(profiles, result)

        # Compare speeds
        self._compare_speeds(profiles, result)

        # Compare flow settings
        self._compare_flow_settings(profiles, result)

        # Add metadata
        result.metadata['sources'] = [p.source for p in profiles]
        result.metadata['urls'] = [p.url for p in profiles]
        result.metadata['newest_date'] = max(p.scraped_at for p in profiles)

        logger.info(f"Comparison complete. Found {len(result.conflicts)} conflicts")
        return result

    def _create_base_profile(self, profiles: List[ScrapedData]) -> ScrapedData:
        """Create a base profile from the highest confidence source"""
        # Use the profile with highest confidence as base
        base = max(profiles, key=lambda p: p.confidence)
        return ScrapedData(
            source="Merged from multiple sources",
            url="",
            manufacturer=base.manufacturer,
            material_type=base.material_type,
            material_name=base.material_name,
            color=base.color,
            confidence=sum(p.confidence for p in profiles) / len(profiles)
        )

    def _compare_temperatures(self, profiles: List[ScrapedData], result: ComparisonResult):
        """Compare temperature settings across profiles"""
        temp_keys = ['nozzle', 'nozzle_first_layer', 'bed']

        for temp_key in temp_keys:
            values = []
            for profile in profiles:
                if temp_key in profile.temperatures:
                    value = profile.temperatures[temp_key]
                    values.append((value, profile.source, profile.confidence))

            if values:
                # Check for conflicts
                unique_values = set(v[0] for v in values)
                if len(unique_values) > 1:
                    # Conflict detected
                    recommended = self._resolve_temperature_conflict(values)
                    conflict = SettingConflict(
                        setting_name=f"{temp_key}_temperature",
                        values=values,
                        recommended_value=recommended,
                        reason=self._get_conflict_reason(values, recommended)
                    )
                    result.conflicts.append(conflict)
                    result.merged_data.temperatures[temp_key] = recommended
                else:
                    # No conflict, use the value
                    result.merged_data.temperatures[temp_key] = values[0][0]

    def _compare_speeds(self, profiles: List[ScrapedData], result: ComparisonResult):
        """Compare speed settings across profiles"""
        for profile in profiles:
            for speed_key, value in profile.speeds.items():
                if speed_key not in result.merged_data.speeds:
                    result.merged_data.speeds[speed_key] = value

    def _compare_flow_settings(self, profiles: List[ScrapedData], result: ComparisonResult):
        """Compare flow settings across profiles"""
        flow_values = []
        for profile in profiles:
            if 'flow_ratio' in profile.flow_settings:
                value = profile.flow_settings['flow_ratio']
                flow_values.append((value, profile.source, profile.confidence))

        if flow_values:
            unique_values = set(v[0] for v in flow_values)
            if len(unique_values) > 1:
                # Conflict
                recommended = self._resolve_flow_conflict(flow_values)
                conflict = SettingConflict(
                    setting_name="flow_ratio",
                    values=flow_values,
                    recommended_value=recommended,
                    reason=self._get_conflict_reason(flow_values, recommended)
                )
                result.conflicts.append(conflict)
                result.merged_data.flow_settings['flow_ratio'] = recommended
            else:
                result.merged_data.flow_settings['flow_ratio'] = flow_values[0][0]

    def _resolve_temperature_conflict(self, values: List[Tuple[int, str, float]]) -> int:
        """
        Resolve temperature conflicts using weighted average

        Args:
            values: List of (temperature, source, confidence) tuples

        Returns:
            Recommended temperature
        """
        # Weighted average based on confidence
        total_weight = sum(conf for _, _, conf in values)
        weighted_sum = sum(temp * conf for temp, _, conf in values)

        if total_weight > 0:
            recommended = int(weighted_sum / total_weight)
        else:
            # Fallback to simple average
            recommended = int(sum(v[0] for v in values) / len(values))

        logger.debug(f"Temperature conflict resolved to: {recommended}°C")
        return recommended

    def _resolve_flow_conflict(self, values: List[Tuple[float, str, float]]) -> float:
        """
        Resolve flow ratio conflicts using weighted average

        Args:
            values: List of (flow_ratio, source, confidence) tuples

        Returns:
            Recommended flow ratio
        """
        # Weighted average based on confidence
        total_weight = sum(conf for _, _, conf in values)
        weighted_sum = sum(flow * conf for flow, _, conf in values)

        if total_weight > 0:
            recommended = round(weighted_sum / total_weight, 4)
        else:
            recommended = round(sum(v[0] for v in values) / len(values), 4)

        logger.debug(f"Flow ratio conflict resolved to: {recommended}")
        return recommended

    def _get_conflict_reason(
        self,
        values: List[Tuple[Any, str, float]],
        recommended: Any
    ) -> str:
        """
        Generate explanation for conflict resolution

        Args:
            values: List of conflicting values
            recommended: Recommended value

        Returns:
            Human-readable reason
        """
        value_range = max(v[0] for v in values) - min(v[0] for v in values)
        sources = [v[1] for v in values]

        reason = f"Found {len(values)} different values from {len(set(sources))} sources. "
        reason += f"Range: {min(v[0] for v in values)} - {max(v[0] for v in values)}. "
        reason += f"Recommended {recommended} using weighted average based on source confidence."

        return reason

    def format_conflicts_for_display(self, result: ComparisonResult) -> str:
        """
        Format conflicts as human-readable text

        Args:
            result: ComparisonResult with conflicts

        Returns:
            Formatted string
        """
        if not result.conflicts:
            return "No conflicts found. All sources agree!"

        output = f"Found {len(result.conflicts)} conflict(s):\n\n"

        for i, conflict in enumerate(result.conflicts, 1):
            output += f"{i}. {conflict.setting_name}:\n"
            output += f"   Recommended: {conflict.recommended_value}\n"
            output += f"   Reason: {conflict.reason}\n"
            output += f"   Values from sources:\n"
            for value, source, confidence in conflict.values:
                output += f"     - {value} from {source} (confidence: {confidence:.1%})\n"
            output += "\n"

        return output
