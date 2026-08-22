# encoding: utf-8
from __future__ import division, print_function, unicode_literals

###########################################################################################################
#
#
#	Reporter Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Reporter
#
#
###########################################################################################################

import objc
from GlyphsApp import Glyphs
from GlyphsApp.plugins import ReporterPlugin
from AppKit import NSColor, NSBezierPath, NSAffineTransform, NSPoint

class ShowVerticalMetrics(ReporterPlugin):
	lowestGlyphName = None
	tallestGlyphName = None

	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': 'Vertical Metrics',
			'de': 'Vertikalmaße',
			'es': 'métricas verticales',
			'fr': 'mesures verticales',
			'it': 'metriche verticali',
		})
		self.verticalMetrics = (
			"hheaAscender",
			"hheaDescender",
			"typoAscender",
			"typoDescender",
			"winAscent",
			"winDescent",
			# "hheaLineGap",
			# "typoLineGap",
		)

	@objc.python_method
	def metricValue(self, thisMaster, thisMetric):
		"""
		Returns the value of the vertical metric custom parameter.
		In Glyphs 4+, font-wide parameters are also accepted,
		but master parameters take precedence over them.
		"""
		height = thisMaster.customParameters[thisMetric]
		if height is None and Glyphs.versionNumber >= 4.0:
			thisFont = thisMaster.font
			if thisFont:
				height = thisFont.customParameters[thisMetric]
		return height

	@objc.python_method
	def metricColor(self):
		"""
		Returns the color for the metric lines and their names, either the
		default green or the color set in the ...ShowVerticalMetrics.color pref.
		"""
		defaultColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.4, 0.8, 0.4, 1)
		if Glyphs.defaults["com.mekkablue.ShowVerticalMetrics.color"]:
			rgba = [
				defaultColor.redComponent(),
				defaultColor.greenComponent(),
				defaultColor.blueComponent(),
				defaultColor.alphaComponent(),
			]
			colorpref = Glyphs.defaults["com.mekkablue.ShowVerticalMetrics.color"].split(",")
			for i in range(min(4, len(colorpref))):
				try:
					colorvalue = float(colorpref[i].strip())
					if colorvalue > 1.0:
						colorvalue /= 100.0
					rgba[i] = colorvalue % 1.0
				except:
					print("\nWarning: could not convert '%s' into %s value." % (colorpref[i], ("red","green","blue","alpha")[i]))
					print("com.mekkablue.ShowVerticalMetrics.color takes comma-separated numbers between 0.0 and 1.0 (or 0 and 100).")
			defaultColor = NSColor.colorWithRed_green_blue_alpha_(rgba[0], rgba[1], rgba[2], rgba[3])
		return defaultColor

	@objc.python_method
	def metricsForMaster(self, thisMaster):
		"""
		Returns a list of (metricName, height, alignment, isFirstAtThisHeight)
		tuples for all vertical metrics defined in thisMaster. Only the first
		metric at a given height gets a line, the others are labelled differently
		so that their names do not overlap.
		"""
		metrics = []
		heightsAlreadyUsed = []
		for thisMetric in self.verticalMetrics:
			height = self.metricValue(thisMaster, thisMetric)
			if not height:
				continue

			if thisMetric == "winDescent":
				height *= -1

			isFirstAtThisHeight = height not in heightsAlreadyUsed
			if isFirstAtThisHeight:
				heightsAlreadyUsed.append(height)
				alignment = "bottomright"
			else:
				alignment = "topright"
				if "win" in thisMetric:
					alignment = "bottomleft"

			metrics.append((thisMetric, height, alignment, isFirstAtThisHeight))
		return metrics

	@objc.python_method
	def currentLayer(self):
		"""
		Returns the currently edited layer. Recent Glyphs versions call
		backgroundInViewCoords() without arguments, so we need to be able to
		determine the layer ourselves.
		"""
		try:
			layer = self.controller.graphicView().activeLayer()
			if layer:
				return layer
		except:
			pass
		thisFont = Glyphs.font
		if thisFont:
			selectedLayers = thisFont.selectedLayers
			if selectedLayers:
				return selectedLayers[0]
		return None

	@objc.python_method
	def background(self, layer=None):
		"""
		Draws the metric lines in layer (em unit) coordinates.
		The metric names are drawn in backgroundInViewCoords() instead,
		because they must not move when the user zooms.
		"""
		if layer is None:
			layer = self.currentLayer()
		if not layer:
			return
		thisMaster = layer.associatedFontMaster()
		if not thisMaster:
			return

		self.metricColor().set()
		zoomFactor = self.getScale()

		for thisMetric, height, alignment, isFirstAtThisHeight in self.metricsForMaster(thisMaster):
			if not isFirstAtThisHeight:
				continue
			line = NSBezierPath.bezierPath()
			line.moveToPoint_(NSPoint(-50000, height))
			line.lineToPoint_(NSPoint(+50000, height))
			line.setLineWidth_(1.0 / zoomFactor)
			line.setLineDash_count_phase_([1.0 / zoomFactor, 3.0 / zoomFactor], 2, 3.5 / zoomFactor)
			line.stroke()

		# draw tallest and lowest glyphs:
		if False: #Glyphs.defaults["com.mekkablue.ShowVerticalMetrics.displayExtremeGlyphs"]:
			# TODO: when this is switched on again, move it into backgroundInViewCoords(),
			# so that it sticks to the left window border like the metric names do.
			xPosition = self.controller.viewPort.origin.x - self.controller.selectedLayerOrigin.x
			shiftToWindowBorder = xPosition / zoomFactor
			extremeBezierPaths = self.extremeLayerBezierPathsForFont(thisMaster.font)

			if extremeBezierPaths:
				# shift to the left side
				try:
					lsbShift = extremeBezierPaths.bounds().origin.x / zoomFactor
				except:
					lsbShift = 0
				shift = NSAffineTransform.transform()
				shift.translateXBy_yBy_(shiftToWindowBorder-lsbShift,0)
				extremeBezierPaths.transformUsingAffineTransform_(shift)

				# draw outline:
				NSColor.colorWithRed_green_blue_alpha_(1.0, 0.1, 0.3, 0.2).set()
				if zoomFactor >= 0.07:
					extremeBezierPaths.setLineWidth_(1.0 / zoomFactor)
					extremeBezierPaths.stroke()
				else:
					extremeBezierPaths.fill()
			else:
				pass
				# print("No extreme paths drawn.") # DEBUG

	@objc.python_method
	def backgroundInViewCoords(self, layer=None):
		"""
		Draws the metric names. This happens in view coordinates (screen pixels
		relative to the Edit view) rather than in em units, so the names keep a
		fixed distance from the left border of the viewport at every zoom stage.
		"""
		zoomFactor = self.getScale()
		if zoomFactor < 0.07: # only display names when zoomed in enough
			return

		if layer is None:
			layer = self.currentLayer()
		if not layer:
			return
		thisMaster = layer.associatedFontMaster()
		if not thisMaster:
			return

		fontColor = self.metricColor()

		# Left border of the Edit view plus a fixed pixel margin.
		# Careful: controller.viewPort cannot be used for this. Its origin is not
		# a position in the view, it is the visible rectangle measured relative to
		# the layer origin, so viewPort.origin.x + selectedLayerOrigin.x is always
		# the same value. The graphic view itself is the reliable source here,
		# and its visibleRect is in the same coordinates we are drawing in.
		leftWindowBorder = 0.0
		try:
			leftWindowBorder = self.controller.graphicView().visibleRect().origin.x
		except:
			pass
		xPosition = leftWindowBorder + 80
		# em units are the only thing that still needs to be scaled into view coordinates:
		yOrigin = self.controller.selectedLayerOrigin.y

		for thisMetric, height, alignment, isFirstAtThisHeight in self.metricsForMaster(thisMaster):
			yPosition = yOrigin + height * zoomFactor
			if "bottom" in alignment:
				yPosition += 2 # keep the name clear of the metric line

			self.drawTextAtPoint(
				"  %s  " % thisMetric,  # use old fashioned format string to make it work in Glyphs 2
				NSPoint(xPosition, yPosition),
				fontSize=10.0 * zoomFactor, # counters the scaling drawTextAtPoint applies
				fontColor=fontColor,
				align=alignment,
			)

	@objc.python_method
	def extremeLayerBezierPathsForFont(self, thisFont):
		if not self.tallestGlyphName or not self.lowestGlyphName:
			self.updateExtremeLayersForFont(thisFont)

		tallestGlyph = thisFont.glyphs[self.tallestGlyphName]
		lowestGlyph = thisFont.glyphs[self.lowestGlyphName]
		tallestLayer = None
		lowestLayer = None

		if not tallestGlyph or not lowestGlyph:
			self.updateExtremeLayersForFont(thisFont)
		else:
			for tallLayer in tallestGlyph.layers:
				if tallestLayer is None: 
					tallestLayer = tallLayer
				elif tallLayer.bounds.origin.y + tallLayer.bounds.size.height > tallestLayer.bounds.origin.y + tallestLayer.bounds.size.height:
					tallestLayer = tallLayer

			for lowLayer in lowestGlyph.layers:
				if lowestLayer is None:
					lowestLayer = lowLayer
				elif lowLayer.bounds.origin.y < lowestLayer.bounds.origin.y:
					lowestLayer = lowLayer

		extremeBeziers = NSBezierPath.bezierPath()
		for extremeLayer in (lowestLayer, tallestLayer):
			if not extremeLayer:
				# print("Extreme Layer empty.") # DEBUG
				continue
			extremeBezier = extremeLayer.completeBezierPath
			if extremeBezier:
				# print("Cannot get bezierPath for %s." % repr(extremeLayer)) # DEBUG
				extremeBeziers.appendBezierPath_(extremeBezier)
		return extremeBeziers

	@objc.python_method
	def updateExtremeLayersForFont(self, thisFont):
		for thisMaster in thisFont.masters:
			self.updateExtremeLayersForMaster(thisMaster)

	@objc.python_method
	def updateExtremeLayersForMaster(self, thisMaster):
		thisFont = thisMaster.font
		mID = thisMaster.id
		lowest, highest = 0, 0
		for thisGlyph in thisFont.glyphs:
			if thisGlyph.export:
				thisLayer = thisGlyph.layers[mID]
				theseBounds = thisLayer.bounds
				if (not self.lowestGlyphName) or theseBounds.origin.y < lowest:
					self.lowestGlyphName = thisGlyph.name
					lowest = theseBounds.origin.y
				if (not self.tallestGlyphName) or (theseBounds.origin.y + theseBounds.size.height) > highest:
					self.tallestGlyphName = thisGlyph.name
					highest = (theseBounds.origin.y + theseBounds.size.height)

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
