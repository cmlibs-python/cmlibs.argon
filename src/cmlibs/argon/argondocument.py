"""
   Copyright 2015 University of Auckland

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
import json

from packaging import version

from cmlibs.argon import __version__
from cmlibs.argon.argonregion import ArgonRegion, REGION_PATH_SEPARATOR
from cmlibs.argon.argonspectrums import ArgonSpectrums
from cmlibs.argon.argonmaterials import ArgonMaterials
from cmlibs.argon.argonviews import ArgonViewManager
from cmlibs.argon.argontessellations import ArgonTessellations
from cmlibs.argon.argonerror import ArgonError
from cmlibs.argon.argonlogger import ArgonLogger
from cmlibs.argon.settings import mainsettings

from cmlibs.zinc.context import Context
from cmlibs.zinc.material import Material


ARGON_DOCUMENT_VERSION_KEY = "CMLibs Argon Version"


class ArgonDocument(object):

    def __init__(self, name="Argon"):
        self._name = name
        self._zincContext = None
        self._rootRegion = None
        self._spectrums = None
        self._materials = None
        self._view_manager = None
        self._tessellations = None

    def checkVersion(self, minimum_required):
        """
        Check the version number of this Argon library. Raise an error if current Argon is less than the minimun required version.
        """
        if version.parse(__version__) < version.parse(minimum_required):
            raise SyntaxError(f"Argon document error - Argon document must be at least version '{minimum_required}'.")

    def getName(self):
        """
        Returns the name of the zinc Context.

        :return: string
        """
        return self._zincContext.getName()

    def initialiseVisualisationContents(self):
        """
        Initialise the default Visualisation Contents.
        """
        self._zincContext = Context(self._name)

        sceneviewermodule = self._zincContext.getSceneviewermodule()
        sceneviewermodule.setDefaultBackgroundColourRGB([1.0, 1.0, 1.0])

        # set up standard materials and glyphs
        materialmodule = self._zincContext.getMaterialmodule()
        materialmodule.beginChange()
        materialmodule.defineStandardMaterials()
        # make default material black
        defaultMaterial = materialmodule.getDefaultMaterial()
        defaultMaterial.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [0.0, 0.0, 0.0])
        defaultMaterial.setAttributeReal3(Material.ATTRIBUTE_DIFFUSE, [0.0, 0.0, 0.0])
        # still want surfaces to default to white material
        white = materialmodule.findMaterialByName("white")
        materialmodule.setDefaultSurfaceMaterial(white)
        materialmodule.endChange()
        glyphmodule = self._zincContext.getGlyphmodule()
        glyphmodule.defineStandardGlyphs()
        spectrummodule = self._zincContext.getSpectrummodule()
        spectrummodule.defineStandardSpectrums()

        zincRootRegion = self._zincContext.getDefaultRegion()
        self._rootRegion = ArgonRegion(name=None, zincRegion=zincRootRegion, parent=None)
        self._rootRegion.connectRegionChange(self._regionChange)

        self._materials = materialmodule
        self._spectrums = ArgonSpectrums(self._zincContext)
        self._materials = ArgonMaterials(self._zincContext)
        self._view_manager = ArgonViewManager(self._zincContext)
        self._tessellations = ArgonTessellations(self._zincContext)
        ArgonLogger.setZincContext(self._zincContext)

    def freeVisualisationContents(self):
        """
        Deletes subobjects of document to help free memory held by Zinc objects earlier.
        """
        self._rootRegion.freeContents()
        del self._tessellations
        del self._spectrums
        del self._materials
        del self._view_manager
        del self._rootRegion
        del self._zincContext

    def _regionChange(self, changedRegion, treeChange):
        """
        If root region has changed, set its new Zinc region as Zinc context's default region.
        :param changedRegion: The top region changed
        :param treeChange: True if structure of tree, or zinc objects reconstructed
        """
        if treeChange and (changedRegion is self._rootRegion):
            zincRootRegion = changedRegion.getZincRegion()
            self._zincContext.setDefaultRegion(zincRootRegion)

    def deserialize(self, state):
        """
        Read the JSON description to the argon document object. This will change the settings of ArgonDocument Object.

        :param  state: string serialisation of Argon JSON document.
        """
        d = json.loads(state)
        if not ((ARGON_DOCUMENT_VERSION_KEY in d) and ("RootRegion" in d)):
            raise ArgonError("Invalid Argon document")

        document_version = d[ARGON_DOCUMENT_VERSION_KEY]
        document_version_string = ".".join(document_version)
        if version.parse(document_version_string) > version.parse(mainsettings.VERSION_STRING):
            raise ArgonError(f"Document version '{document_version_string}' is greater than this version of Argon ({mainsettings.VERSION_STRING})."
                             f" Please update your Argon application.")
        # Ideally would enclose following in:
        # try: zincRegion.beginHierarchicalChange() ... finally: zincRegion.endHierarchicalChange()
        # Can't do this due to Zinc issue 3924 which prevents computed field wrappers being created, so graphics can't find fields
        if "Tessellations" in d:
            self._tessellations.deserialize(d["Tessellations"])
        if "Spectrums" in d:
            self._spectrums.deserialize(d["Spectrums"])
        if "Materials" in d:
            self._materials.deserialize(d["Materials"])
        if "Views" in d:
            self._view_manager.deserialize(d["Views"])
        self._rootRegion.deserialize(d["RootRegion"])

    def serialize(self, base_path=None):
        """
        Write the JSON file describing the Argon document in the argon document object, which can be used to store the current argon document settings.

        :param base_path: The base path of JSON file, default is None.
        :return: Python JSON object containing the JSON description of argon document object.
        """
        dictOutput = {
            ARGON_DOCUMENT_VERSION_KEY: mainsettings.VERSION_LIST,
            "Spectrums": self._spectrums.serialize(),
            "Materials": self._materials.serialize(),
            "Views": self._view_manager.serialize(),
            "Tessellations": self._tessellations.serialize(),
            "RootRegion": self._rootRegion.serialize(base_path)
        }
        return json.dumps(dictOutput, default=lambda o: o.__dict__, sort_keys=True, indent=2)

    def getZincContext(self):
        """
        Returns the underlying Zinc context for the document.

        :return: cmlibs.zinc.context.Context
        """
        return self._zincContext

    def getRootRegion(self):
        """
        Returns the root region in the context. A convenience for applications that need only one region tree.

        :return: ArgonRegion
        """
        return self._rootRegion

    def getSpectrums(self):
        """
        Returns the spectrums in the context.

        :return: ArgonSpectrums
        """
        return self._spectrums

    def getMaterials(self):
        """
        Returns the materials in the context.

        :return: ArgonMaterials
        """
        return self._materials

    def getViewManager(self):
        """
        Returns the view manager in the context.

        :return: ArgonViewManager
        """
        return self._view_manager

    def getTessellations(self):
        """
        Returns the tessellations in the context.

        :return: ArgonTessellations
        """
        return self._tessellations

    def setTessellationLevel(self, level):
        """
        Set the tessellations.
        """
        if level == "medium":
            self._rootRegion.setTessellation("default")
        else:
            self._tessellations.setTessellationLevel(level)
            self._rootRegion.setTessellation("tessellation_%s" % level)

        state = self.serialize()
        self.deserialize(state)

    def findRegion(self, name):
        """
        Find region by name.

        :param name: The name of the region as a string.
        :return: ArgonRegion or None if region is not found.
        """
        if not name.endswith(REGION_PATH_SEPARATOR):
            name += REGION_PATH_SEPARATOR
        return _findSubRegion(self._rootRegion, name)


def _findSubRegion(region, name):
    region_path = region.getPath()
    if name == region_path:
        return region
    elif name.startswith(region_path):
        for child_index in range(region.getChildCount()):
            result = _findSubRegion(region.getChild(child_index), name)
            if result is not None:
                return result

    return None
