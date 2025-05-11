# Auto-generated compatibility layer
from typing import Dict, Any
from dataclasses import asdict
import semver

class OntologyAdapter:
    """Handle version migrations between ontology versions"""
    CURRENT_VERSION = "1.0.0"
    MIGRATION_RULES = {'field_renames': {}}

    @classmethod
    def migrate(cls, old_data: Dict[str, Any], old_version: str) -> Dict[str, Any]:
        if old_version == cls.CURRENT_VERSION:
            return old_data

        try:
            migrated = old_data.copy()
            # Apply field renames
            for old_field, new_field in cls.MIGRATION_RULES.get('field_renames', {}).items():
                if old_field in migrated.get('University', {}):
                    migrated['University'][new_field] = migrated['University'].pop(old_field)

            # Set defaults for new fields
            if 'University' in migrated:
                migrated['University'].setdefault('name', "")
                

            return migrated
        except Exception as e:
            raise ValueError(f"Migration failed: {str(e)}")

    @staticmethod
    def to_dict(obj) -> Dict[str, Any]:
        return asdict(obj)

    @staticmethod
    def from_dict(data: Dict[str, Any], target_class):
        return target_class(**data)