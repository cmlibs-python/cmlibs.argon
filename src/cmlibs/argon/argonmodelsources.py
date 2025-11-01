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
import os
import pathlib

from cmlibs.zinc.streamregion import StreaminformationRegion
from cmlibs.argon.argonerror import ArgonError


def _file_name_to_relative_path(file_name, base_path):
    if (base_path is None) or (not os.path.isabs(file_name)) or (os.path.commonprefix([file_name, base_path]) == ""):
        return pathlib.PurePath(file_name).as_posix()
    return pathlib.PurePath(os.path.relpath(file_name, base_path)).as_posix()


class ArgonModelSourceFile(object):

    def __init__(self, file_name=None, dict_input=None, base_path=None):
        self._time = None
        self._format = None
        self._edit = False
        self._loaded = False
        if file_name is not None:
            self._file_name = file_name
        else:
            self._deserialize(dict_input, base_path)

    def getType(self):
        """
        Returns Argon Model Source File type "FILE".

        :return: string
        """
        return "FILE"

    def addToZincStreaminformationRegion(self, stream_info):
        """
        Add to Zinc Stream information Region.

        :param stream_info: streamInfo
        """
        if self._edit:
            return
        if not self._file_name:
            self._edit = True
            return
        resource = stream_info.createStreamresourceFile(self._file_name)
        self._loaded = True
        if self._time is not None and self._time:
            time = self._time
            if not isinstance(self._time, float):
                time = float(self._time)
            stream_info.setResourceAttributeReal(resource, StreaminformationRegion.ATTRIBUTE_TIME, time)
        # if self._format is not None:
        #    if format == "EX":
        #        #can't set per-resource file format
        #        #streamInfo.setResourceFileFormat(resource, StreaminformationRegion.FILE_FORMAT_EX)

    def unload(self):
        """
        Set Argon model sources loaded state to False.
        """
        self._loaded = False

    def getFileName(self):
        """
        Returns the file name of current Argon model sources.

        :return: string
        """
        return self._file_name

    def setFileName(self, file_name):
        """
        Set file name.

        :param file_name: string
        """
        self._file_name = file_name

    def getTime(self):
        """
        Returns the time of current Argon model sources.

        :return: string
        """
        return self._time

    def setTime(self, time):
        """
        Change time.

        :param time: string
        """
        self._time = time

    def getDisplayName(self):
        """
        Returns the display name of current Argon model sources.

        :return: string
        """
        editText = "[To Apply] " if self._edit else ""
        if self._time is None:
            timeText = ""
        else:
            timeText = ", time " + repr(self._time)
        displayFileName = os.path.basename(self._file_name)
        return editText + "File " + displayFileName + timeText

    def isLoaded(self):
        """
        Returns the load state of current Argon model sources.

        :return: boolean
        """
        return self._loaded

    def isEdit(self):
        """
        Returns the edit state of current Argon model sources.

        :return: boolean
        """
        return self._edit

    def setEdit(self, edit):
        """
        Change edit state for Argon model sources.

        :param edit: boolean
        """
        self._edit = edit

    def _deserialize(self, dict_input, reference_dir):
        # convert to absolute file path so can save Neon file to new location and get correct relative path
        if reference_dir is not None:
            self._file_name = os.path.abspath(os.path.join(reference_dir, dict_input["FileName"]))
        else:
            self._file_name = os.path.abspath(dict_input["FileName"])
        if "Edit" in dict_input:
            self._edit = dict_input["Edit"]
        if "Format" in dict_input:
            self._format = dict_input["Format"]
        if "Time" in dict_input:
            self._time = dict_input["Time"]

    def serialize(self, base_path=None):
        """
        Write the JSON file describing the Argon model sources, which can be used to store the current Argon model sources settings.
        :param base_path: The base path of JSON file, default is None.
        :return: Python JSON object containing the JSON description of Argon model sources object.
        """
        dict_output = {
            "Type": self.getType(),
            "FileName": _file_name_to_relative_path(self._file_name, base_path)
        }
        if self._edit:
            dict_output["Edit"] = True
        if self._format is not None:
            dict_output["Format"] = self._format
        if self._time is not None:
            dict_output["Time"] = self._time

        return dict_output


def deserializeArgonModelSource(dict_input, base_path=None):
    """
    Factory method for creating the appropriate neon model source type from the dict serialization
    """
    if "Type" not in dict_input:
        raise ArgonError("Model source is missing Type attribute")

    typeString = dict_input["Type"]
    if typeString == "FILE":
        modelSource = ArgonModelSourceFile(dict_input=dict_input, base_path=base_path)
    else:
        raise ArgonError("Model source has unrecognised Type " + typeString)
    return modelSource
