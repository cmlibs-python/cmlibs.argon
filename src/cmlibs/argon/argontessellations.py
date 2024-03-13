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
import json

from cmlibs.zinc.status import OK as ZINC_OK
from cmlibs.argon.argonerror import ArgonError


class ArgonTessellations(object):
    """
    Manages and serializes Zinc Tessellations within Neon.
    """

    def __init__(self, zincContext):
        self._zincContext = zincContext
        self._tessellationmodule = zincContext.getTessellationmodule()
        self._tessellationLevel = "medium"

    def getZincContext(self):
        """
        Return the zinc Context of current Argon Tessellations.

        :return: cmlibs.zinc.context.Context
        """
        return self._zincContext

    def deserialize(self, dictInput):
        """
        Read the JSON description to the Argon Tessellations object. This will change the tessellation in the Zinc tessellation module. 
        Raising an ArgonError if Zinc tessellation module read JSON description failed.

        :param  dictInput: The string containing JSON description
        """
        tessellationsDescription = json.dumps(dictInput)
        result = self._tessellationmodule.readDescription(tessellationsDescription)
        if result != ZINC_OK:
            raise ArgonError("Failed to read tessellations")

    def serialize(self):
        """
        Write the JSON file describing the tessellations in the argon tessellation object, which can be used to store the current tessellation settings.

        :return: Python JSON object containing the JSON description of argon tessellation object, otherwise 0.
        """
        tessellationsDescription = self._tessellationmodule.writeDescription()
        dictOutput = json.loads(tessellationsDescription)
        if self._tessellationLevel != "medium":
            new_tessellation = {
                "CircleDivisions": 12,
                "MinimumDivisions": [
                    1
                ],
                "Name": "tessellation_%s" % self._tessellationLevel,
                "RefinementFactors": [
                    1 if self._tessellationLevel == "low" else 12
                ]
            }
            dictOutput["Tessellations"].append(new_tessellation)

        return dictOutput

    def setTessellationLevel(self, level):
        """
        Set tessellation level.
        """
        self._tessellationLevel = level
