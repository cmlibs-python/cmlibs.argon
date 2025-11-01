"""
   Copyright 2016 University of Auckland

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import copy
import hashlib
import json

from cmlibs.zinc import __version__ as zinc_version
from cmlibs.zinc.status import OK as ZINC_OK
from cmlibs.argon.argonerror import ArgonError


DEFAULT_ZINC_VERSION = '4.2.1'


def _get_strings_hash(text):
    """Calculates the SHA-256 hash for the entire text block."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _get_item_hashes(materials_list):
    """
    Calculates the canonical hash for each individual item.
    Uses 'Name' as the unique key.
    Returns a dictionary {material_name: hash}
    """
    hashes = {}
    for item in materials_list:
        # Use 'Name' as the unique identifier
        item_name = item.get('Name')
        if not item_name:
            continue

        # Create a canonical (sorted) string representation for hashing
        # This ensures {'a': 1, 'b': 2} hashes the same as {'b': 2, 'a': 1}
        canonical_string = json.dumps(item, sort_keys=True)
        hashes[item_name] = _get_strings_hash(canonical_string)
    return hashes


BASE_MATERIALS_OBJECT = {
    'DefaultMaterial': 'default',
    'DefaultSelectedMaterial': 'default_selected',
    'Materials': [
        {'Alpha': 1, 'Ambient': [0, 0, 0], 'Diffuse': [0, 0, 0], 'Emission': [0, 0, 0], 'Name': 'black',
         'Shininess': 0.2, 'Specular': [0.3, 0.3, 0.3]},
        {'Alpha': 1, 'Ambient': [0, 0, 1], 'Diffuse': [0, 0, 1], 'Emission': [0, 0, 0], 'Name': 'blue',
         'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [0.7, 0.7, 0.6], 'Diffuse': [0.9, 0.9, 0.7], 'Emission': [0, 0, 0],
         'Name': 'bone', 'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [0.5, 0.25, 0], 'Diffuse': [0.5, 0.25, 0], 'Emission': [0, 0, 0],
         'Name': 'brown', 'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [0, 1, 1], 'Diffuse': [0, 1, 1], 'Emission': [0, 0, 0], 'Name': 'cyan',
         'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [1, 1, 1], 'Diffuse': [1, 1, 1], 'Emission': [0, 0, 0], 'Name': 'default',
         'Shininess': 0, 'Specular': [0, 0, 0]},
        {'Alpha': 1, 'Ambient': [1, 0.2, 0], 'Diffuse': [1, 0.2, 0], 'Emission': [0, 0, 0],
         'Name': 'default_selected', 'Shininess': 0, 'Specular': [0, 0, 0]},
        {'Alpha': 1, 'Ambient': [1, 0.4, 0], 'Diffuse': [1, 0.7, 0], 'Emission': [0, 0, 0], 'Name': 'gold',
         'Shininess': 0.3, 'Specular': [0.5, 0.5, 0.5]},
        {'Alpha': 1, 'Ambient': [0, 1, 0], 'Diffuse': [0, 1, 0], 'Emission': [0, 0, 0], 'Name': 'green',
         'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [0.25, 0.25, 0.25], 'Diffuse': [0.25, 0.25, 0.25], 'Emission': [0, 0, 0],
         'Name': 'grey25', 'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [0.5, 0.5, 0.5], 'Diffuse': [0.5, 0.5, 0.5], 'Emission': [0, 0, 0],
         'Name': 'grey50', 'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [0.75, 0.75, 0.75], 'Diffuse': [0.75, 0.75, 0.75], 'Emission': [0, 0, 0],
         'Name': 'grey75', 'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [1, 0, 1], 'Diffuse': [1, 0, 1], 'Emission': [0, 0, 0], 'Name': 'magenta',
         'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [0.4, 0.14, 0.11], 'Diffuse': [0.5, 0.12, 0.1], 'Emission': [0, 0, 0],
         'Name': 'muscle', 'Shininess': 0.2, 'Specular': [0.3, 0.5, 0.5]},
        {'Alpha': 1, 'Ambient': [1, 0.5, 0], 'Diffuse': [1, 0.5, 0], 'Emission': [0, 0, 0], 'Name': 'orange',
         'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [1, 0, 0], 'Diffuse': [1, 0, 0], 'Emission': [0, 0, 0], 'Name': 'red',
         'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]},
        {'Alpha': 1, 'Ambient': [0.4, 0.4, 0.4], 'Diffuse': [0.7, 0.7, 0.7], 'Emission': [0, 0, 0],
         'Name': 'silver', 'Shininess': 0.3, 'Specular': [0.5, 0.5, 0.5]},
        {'Alpha': 1, 'Ambient': [0.9, 0.7, 0.5], 'Diffuse': [0.9, 0.7, 0.5], 'Emission': [0, 0, 0],
         'Name': 'tissue', 'Shininess': 0.2000000029802322, 'Specular': [0.2, 0.2, 0.3]},
        {'Alpha': 1, 'Ambient': [1, 1, 1], 'Diffuse': [1, 1, 1], 'Emission': [0, 0, 0], 'Name': 'white',
         'Shininess': 0, 'Specular': [0, 0, 0]},
        {'Alpha': 1, 'Ambient': [1, 1, 0], 'Diffuse': [1, 1, 0], 'Emission': [0, 0, 0], 'Name': 'yellow',
         'Shininess': 0.2, 'Specular': [0.1, 0.1, 0.1]}
    ]
}

KNOWN_MATERIAL_DATABASE = {
    '4.2.1': {'base': BASE_MATERIALS_OBJECT, 'changes': []}
}


def _apply_changes(base_object, change_stack):
    """
    Applies a stack of change objects to a base material object.

    :param base_object: The starting state (e.g., BASE_MATERIALS_OBJECT).
    :param change_stack: A list of change objects to apply in order.
    :return: A new dictionary representing the final state.
    """
    # 1. Start with a deep copy of the base state.
    #    This is crucial so we don't modify the original constant.

    final_state = copy.deepcopy(base_object)

    # 2. Convert the list of materials into a map (dictionary)
    #    for efficient O(1) lookups, updates, and deletions.
    material_map = {mat['Name']: mat for mat in final_state['Materials']}

    # 3. Iterate through each change in the stack and apply it
    for i, change in enumerate(change_stack):
        # Handle Additions: Add new items to the map
        for material_to_add in change.get('added', []):
            name = material_to_add.get('Name')
            if name:
                material_map[name] = material_to_add

        # Handle Changes: Overwrite existing items in the map
        for material_to_change in change.get('changed', []):
            name = material_to_change.get('Name')
            if name:
                material_map[name] = material_to_change

        # Handle Deletions: Remove items from the map
        for material_to_delete in change.get('deleted', []):
            name = material_to_delete.get('Name')
            if name and name in material_map:
                del material_map[name]
            elif name:
                raise ArgonError(f"Could not delete '{name}', not found.")

        # Handle Top-Level Changes (e.g., DefaultMaterial)
        # We assume if top_level_changed is True, the new values
        # are also present in the change object.
        if change.get('top_level_changed', False):
            if 'DefaultMaterial' in change:
                new_default = change['DefaultMaterial']
                final_state['DefaultMaterial'] = new_default
            if 'DefaultSelectedMaterial' in change:
                new_selected = change['DefaultSelectedMaterial']
                final_state['DefaultSelectedMaterial'] = new_selected

    # 4. After all changes, convert the map's values back to a list
    final_state['Materials'] = list(material_map.values())

    return final_state

def _determine_material_changes(base, new_materials_json_string):
    """
    Checks for changes using the hybrid hash method.
    Returns a dictionary detailing the changes.
    """
    base_full_data = copy.deepcopy(base)

    # Stores {material_name: hash} for granular checking.
    base_item_hashes = _get_item_hashes(base_full_data['Materials'])

    # Granular check: Hashes don't match, so parse and investigate.
    try:
        new_data_dict = json.loads(new_materials_json_string)
        new_materials_list = new_data_dict.get('Materials', [])
    except json.JSONDecodeError as e:
        return {"status": "error", "message": str(e)}

    new_item_hashes = _get_item_hashes(new_materials_list)

    # Find differences
    new_names = set(new_item_hashes.keys())
    old_names = set(base_item_hashes.keys())

    # Find items whose 'Name' exists in both but hash is different
    changed = [name for name in (new_names & old_names)
               if new_item_hashes[name] != base_item_hashes[name]]

    # Find items with 'Name' in new set but not old
    added = list(new_names - old_names)

    # Find items with 'Name' in old set but not new
    deleted = list(old_names - new_names)

    # Check for changes in top-level keys (e.g., 'DefaultMaterial')
    top_level_changed = False
    if base_full_data:
        if (base_full_data.get('DefaultMaterial') != new_data_dict.get('DefaultMaterial') or
                base_full_data.get('DefaultSelectedMaterial') != new_data_dict.get(
                    'DefaultSelectedMaterial')):
            top_level_changed = True

    if not changed and not added and not deleted and not top_level_changed:
        # No data changes found.
        # This means the *only* change was JSON formatting (e.g., whitespace, key order).
        # We will report this as no data change.
        return {"status": "no_change", "added": [], "changed": [], "deleted": [],
                "top_level_changed": False}

    # Genuine data changes were found.
    material_map = {material['Name']: material for material in new_data_dict['Materials']}
    # Sorted for consistent test results.
    added_materials = [material_map.get(m) for m in sorted(added)]
    changed_materials = [material_map.get(m) for m in sorted(changed)]
    deleted_materials = [{'Name': m} for m in sorted(deleted)]

    return {
        "status": "changes_detected",
        "added": added_materials,
        "changed": changed_materials,
        "deleted": deleted_materials,
        "top_level_changed": top_level_changed
    }


class ArgonMaterials:
    """
    Manages and serializes Zinc Materials.
    """

    def __init__(self, zinc_context):
        self._zinc_context = zinc_context
        self._materials_module = zinc_context.getMaterialmodule()

    def getZincContext(self):
        """
        Returns the underlying Zinc context for the Argon Material.

        :return: cmlibs.zinc.context.Context
        """
        return self._zinc_context

    def deserialize(self, dict_input):
        """
        Read the JSON description to the argon Material object. This will change the materials in the material module.

        :param dict_input: The string containing JSON description.
        """
        dict_id = dict_input.get('id')
        if dict_id is None:
            materials_description = json.dumps(dict_input)
        elif dict_id == 'nz.ac.abi.argon_document.materials':
            version_materials = KNOWN_MATERIAL_DATABASE.get(dict_input['zinc_version'])
            if version_materials is None:
                raise ArgonError('Could not find matching materials in database for zinc version: {}'.format(dict_input['zinc_version']))

            version_materials = _apply_changes(version_materials['base'], version_materials['changes'])
            materials_dict = _apply_changes(version_materials, dict_input['changes'])
            materials_description = json.dumps(materials_dict)
        else:
            raise ArgonError('Unknown Argon document materials ID')

        result = self._materials_module.readDescription(materials_description)
        if result != ZINC_OK:
            raise ArgonError("Failed to read materials")

    def serialize(self):
        """
        Write the JSON file describing the materials in the Argon Materials object, which can be used to store the current material settings.

        :return: Python JSON object containing the JSON description of Argon Materials object, otherwise 0.
        """
        materials_description = self._materials_module.writeDescription()
        if zinc_version in KNOWN_MATERIAL_DATABASE:
            db_entry = KNOWN_MATERIAL_DATABASE[zinc_version]
            used_zinc_version = zinc_version
        else:
            db_entry = KNOWN_MATERIAL_DATABASE[DEFAULT_ZINC_VERSION]
            used_zinc_version = DEFAULT_ZINC_VERSION

        effective_base = _apply_changes(db_entry['base'], db_entry['changes'])

        dict_output = {
            'id': 'nz.ac.abi.argon_document.materials',
            'version': '1.0',
            'zinc_version': used_zinc_version,
            'changes': [_determine_material_changes(effective_base, materials_description)]
        }
        # dict_output = json.loads(materials_description)
        return dict_output
