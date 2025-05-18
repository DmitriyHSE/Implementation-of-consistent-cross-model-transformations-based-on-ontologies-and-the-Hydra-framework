# Auto-generated compatibility layer
from typing import Dict, Any, Union
from dataclasses import asdict
import semver

class OntologyAdapter:
    """Handle version migrations between ontology versions"""
    CURRENT_VERSION = "2.0.0"
    MIGRATION_RULES = {"added_fields": {}, "class_changes": {}, "default_values": {}, "field_renames": {}, "removed_fields": {}, "type_changes": {}}

    @classmethod
    def migrate(cls, old_data: Dict[str, Any], old_version: str) -> Dict[str, Any]:
        if old_version == cls.CURRENT_VERSION:
            return old_data

        migrated = old_data.copy()

        # Apply field renames
        for old_field, new_field in cls.MIGRATION_RULES.get('field_renames', {}).items():
            for entity_type, entity_data in migrated.items():
                if old_field in entity_data:
                    entity_data[new_field] = entity_data.pop(old_field)

        # Set defaults for new fields
        for entity_type, entity_data in migrated.items():
            for new_field, field_info in cls.MIGRATION_RULES.get('added_fields', {}).items():
                entity_data.setdefault(new_field, field_info['default'])

        # Handle type conversions
        for field, type_change in cls.MIGRATION_RULES.get('type_changes', {}).items():
            for entity_type, entity_data in migrated.items():
                if field in entity_data:
                    try:
                        if type_change['old'] == 'int' and type_change['new'] == 'float':
                            entity_data[field] = float(entity_data[field])
                        elif type_change['old'] == 'str' and type_change['new'] == 'int':
                            entity_data[field] = int(entity_data[field])
                        elif type_change['old'] == 'float' and type_change['new'] == 'int':
                            entity_data[field] = int(entity_data[field])
                    except (ValueError, TypeError):
                        entity_data[field] = cls.MIGRATION_RULES['added_fields'].get(field, {}).get('default')

        return migrated

    @staticmethod
    def to_dict(obj) -> Dict[str, Any]:
        return asdict(obj)

    @staticmethod
    def from_dict(data: Dict[str, Any], target_class):
        return target_class(**data)