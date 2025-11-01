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
from cmlibs.zinc.sceneviewer import Sceneviewer

SceneviewerProjectionModeMap = {
    Sceneviewer.PROJECTION_MODE_PARALLEL: "PARALLEL",
    Sceneviewer.PROJECTION_MODE_PERSPECTIVE: "PERSPECTIVE"
}


def SceneviewerProjectionModeEnumFromString(projectionModeName: str):
    for mode, name in SceneviewerProjectionModeMap.items():
        if name == projectionModeName:
            return mode
    return Sceneviewer.PROJECTION_MODE_INVALID


def SceneviewerProjectionModeEnumToString(projectionMode):
    for mode, name in SceneviewerProjectionModeMap.items():
        if mode == projectionMode:
            return name
    return None


SceneviewerTransparencyModeMap = {
    Sceneviewer.TRANSPARENCY_MODE_FAST: "FAST",
    Sceneviewer.TRANSPARENCY_MODE_SLOW: "SLOW",
    Sceneviewer.TRANSPARENCY_MODE_ORDER_INDEPENDENT: "ORDER_INDEPENDENT"
}


def SceneviewerTransparencyModeEnumFromString(transparencyModeName: str):
    for mode, name in SceneviewerTransparencyModeMap.items():
        if name == transparencyModeName:
            return mode
    return Sceneviewer.TRANSPARENCY_MODE_INVALID


def SceneviewerTransparencyModeEnumToString(transparencyMode):
    for mode, name in SceneviewerTransparencyModeMap.items():
        if mode == transparencyMode:
            return name
    return None


class ArgonSceneviewer(object):

    def __init__(self, zinc_context, parent=None):
        self._zinc_context = zinc_context
        self._parent = parent
        self._anti_alias_sampling = default_anti_alias_sampling
        self._background_colour_RGB = default_background_colour_RGB
        self._eye_position = default_eye_position
        self._far_clipping_plane = default_far_clipping_plane
        self._lighting_local_viewer = default_lighting_local_viewer
        self._lighting_two_sided = default_lighting_two_sided
        self._lookat_position = default_lookat_position
        self._near_clipping_plane = default_near_clipping_plane
        self._perturb_lines_flag = default_perturb_lines_flag
        self._projection_mode = default_projection_mode
        self._scene = default_scene
        self._scene_filter = default_scene_filter
        self._translation_rate = default_translation_rate
        self._transparency_mode = default_transparency_mode
        self._transparency_layers = default_transparency_layers
        self._tumble_rate = default_tumble_rate
        self._up_vector = default_up_vector
        self._view_angle = default_view_angle
        self._zoom_rate = default_zoom_rate

    def applyParameters(self, sceneviewer):
        """
        Apply Argon sceneviewer parameters to Zinc sceneviewer.

        :param  sceneviewer: Zinc scenviewer object.
        """
        sceneviewer.setEyePosition(self._eye_position)
        sceneviewer.setLookatPosition(self._lookat_position)
        sceneviewer.setUpVector(self._up_vector)
        sceneviewer.setNearClippingPlane(self._near_clipping_plane)
        sceneviewer.setFarClippingPlane(self._far_clipping_plane)
        sceneviewer.setBackgroundColourRGB(self._background_colour_RGB)
        sceneviewer.setAntialiasSampling(self._anti_alias_sampling)
        sceneviewer.setProjectionMode(self._projection_mode)
        sceneviewer.setTransparencyMode(self._transparency_mode)
        sceneviewer.setTransparencyLayers(self._transparency_layers)
        sceneviewer.setLightingTwoSided(self._lighting_two_sided)
        sceneviewer.setPerturbLinesFlag(self._perturb_lines_flag)
        sceneviewer.setViewAngle(self._view_angle)
        root_region = self._zinc_context.getDefaultRegion()
        if self._scene is not None:
            scene_region = root_region.findChildByName(self._scene)
            if scene_region.isValid():
                sceneviewer.setScene(scene_region.getScene())

    def updateParameters(self, sceneviewer):
        """
        Read parameters from Zinc scenviewer to the Argon sceneviewer object. This will change the settings of ArgonSceneviewer Object.

        :param  sceneviewer: Zinc scenviewer object.
        """
        result, eye = sceneviewer.getEyePosition()
        result, lookat = sceneviewer.getLookatPosition()
        result, up_vector = sceneviewer.getUpVector()
        near = sceneviewer.getNearClippingPlane()
        far = sceneviewer.getFarClippingPlane()
        result, colourRGB = sceneviewer.getBackgroundColourRGB()
        antialiasValue = sceneviewer.getAntialiasSampling()
        projection_mode = sceneviewer.getProjectionMode()
        transparency_mode = sceneviewer.getTransparencyMode()
        transparency_layers = sceneviewer.getTransparencyLayers()
        flag_is_two_sided = sceneviewer.isLightingTwoSided()
        flag_perturb_lines = sceneviewer.getPerturbLinesFlag()
        view_angle = sceneviewer.getViewAngle()
        scene_region = sceneviewer.getScene().getRegion().getName()

        self._anti_alias_sampling = antialiasValue
        self._background_colour_RGB = colourRGB
        self._eye_position = eye
        self._far_clipping_plane = far
        self._lighting_local_viewer = default_lighting_local_viewer
        self._lighting_two_sided = flag_is_two_sided
        self._lookat_position = lookat
        self._near_clipping_plane = near
        self._perturb_lines_flag = flag_perturb_lines
        self._projection_mode = projection_mode
        self._scene = scene_region
        self._scene_filter = default_scene_filter
        self._translation_rate = default_translation_rate
        self._transparency_mode = transparency_mode
        self._transparency_layers = transparency_layers
        self._tumble_rate = default_tumble_rate
        self._up_vector = up_vector
        self._view_angle = view_angle
        self._zoom_rate = default_zoom_rate

    def get_view_parameters(self):
        """
        Return the view parameters of Argon sceneviewer.

        :return: dictionary
        """
        return {'farClippingPlane': self._far_clipping_plane, 'nearClippingPlane': self._near_clipping_plane,
                'eyePosition': self._eye_position, 'lookAtPosition': self._lookat_position, 'upVector': self._up_vector,
                'viewAngle': self._view_angle}

    def deserialize(self, d):
        """
        Read the JSON description to the Argon sceneviewer object. This will change the settings of ArgonSceneviewer Object.

        :param  d: Python JSON object containing the JSON description of Argon sceneviewer object.
        """
        # d = json.loads(s)
        self._anti_alias_sampling = d["AntialiasSampling"] if "AntialiasSampling" in d else default_anti_alias_sampling
        self._background_colour_RGB = d["BackgroundColourRGB"] if "BackgroundColourRGB" in d \
            else default_background_colour_RGB
        self._eye_position = d["EyePosition"] if "EyePosition" in d else default_eye_position
        self._far_clipping_plane = d["FarClippingPlane"] if "FarClippingPlane" in d else default_far_clipping_plane
        self._lighting_local_viewer = d["LightingLocalViewer"] if "LightingLocalViewer" in d \
            else default_lighting_local_viewer
        self._lighting_two_sided = d["LightingTwoSided"] if "LightingTwoSided" in d else default_lighting_two_sided
        self._lookat_position = d["LookatPosition"] if "LookatPosition" in d else default_lookat_position
        self._near_clipping_plane = d["NearClippingPlane"] if "NearClippingPlane" in d else default_near_clipping_plane
        self._perturb_lines_flag = d["PerturbLinesFlag"] if "PerturbLinesFlag" in d else default_perturb_lines_flag
        self._projection_mode = SceneviewerProjectionModeEnumFromString(d["ProjectionMode"]) if "ProjectionMode" in d \
            else default_projection_mode
        self._scene = d["Scene"] if "Scene" in d else default_scene
        self._scene_filter = d["Scenefilter"] if "Scenefilter" in d else default_scene_filter
        self._translation_rate = d["TranslationRate"] if "TranslationRate" in d else default_translation_rate
        self._transparency_mode = SceneviewerTransparencyModeEnumFromString(d["TransparencyMode"]) \
            if "TransparencyMode" in d else default_transparency_mode
        self._transparency_layers = d["TransparencyLayers"] if "TransparencyLayers" in d \
            else default_transparency_layers
        self._tumble_rate = d["TumbleRate"] if "TumbleRate" in d else default_tumble_rate
        self._up_vector = d["UpVector"] if "UpVector" in d else default_up_vector
        self._view_angle = d["ViewAngle"] if "ViewAngle" in d else default_view_angle
        self._zoom_rate = d["ZoomRate"] if "ZoomRate" in d else default_zoom_rate

    def serialize(self):
        """
        Write the JSON file describing the Argon sceneviewer, which can be used to store the current Argon sceneviewer settings.

        :return: Python JSON object containing the JSON description of Argon sceneviewer object.
        """
        return {
            "AntialiasSampling": self._anti_alias_sampling, "BackgroundColourRGB": self._background_colour_RGB,
            "EyePosition": self._eye_position, "FarClippingPlane": self._far_clipping_plane,
            "LightingLocalViewer": self._lighting_local_viewer, "LightingTwoSided": self._lighting_two_sided,
            "LookatPosition": self._lookat_position, "NearClippingPlane": self._near_clipping_plane,
            "PerturbLinesFlag": self._perturb_lines_flag,
            "ProjectionMode": SceneviewerProjectionModeEnumToString(self._projection_mode), "Scene": self._scene,
            "Scenefilter": self._scene_filter, "TranslationRate": self._translation_rate,
            "TransparencyMode": SceneviewerTransparencyModeEnumToString(self._transparency_mode),
            "TransparencyLayers": self._transparency_layers, "TumbleRate": self._tumble_rate, "UpVector": self._up_vector,
            "ViewAngle": self._view_angle, "ZoomRate": self._zoom_rate
        }


default_anti_alias_sampling = 0
default_background_colour_RGB = [1, 1, 1]
default_eye_position = [0, 0, 3.88551982890656]
default_far_clipping_plane = 7.88551982890656
default_lighting_local_viewer = False
default_lighting_two_sided = True
default_lookat_position = [0, 0, 0]
default_near_clipping_plane = 0.1942759914453282
default_perturb_lines_flag = False
default_projection_mode = Sceneviewer.PROJECTION_MODE_PERSPECTIVE
default_scene = "/"
default_scene_filter = "default"
default_translation_rate = 1
default_transparency_mode = Sceneviewer.TRANSPARENCY_MODE_FAST
default_transparency_layers = 1
default_tumble_rate = 1.5
default_up_vector = [0, 1, 0]
default_view_angle = 0.6981317007977318
default_zoom_rate = 1
