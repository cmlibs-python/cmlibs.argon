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

from cmlibs.argon.argonmodelsources import deserializeArgonModelSource
from cmlibs.argon.argonerror import ArgonError
from cmlibs.zinc.status import OK as ZINC_OK


REGION_PATH_SEPARATOR = "/"


class ArgonRegion(object):

    def __init__(self, name, zincRegion, parent=None):
        self._name = name
        self._parent = parent
        self._children = []
        self._modelSources = []
        self._zincRegion = zincRegion
        self._tessellation_name = None
        # record whether region was created by ancestor model source; see: _reloadModelSources
        self._ancestorModelSourceCreated = False
        # callback class, only for root region
        if not parent:
            self._regionChangeCallbacks = []

        self._fieldTypeDict = {}

    # def __del__(self):
    #    print("NeonRegion.__del__ " + self.getDisplayName())

    def freeContents(self):
        """
        Deletes subobjects of region to help free memory held by Zinc objects earlier.
        """
        del self._zincRegion
        for child in self._children:
            child.freeContents()

    def _createBlankCopy(self):
        zincRegion = self._zincRegion.createRegion()
        if self._name:
            zincRegion.setName(self._name)
        blankRegion = ArgonRegion(self._name, zincRegion, self._parent)
        return blankRegion

    def _assign(self, source):
        """
        Replace contents of self with that of source. Fixes up Zinc parent/child region relationships.
        """
        if self._parent:
            oldZincRegion = self._zincRegion
            zincSiblingAfter = oldZincRegion.getNextSibling()
        else:
            oldZincRegion = None
            zincSiblingAfter = None
        self.freeContents()
        self._name = source._name
        # self._parent = source._parent should not be changed
        self._children = source._children
        for child in self._children:
            child._parent = self
        self._modelSources = source._modelSources
        self._zincRegion = source._zincRegion
        # self._ancestorModelSourceCreated is unchanged
        if self._parent:
            self._parent._zincRegion.removeChild(oldZincRegion)
            self._parent._zincRegion.insertChildBefore(self._zincRegion, zincSiblingAfter)

    def _informRegionChange(self, treeChange):
        """
        Called by regions when their tree structure changes or zinc regions are rebuilt.
        Informs registered clients of change. Root region handle these signals for whole tree.
        """
        rootRegion = self
        while rootRegion._parent:
            rootRegion = rootRegion._parent
        for callback in rootRegion._regionChangeCallbacks:
            callback(self, treeChange)

    def connectRegionChange(self, callableObject):
        """
        Request callbacks on region tree changes.

        :param callableObject: Callable object taking a NeonRegion argument and a boolean flag which is True if tree
                               structure below region needs to be rebuilt.
        """
        self._regionChangeCallbacks.append(callableObject)

    def _loadModelSourceStreams(self, streamInfo):
        self._zincRegion.beginHierarchicalChange()
        result = self._zincRegion.read(streamInfo)
        fieldmodule = self._zincRegion.getFieldmodule()
        fieldmodule.defineAllFaces()
        self._zincRegion.endHierarchicalChange()
        if result != ZINC_OK:
            raise ArgonError("Failed to load model sources into region " + self.getPath())

    def _loadModelSource(self, modelSource):
        streamInfo = self._zincRegion.createStreaminformationRegion()
        modelSource.addToZincStreaminformationRegion(streamInfo)
        self._loadModelSourceStreams(streamInfo)
        newRegionCount = self._discoverNewZincRegions()
        self._informRegionChange(newRegionCount > 0)
        self._updateTimekeeper()

    def _loadModelSources(self):
        streamInfo = self._zincRegion.createStreaminformationRegion()
        for modelSource in self._modelSources:
            modelSource.addToZincStreaminformationRegion(streamInfo)
        self._loadModelSourceStreams(streamInfo)
        self._updateTimekeeper()

    def _updateTimekeeper(self):
        current_region = self._zincRegion
        parent_region = current_region.getParent()
        while parent_region.isValid():
            current_region = parent_region
            parent_region = current_region.getParent()

        root_region = current_region
        scene = root_region.getScene()
        time_keeper_module = scene.getTimekeepermodule()
        time_keeper = time_keeper_module.getDefaultTimekeeper()
        result, minimum_time, maximum_time = root_region.getTimeRange()
        if result == ZINC_OK:
            current_minimum_time = time_keeper.getMinimumTime()
            if current_minimum_time != minimum_time:
                time_keeper.setMinimumTime(minimum_time)
            current_maximum_time = time_keeper.getMaximumTime()
            if current_maximum_time != maximum_time:
                time_keeper.setMaximumTime(maximum_time)

    def _reload(self):
        """
        Must be called when already-loaded model source modified or deleted.
        Saves and reloads region tree, starting at ancestor if this region was created by its model source.
        """
        if self._ancestorModelSourceCreated:
            self._parent._reload()
        else:
            # beware this breaks parent/child links such as current selection / hierarchical groups
            dictSave = self.serialize()
            tmpRegion = self._createBlankCopy()
            tmpRegion.deserialize(dictSave)
            self._assign(tmpRegion)
            self._informRegionChange(True)

    def _discoverNewZincRegions(self):
        """
        Ensure there are Neon regions for every Zinc Region in tree.

        :return: Number of new descendant regions created
        """
        newRegionCount = 0
        zincChildRef = self._zincRegion.getFirstChild()
        while zincChildRef.isValid():
            childName = zincChildRef.getName()
            neonChild = self._findChildByName(childName)
            if not neonChild:
                neonChild = ArgonRegion(childName, zincChildRef, self)
                neonChild._ancestorModelSourceCreated = True
                self._children.append(neonChild)
                newRegionCount += (1 + neonChild._discoverNewZincRegions())
            zincChildRef = zincChildRef.getNextSibling()
        return newRegionCount

    def _findChildByName(self, name):
        for child in self._children:
            if child._name == name:
                return child
        return None

    def _generateChildName(self):
        count = len(self._children) + 1
        while True:
            name = "region" + str(count)
            if not self._findChildByName(name):
                return name
            count += 1
        return None

    def deserialize(self, dictInput):
        """
        Read the JSON description to the argon region object. This will change the settings of ArgonRegion Object.

        :param  state: string serialisation of Argon JSON Region.
        """
        if "Model" in dictInput:
            model = dictInput["Model"]
            if "Sources" in model:
                try:
                    for dictModelSource in model["Sources"]:
                        modelSource = deserializeArgonModelSource(dictModelSource)
                        if modelSource:
                            self._modelSources.append(modelSource)
                except ArgonError as neonError:
                    raise ArgonError(neonError.getMessage() + " in region " + self.getPath())
                self._loadModelSources()

        if "Fieldmodule" in dictInput:
            # must define fields before scene otherwise referenced fields won't exist
            fieldmodule = self._zincRegion.getFieldmodule()
            fieldmoduleDescription = json.dumps(dictInput["Fieldmodule"])
            result = fieldmodule.readDescription(fieldmoduleDescription)
            if result != ZINC_OK:
                raise ArgonError("Failed to read field module description into region " + self.getPath())

        if "Scene" in dictInput:
            scene = self._zincRegion.getScene()
            sceneDescription = json.dumps(dictInput["Scene"])
            result = scene.readDescription(sceneDescription, True)
            if result != ZINC_OK:
                raise ArgonError("Failed to read scene description into region " + self.getPath())

        if ("Fieldmodule" in dictInput) and isinstance(dictInput["Fieldmodule"], dict) and \
                ("Fields" in dictInput["Fieldmodule"]):
            # clear IsManaged flags for fields so marked; do last otherwise fields in use by scene may be destroyed
            fieldsDict = dictInput["Fieldmodule"]["Fields"]
            for fieldDict in fieldsDict:
                isManaged = fieldDict["IsManaged"]
                if not isManaged:
                    field = fieldmodule.findFieldByName(fieldDict["Name"])
                    if field.isValid():
                        field.setManaged(False)
                for currentKey in fieldDict.keys():
                    if currentKey.find('Field') != -1:
                        self._fieldTypeDict[fieldDict["Name"]] = currentKey

        # following assumes no neon child regions exist, i.e. we are deserializing into a blank region
        # for each neon region, ensure there is a matching zinc region in the same order, and recurse
        zincChildRef = self._zincRegion.getFirstChild()
        if "ChildRegions" in dictInput:
            for dictChild in dictInput["ChildRegions"]:
                childName = dictChild["Name"]
                # see if zinc child with this name created by model source here or in ancestor region
                ancestorModelSourceCreated = True
                zincChild = self._zincRegion.findChildByName(childName)
                if zincChildRef.isValid() and (zincChild == zincChildRef):
                    zincChildRef = zincChildRef.getNextSibling()
                else:
                    if not zincChild.isValid():
                        zincChild = self._zincRegion.createRegion()
                        zincChild.setName(childName)
                        ancestorModelSourceCreated = False
                    self._zincRegion.insertChildBefore(zincChild, zincChildRef)
                neonChild = ArgonRegion(childName, zincChild, self)
                neonChild._ancestorModelSourceCreated = ancestorModelSourceCreated
                self._children.append(neonChild)
                neonChild.deserialize(dictChild)
        self._discoverNewZincRegions()

    def serialize(self, basePath=None):
        """
        Write the JSON file describing the Argon region, which can be used to store the current argon region settings.

        :param basePath: The base path of JSON file, default is None.
        :return: Python JSON object containing the JSON description of argon region object.
        """
        dictOutput = {}
        if self._name:
            dictOutput["Name"] = self._name
        dictOutput["Model"] = {}
        if self._modelSources:
            tmpOutput = []
            for modelSource in self._modelSources:
                tmpOutput.append(modelSource.serialize(basePath))
            dictOutput["Model"]["Sources"] = tmpOutput
        if not dictOutput["Model"]:
            dictOutput.pop("Model")
        if self._zincRegion:
            fieldmodule = self._zincRegion.getFieldmodule()
            fieldmoduleDescription = fieldmodule.writeDescription()
            dictOutput["Fieldmodule"] = json.loads(fieldmoduleDescription)

            scene = self._zincRegion.getScene()
            sceneDescription = scene.writeDescription()
            dictOutput["Scene"] = json.loads(sceneDescription)
            if self._tessellation_name:
                for g in dictOutput["Scene"]["Graphics"]:
                    g["Tessellation"] = self._tessellation_name
        if self._children:
            tmpOutput = []
            for child in self._children:
                tmpOutput.append(child.serialize(basePath))
            dictOutput["ChildRegions"] = tmpOutput

        return dictOutput

    def setTessellation(self, tessellation_name):
        self._tessellation_name = tessellation_name

    def getDisplayName(self):
        """
        Returns the display name of current region.

        :return: string
        """
        if self._name:
            return self._name
        elif not self._parent:
            return REGION_PATH_SEPARATOR
        return "?"

    def getName(self):
        """
        Returns the name of current region.

        :return: string
        """
        return self._name

    def getPath(self):
        """
        Returns the path of current region.

        :return: string
        """
        if self._name:
            return self._parent.getPath() + self._name + REGION_PATH_SEPARATOR
        return REGION_PATH_SEPARATOR

    def getParent(self):
        """
        Returns the parent Argon region of current region.

        :return: ArgonRegion
        """
        return self._parent

    def getZincRegion(self):
        """
        Returns the underlying Zinc context for the Argon region.

        :return: cmlibs.zinc.context.Context
        """
        return self._zincRegion

    def getChildCount(self):
        """
        Returns the number of child regions the current region has.

        :return: int
        """
        return len(self._children)

    def getChild(self, index):
        """
        Returns the child region of current region by given index.

        :param index: The index of target region.
        :return: ArgonRegion
        """
        return self._children[index]

    def getFieldTypeDict(self):
        """
        Returns the dictionary of field type in current region.

        :return: dict
        """
        return self._fieldTypeDict

    def addFieldTypeToDict(self, field, fieldType):
        """
        Add new field type and field to the field type dictionary in current region.

        :param field: The field need to be added to current region.
        :param fieldType: The field type of the field.
        """
        if field and field.isValid():
            self._fieldTypeDict[field.getName()] = fieldType

    def replaceFieldTypeKey(self, oldName, newName):
        """
        Replace field type name in the field type dictionary in current region.

        :param oldName: Current field need to be replaced.
        :param newName: New name that will be change to.
        """
        if oldName in self._fieldTypeDict:
            self._fieldTypeDict[newName] = self._fieldTypeDict.pop(oldName)

    def clear(self):
        """
        Clear all contents of region. Can be called for root region
        """
        tmpRegion = self._createBlankCopy()
        self._assign(tmpRegion)
        if self._ancestorModelSourceCreated:
            self._reload()
        else:
            self._informRegionChange(True)

    def createChild(self):
        """
        Create a child region with a default name

        :return: ArgonRegion
        """
        childName = self._generateChildName()
        zincRegion = self._zincRegion.createChild(childName)
        if zincRegion.isValid():
            childRegion = ArgonRegion(childName, zincRegion, self)
            self._children.append(childRegion)
            self._informRegionChange(True)
            return childRegion
        return None

    def removeChild(self, childRegion):
        """
        Remove child region and destroy.

        :param childRegion: ArgonRegion
        """
        self._children.remove(childRegion)
        self._zincRegion.removeChild(childRegion._zincRegion)
        childRegion._parent = None
        childRegion.freeContents()
        if childRegion._ancestorModelSourceCreated:
            self._reload()
        else:
            self._informRegionChange(True)

    def remove(self):
        """
        Remove self from region tree and destroy; replace with blank region if root
        """
        if self._parent:
            self._parent.removeChild(self)
        else:
            self.clear()

    def setName(self, name):
        """
        Change region name, the name of Root Region can not be changed.

        :param name: string
        """
        if not self._parent:
            return False
        if len(name) == 0:
            return False
        if self._ancestorModelSourceCreated:
            return False
        if ZINC_OK != self._zincRegion.setName(name):
            return False
        self._name = name
        self._informRegionChange(True)
        return True

    def getModelSources(self):
        """
        Get model sources.

        :return: The model source
        """
        return self._modelSources

    def addModelSource(self, modelSource):
        """
        Add model source, applying it if not currently editing

        :param modelSource: The model source to add
        """
        self._modelSources.append(modelSource)
        if not modelSource.isEdit():
            self.applyModelSource(modelSource)

    def applyModelSource(self, modelSource):
        """
        Apply model source, loading it or reloading it with all other sources as required

        :param modelSource: The model source to apply
        """
        modelSource.setEdit(False)
        if modelSource.isLoaded():
            self._reload()
        else:
            self._loadModelSource(modelSource)

    def removeModelSource(self, modelSource):
        """
        Remove model source, reloading model if it removed source had been loaded

        :param modelSource: The model source to remove
        """
        self._modelSources.remove(modelSource)
        if modelSource.isLoaded():
            modelSource.unload()
            self._reload()
