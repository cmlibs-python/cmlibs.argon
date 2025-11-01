import types
import unittest
import json
import copy
import sys

import cmlibs.argon

# Mock cmlibs.zinc classes.
class MockZincStatus:
    OK = 0


class MockZincModule:
    def __init__(self):
        # This stores the JSON string that 'deserialize' passes to Zinc
        self.last_read_description = None
        # This stores the JSON string that 'serialize' will get from Zinc
        self.current_description = ""

    def readDescription(self, json_string):
        self.last_read_description = json_string
        return MockZincStatus.OK

    def writeDescription(self):
        return self.current_description


class MockZincContext:
    def __init__(self):
        self._materials_module = MockZincModule()

    def getMaterialmodule(self):
        return self._materials_module


# --- Mock cmlibs dependencies BEFORE importing the module to test ---

# 1. Mock top-level 'cmlibs' (Namespace Package)
#    This ensures that subsequent 'cmlibs.X' imports work.
mock_cmlibs = types.ModuleType('cmlibs')
mock_cmlibs.__path__ = []  # Declare it as a namespace package
sys.modules['cmlibs'] = mock_cmlibs

# 2. Mock 'cmlibs.zinc' (Fake Package with attributes)
mock_zinc = types.ModuleType('cmlibs.zinc')
mock_zinc.__path__ = []  # Make it a package so it can have submodules
mock_zinc.__version__ = '4.2.1-mock'  # Mock the version import
sys.modules['cmlibs.zinc'] = mock_zinc

# 3. Mock 'cmlibs.zinc.status' (Fake Module)
mock_zinc_status = types.ModuleType('cmlibs.zinc.status')
mock_zinc_status.OK = 0  # Mock the OK status import
sys.modules['cmlibs.zinc.status'] = mock_zinc_status
mock_zinc.status = mock_zinc_status  # Link it to the parent

import cmlibs.argon.argonmaterials as argon_materials

# Now we can alias the real code and mocked values
ArgonMaterials = argon_materials.ArgonMaterials
ArgonError = argon_materials.ArgonError
ZINC_OK = argon_materials.ZINC_OK
BASE_MATERIALS_OBJECT = argon_materials.BASE_MATERIALS_OBJECT
DEFAULT_ZINC_VERSION = argon_materials.DEFAULT_ZINC_VERSION


class TestHelperFunctions(unittest.TestCase):
    """
    Tests the standalone helper functions _apply_changes
    and _determine_material_changes.
    """

    def setUp(self):
        self.base = copy.deepcopy(BASE_MATERIALS_OBJECT)

    def test_determine_no_change(self):
        """
        Test that identical data (even with different formatting)
        results in 'no_change'.
        """
        # Test with compact, unsorted JSON
        new_json_string = json.dumps(self.base)
        changes = argon_materials._determine_material_changes(self.base, new_json_string)
        self.assertEqual(changes["status"], "no_change")
        self.assertEqual(len(changes["added"]), 0)
        self.assertEqual(len(changes["changed"]), 0)

    def test_determine_change_one_material(self):
        """Test that a change in one material is detected."""
        modified = copy.deepcopy(self.base)
        modified['Materials'][1]['Alpha'] = 0.5  # Change 'blue'
        new_json_string = json.dumps(modified)

        changes = argon_materials._determine_material_changes(self.base, new_json_string)

        self.assertEqual(changes["status"], "changes_detected")
        self.assertEqual(len(changes["changed"]), 1)
        self.assertEqual(changes["changed"][0]["Name"], "blue")
        self.assertEqual(changes["changed"][0]["Alpha"], 0.5)

    def test_determine_add_one_material(self):
        """Test that adding a material is detected."""
        modified = copy.deepcopy(self.base)
        purple = {'Alpha': 1, 'Name': 'purple', 'Ambient': [0.5, 0, 0.5]}
        modified['Materials'].append(purple)
        new_json_string = json.dumps(modified)

        changes = argon_materials._determine_material_changes(self.base, new_json_string)

        self.assertEqual(changes["status"], "changes_detected")
        self.assertEqual(len(changes["added"]), 1)
        self.assertEqual(changes["added"][0]["Name"], "purple")

    def test_determine_delete_one_material(self):
        """Test that deleting a material is detected."""
        modified = copy.deepcopy(self.base)
        modified['Materials'].pop(0)  # Delete 'black'
        new_json_string = json.dumps(modified)

        changes = argon_materials._determine_material_changes(self.base, new_json_string)

        self.assertEqual(changes["status"], "changes_detected")
        self.assertEqual(len(changes["deleted"]), 1)
        self.assertEqual(changes["deleted"][0]["Name"], "black")

    def test_determine_top_level_change(self):
        """Test that changing 'DefaultMaterial' is detected."""
        modified = copy.deepcopy(self.base)
        modified['DefaultMaterial'] = 'blue'
        new_json_string = json.dumps(modified)

        changes = argon_materials._determine_material_changes(self.base, new_json_string)

        self.assertEqual(changes["status"], "changes_detected")
        self.assertTrue(changes["top_level_changed"])
        self.assertEqual(len(changes["changed"]), 0)  # No list items changed

    def test_apply_changes(self):
        """Test the _apply_changes logic for reconstructing a state."""
        change_1_obj = copy.deepcopy(self.base['Materials'][1])
        change_1_obj['Alpha'] = 0.5  # Change 'blue'

        change_stack = [
            {
                "status": "changes_detected",
                "changed": [change_1_obj],
                "added": [], "deleted": [], "top_level_changed": False
            },
            {
                "status": "changes_detected",
                "added": [{'Alpha': 1, 'Name': 'purple', 'Ambient': [1, 0, 1]}],
                "changed": [], "deleted": [], "top_level_changed": False
            },
            {
                "status": "changes_detected",
                "deleted": [{'Name': 'bone'}],
                "added": [], "changed": [], "top_level_changed": True,
                "DefaultMaterial": "blue"
            }
        ]

        final_state = argon_materials._apply_changes(self.base, change_stack)

        # Check final state
        self.assertEqual(final_state['DefaultMaterial'], 'blue')
        material_map = {m['Name']: m for m in final_state['Materials']}
        self.assertIn('purple', material_map)
        self.assertNotIn('bone', material_map)
        self.assertEqual(material_map['blue']['Alpha'], 0.5)
        self.assertEqual(len(material_map), 20)  # 20 base + 1 add - 1 del = 20


class TestArgonMaterials(unittest.TestCase):
    """
    Tests the ArgonMaterials class, mocking all Zinc dependencies.
    """

    def setUp(self):
        # Create fresh mocks for each test
        self.mock_context = MockZincContext()
        self.mock_materials_module = self.mock_context.getMaterialmodule()

        # Instantiate the class under test
        self.argon_materials = ArgonMaterials(self.mock_context)

        # Save and reset the module's state for predictable tests
        self.original_db = copy.deepcopy(argon_materials.KNOWN_MATERIAL_DATABASE)
        self.original_zinc_version = argon_materials.zinc_version

        # Force a known state
        argon_materials.zinc_version = '4.2.1'
        argon_materials.KNOWN_MATERIAL_DATABASE = {
            '4.2.1': {'base': BASE_MATERIALS_OBJECT, 'changes': []}
        }

    def tearDown(self):
        # Restore the module's original state
        argon_materials.KNOWN_MATERIAL_DATABASE = self.original_db
        argon_materials.zinc_version = self.original_zinc_version

    def test_serialize_no_change(self):
        """
        Test serialize() when the Zinc module's state
        is identical to the known '4.2.1' base.
        """
        # Set what self._materials_module.writeDescription() will return
        self.mock_materials_module.current_description = json.dumps(BASE_MATERIALS_OBJECT)

        result = self.argon_materials.serialize()

        self.assertEqual(result['id'], 'nz.ac.abi.argon_document.materials')
        self.assertEqual(result['zinc_version'], '4.2.1')

        change_list = result['changes']
        self.assertEqual(len(change_list), 1)
        self.assertEqual(change_list[0]['status'], 'no_change')

    def test_serialize_with_changes(self):
        """
        Test serialize() when the Zinc module has one change
        compared to the base.
        """
        modified = copy.deepcopy(BASE_MATERIALS_OBJECT)
        modified['Materials'][1]['Alpha'] = 0.5  # Change 'blue'
        self.mock_materials_module.current_description = json.dumps(modified)

        result = self.argon_materials.serialize()

        change_list = result['changes']
        self.assertEqual(change_list[0]['status'], 'changes_detected')
        self.assertEqual(len(change_list[0]['changed']), 1)
        self.assertEqual(change_list[0]['changed'][0]['Name'], 'blue')

    def test_serialize_uses_fallback_version(self):
        """
        Test that serialize() falls back to DEFAULT_ZINC_VERSION
        if the current zinc_version is not in the database.
        """
        argon_materials.zinc_version = 'unknown.version.xyz'

        # Set the mock to return the default base, so 'no_change' is expected
        self.mock_materials_module.current_description = json.dumps(BASE_MATERIALS_OBJECT)

        result = self.argon_materials.serialize()

        # It should have used the DEFAULT_ZINC_VERSION
        self.assertEqual(result['zinc_version'], DEFAULT_ZINC_VERSION)
        self.assertEqual(result['changes'][0]['status'], 'no_change')

    def test_serialize_with_db_changes(self):
        """
        Test that serialize() compares against an 'effective base'
        if the database itself has changes.
        """
        # Add a change to the database for version 4.2.1
        db_change_obj = copy.deepcopy(BASE_MATERIALS_OBJECT['Materials'][0])
        db_change_obj['Alpha'] = 0.1  # Change 'black'
        db_change = {
            'status': 'changes_detected',
            'changed': [db_change_obj],
            'added': [], 'deleted': [], 'top_level_changed': False
        }
        argon_materials.KNOWN_MATERIAL_DATABASE['4.2.1']['changes'] = [db_change]

        # Now, if the current materials *have* this change,
        # it should be reported as 'no_change'.
        current_state = copy.deepcopy(BASE_MATERIALS_OBJECT)
        current_state['Materials'][0]['Alpha'] = 0.1  # Match the DB change
        self.mock_materials_module.current_description = json.dumps(current_state)

        result = self.argon_materials.serialize()
        self.assertEqual(result['changes'][0]['status'], 'no_change')

    def test_deserialize_legacy_format(self):
        """
        Test deserialize() with a raw dict (no 'id' field).
        It should just dump and read the whole thing.
        """
        legacy_dict = {
            'DefaultMaterial': 'blue',
            'Materials': [BASE_MATERIALS_OBJECT['Materials'][0]]
        }

        self.argon_materials.deserialize(legacy_dict)

        # Check what was passed to Zinc's readDescription
        expected_json = json.dumps(legacy_dict)
        self.assertEqual(self.mock_materials_module.last_read_description, expected_json)

    def test_deserialize_new_format(self):
        """
        Test deserialize() with the new 'base + changes' format.
        """
        # A doc that adds 'purple'
        doc_change = {
            'status': 'changes_detected',
            'added': [{'Alpha': 1, 'Name': 'purple', 'Ambient': [1, 0, 1]}],
            'changed': [], 'deleted': [], 'top_level_changed': False
        }
        doc = {
            'id': 'nz.ac.abi.argon_document.materials',
            'zinc_version': '4.2.1',
            'changes': [doc_change]
        }

        self.argon_materials.deserialize(doc)

        # Check that the final JSON passed to Zinc has 'purple'
        final_state = json.loads(self.mock_materials_module.last_read_description)
        material_names = [m['Name'] for m in final_state['Materials']]
        self.assertIn('purple', material_names)
        self.assertEqual(len(material_names), 21)  # 20 base + 1 new
        self.assertEqual(final_state['DefaultMaterial'], 'default')

    def test_deserialize_unknown_id(self):
        """Test that an unknown 'id' raises an ArgonError."""
        doc = {'id': 'unknown.id.string'}
        with self.assertRaises(ArgonError):
            self.argon_materials.deserialize(doc)

    def test_deserialize_unknown_zinc_version(self):
        """Test that an unknown 'zinc_version' raises an ArgonError."""
        doc = {
            'id': 'nz.ac.abi.argon_document.materials',
            'zinc_version': 'not.a.real.version',
            'changes': []
        }
        with self.assertRaises(ArgonError):
            self.argon_materials.deserialize(doc)


if __name__ == '__main__':
    unittest.main()
