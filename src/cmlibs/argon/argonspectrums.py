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

SPECTRUM_GLYPH_NAME_FORMAT = 'colour_bar_{0}'


class ArgonSpectrums(object):
    """
    Manages and serializes Zinc Spectrums within Neon.
    Generates colour bar glyphs for spectrums, which is automatically done if if not found on loading.
    """

    def __init__(self, zincContext):
        self._zincContext = zincContext
        self._spectrummodule = zincContext.getSpectrummodule()
        self._findOrCreateAllSpectrumGlyphColourBars()

    def getZincContext(self):
        """
        Return the zinc Context of current argon spectrum.

        :return: cmlibs.zinc.context.Context
        """
        return self._zincContext

    def deserialize(self, dictInput):
        """
        Read the JSON description to the Argon spectrum object. This will change the spectrums in the Zinc spectrum module. 
        Raising an ArgonError if Zinc spectrum module read JSON description failed.

        :param  dictInput: The string containing JSON description
        """
        spectrumsDescription = json.dumps(dictInput)
        result = self._spectrummodule.readDescription(spectrumsDescription)
        if result != ZINC_OK:
            raise ArgonError("Failed to read spectrums")
        self._findOrCreateAllSpectrumGlyphColourBars()

    def serialize(self):
        """
        Write the JSON file describing the spectrums in the argon spectrum object, which can be used to store the current spectrum settings.

        :return: Python JSON object containing the JSON description of argon spectrum object, otherwise 0.
        """
        spectrumsDescription = self._spectrummodule.writeDescription()
        dictOutput = json.loads(spectrumsDescription)
        return dictOutput

    def _findOrCreateAllSpectrumGlyphColourBars(self):
        """
        Ensures there exists a colour bar for each spectrum.
        """
        iterator = self._spectrummodule.createSpectrumiterator()
        spectrum = iterator.next()
        while spectrum.isValid():
            self.findOrCreateSpectrumGlyphColourBar(spectrum)
            spectrum = iterator.next()

    def _findSpectrumGlyphColourBar(self, spectrum):
        """
        Find or create a GlyphColourBar for spectrum in the glyph module.
        Newly created colour bar is set up for display in the normalised window coordinates at left.
        """
        glyphmodule = self._zincContext.getGlyphmodule()
        glyphName = SPECTRUM_GLYPH_NAME_FORMAT.format(spectrum.getName())

        # try to find by name first
        glyph = glyphmodule.findGlyphByName(glyphName)
        colourBar = glyph.castColourBar()
        if colourBar.isValid() and (colourBar.getSpectrum() == spectrum):
            return colourBar

        # attempt to find by matching spectrum but do not rename it
        glyphiterator = glyphmodule.createGlyphiterator()
        glyph = glyphiterator.next()
        while glyph.isValid():
            colourBar = glyph.castColourBar()
            if colourBar.isValid() and (colourBar.getSpectrum() == spectrum):
                return colourBar
            glyph = glyphiterator.next()

        return None

    def findOrCreateSpectrumGlyphColourBar(self, spectrum):
        """
        Find or create a GlyphColourBar for spectrum in the glyph module.
        Newly created colour bar is set up for display in the normalised window coordinates at left.

        :param spectrum: The spectrum that the colour bar belongs to.
        """
        colourBar = self._findSpectrumGlyphColourBar(spectrum)
        if colourBar:
            return colourBar

        glyphmodule = self._zincContext.getGlyphmodule()
        glyphName = SPECTRUM_GLYPH_NAME_FORMAT.format(spectrum.getName())

        # create a new colour bar, matching Cmgui's defaults:
        glyphmodule.beginChange()
        colourBar = glyphmodule.createGlyphColourBar(spectrum)
        tmpName = glyphName
        i = 1
        while colourBar.setName(tmpName) != ZINC_OK:
            tmpName = glyphName + str(i)
            i += 1
        colourBar.setManaged(True)
        colourBar.setCentre([0.0, 0.0, 0.0])
        colourBar.setAxis([0.0, 1.6, 0.0])  # includes length
        colourBar.setSideAxis([0.06, 0.0, 0.0])  # includes radius
        colourBar.setExtendLength(0.06)
        colourBar.setTickLength(0.04)
        colourBar.setLabelDivisions(10)
        colourBar.setNumberFormat('%+.4e')
        glyphmodule.endChange()
        return colourBar

    def renameSpectrum(self, spectrum, name):
        """
        Renames spectrum and its glyph

        :param spectrum: The spectrum that need to be renamed.
        :param name: New name to the spectrum.
        :return: True on success, otherwise False (means name not set)
        """
        colourBar = self.findOrCreateSpectrumGlyphColourBar(spectrum)
        result = spectrum.setName(name)
        if result == ZINC_OK:
            glyphName = SPECTRUM_GLYPH_NAME_FORMAT.format(name)
            tmpName = glyphName
            i = 1
            while (colourBar.setName(tmpName) != ZINC_OK):
                tmpName = glyphName + str(i)
                i += 1
            return True
        return False

    def removeSpectrumByName(self, name):
        """
        Unmanages spectrum and its colour bar. Note spectrum is only removed if neither are in use.

        :return: True if spectrum and colour bar removed, false if failed i.e. either are in use.
        """
        spectrum = self._spectrummodule.findSpectrumByName(name)
        colourBar = self._findSpectrumGlyphColourBar(spectrum)
        if colourBar:
            colourBarName = colourBar.getName()
            colourBar.setManaged(False)
            del colourBar
            colourBar = self._findSpectrumGlyphColourBar(spectrum)
            if colourBar and (colourBar.getName() == colourBarName):
                # colour bar is in use; do not remove spectrum
                colourBar.setManaged(True)
                return False
        spectrum.setManaged(False)
        del spectrum
        spectrum = self._spectrummodule.findSpectrumByName(name)
        if spectrum.isValid():
            # spectrum is in use so can't remove
            spectrum.setManaged(True)
            self.findOrCreateSpectrumGlyphColourBar(spectrum)
            return False
        return True
