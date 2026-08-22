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
import traceback
from GlyphsApp import Glyphs
from GlyphsApp.plugins import ReporterPlugin
from AppKit import NSColor, NSBezierPath, NSAffineTransform, NSPoint, NSMakeRect, NSGraphicsContext

###########################################################################################################
#
#	TEMPORARY DEBUGGING SWITCHES - remove together with the debug code before release.
#
#	DEBUG         prints a report into the Macro window every time the zoom
#	              factor or the scroll position changes.
#	DEBUG_MARKERS draws colored squares at the positions the plug-in computes:
#	                magenta = controller.viewPort.origin
#	                cyan    = controller.selectedLayerOrigin
#	                red     = where each metric name is drawn
#
###########################################################################################################

DEBUG = True
DEBUG_MARKERS = True


class ShowVerticalMetrics(ReporterPlugin):
	lowestGlyphName = None
	tallestGlyphName = None
	lastDebugKeys = {}

	@objc.python_method
	def settings(self):
		if DEBUG:
			print("\n### ShowVerticalMetrics DEBUG BUILD loaded. Glyphs version %s, build %s." % (
				getattr(Glyphs, "versionNumber", "?"), getattr(Glyphs, "buildNumber", "?")))

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

	###########################################################################################################
	#
	#	TEMPORARY DEBUGGING CODE - everything between here and the end marker
	#	can be deleted once the placement of the metric names is sorted out.
	#
	###########################################################################################################

	@objc.python_method
	def debugWanted(self, methodName, throttleKey):
		"""
		True when debugReport() would actually print for this key. Used to skip
		the expensive info gathering on the redraws that get throttled away.
		"""
		if not DEBUG:
			return False
		return self.lastDebugKeys.get(methodName) != throttleKey

	@objc.python_method
	def debugReport(self, methodName, lines, throttleKey=None):
		"""
		Prints a block of debug lines, but only when throttleKey changed since
		the last call for this method, so that the Macro window does not fill up
		with one report per redraw.
		"""
		if not DEBUG:
			return
		if throttleKey is not None and self.lastDebugKeys.get(methodName) == throttleKey:
			return
		self.lastDebugKeys[methodName] = throttleKey
		print("\n--- ShowVerticalMetrics: %s ---" % methodName)
		for line in lines:
			print("    %s" % line)

	@objc.python_method
	def debugCTM(self):
		"""
		Returns (ctm, clipBox) of the current drawing context, or (None, None).
		The CTM tells us which coordinate system we are actually drawing in:
		a == 1.0 means view coordinates (screen pixels),
		a == zoomFactor means layer (em unit) coordinates.
		"""
		try:
			from Quartz import CGContextGetCTM, CGContextGetClipBoundingBox
			cgContext = NSGraphicsContext.currentContext().CGContext()
			return CGContextGetCTM(cgContext), CGContextGetClipBoundingBox(cgContext)
		except:
			return None, None

	@objc.python_method
	def debugContextInfo(self):
		"""Describes the graphics context we are drawing into."""
		info = []
		try:
			info.append("NSGraphicsContext: %s" % NSGraphicsContext.currentContext())
		except Exception as e:
			info.append("NSGraphicsContext: FAILED (%s)" % e)
		ctm, clipBox = self.debugCTM()
		if ctm is None:
			info.append("CTM: unavailable")
		else:
			info.append("CTM: a=%.5f b=%.5f c=%.5f d=%.5f tx=%.2f ty=%.2f" % (
				ctm.a, ctm.b, ctm.c, ctm.d, ctm.tx, ctm.ty))
			info.append("clip box: x=%.2f y=%.2f w=%.2f h=%.2f" % (
				clipBox.origin.x, clipBox.origin.y, clipBox.size.width, clipBox.size.height))
		return info

	@objc.python_method
	def debugViewInfo(self):
		"""Describes the controller and the graphic view."""
		info = []
		controller = getattr(self, "controller", None)
		info.append("self.controller: %s" % controller)
		for attribute in ("viewPort", "bounds", "selectedLayerOrigin", "scale"):
			try:
				info.append("controller.%s = %s" % (attribute, getattr(controller, attribute)))
			except Exception as e:
				info.append("controller.%s FAILED (%s)" % (attribute, e))
		try:
			graphicView = controller.graphicView()
			info.append("graphicView: %s" % graphicView)
			for method in ("scale", "activePosition", "visibleRect", "frame", "bounds", "isFlipped", "activeLayer"):
				try:
					info.append("graphicView.%s() = %s" % (method, getattr(graphicView, method)()))
				except Exception as e:
					info.append("graphicView.%s() FAILED (%s)" % (method, e))
		except Exception as e:
			info.append("graphicView FAILED (%s)" % e)
		return info

	@objc.python_method
	def debugMarkerSize(self):
		"""
		A marker edge length of roughly 10 screen pixels, whichever coordinate
		system we happen to be drawing in.
		"""
		ctm, clipBox = self.debugCTM()
		if ctm is None or abs(ctm.a) < 0.00001:
			return 10.0
		return 10.0 / abs(ctm.a)

	@objc.python_method
	def debugMarker(self, position, color):
		"""Draws a square at position, so we can see where a point really lands."""
		if not DEBUG_MARKERS:
			return
		try:
			size = self.debugMarkerSize()
			color.set()
			NSBezierPath.fillRect_(NSMakeRect(
				position.x - size / 2, position.y - size / 2, size, size))
		except:
			pass

	###########################################################################################################
	#
	#	END OF TEMPORARY DEBUGGING CODE
	#
	###########################################################################################################

	@objc.python_method
	def background(self, layer=None):
		"""
		Draws the metric lines in layer (em unit) coordinates.
		The metric names are drawn in backgroundInViewCoords() instead,
		because they must not move when the user zooms.
		"""
		try:
			self.drawMetricLines(layer)
		except:
			print("\nShowVerticalMetrics: background() FAILED:\n%s" % traceback.format_exc())

	@objc.python_method
	def backgroundInViewCoords(self, layer=None):
		"""
		Draws the metric names. This happens in view coordinates (screen pixels
		relative to the Edit view) rather than in em units, so the names keep a
		fixed distance from the left border of the viewport at every zoom stage.
		"""
		try:
			self.drawMetricNames(layer)
		except:
			print("\nShowVerticalMetrics: backgroundInViewCoords() FAILED:\n%s" % traceback.format_exc())

	@objc.python_method
	def drawMetricLines(self, layer=None):
		zoomFactor = self.getScale()
		wantDebug = self.debugWanted("background (metric lines)", zoomFactor)
		debugLines = []
		if wantDebug:
			debugLines = [
				"layer argument: %s" % (layer,),
				"self.getScale() = %s" % zoomFactor,
			]
			debugLines.extend(self.debugContextInfo())

		if layer is None:
			layer = self.currentLayer()
			debugLines.append("currentLayer() = %s" % (layer,))
		if not layer:
			debugLines.append(">>> BAILING OUT: no layer <<<")
			self.debugReport("background (metric lines)", debugLines, throttleKey=zoomFactor)
			return
		thisMaster = layer.associatedFontMaster()
		if not thisMaster:
			debugLines.append(">>> BAILING OUT: no associated font master <<<")
			self.debugReport("background (metric lines)", debugLines, throttleKey=zoomFactor)
			return

		self.metricColor().set()

		metrics = self.metricsForMaster(thisMaster)
		debugLines.append("metrics found: %s" % len(metrics))
		for thisMetric, height, alignment, isFirstAtThisHeight in metrics:
			debugLines.append("  %s: height=%s align=%s line=%s" % (
				thisMetric, height, alignment, isFirstAtThisHeight))
			if not isFirstAtThisHeight:
				continue
			line = NSBezierPath.bezierPath()
			line.moveToPoint_(NSPoint(-50000, height))
			line.lineToPoint_(NSPoint(+50000, height))
			line.setLineWidth_(1.0 / zoomFactor)
			line.setLineDash_count_phase_([1.0 / zoomFactor, 3.0 / zoomFactor], 2, 3.5 / zoomFactor)
			line.stroke()

		self.debugReport("background (metric lines)", debugLines, throttleKey=zoomFactor)

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

	@objc.python_method
	def drawMetricNames(self, layer=None):
		zoomFactor = self.getScale()
		wantDebug = self.debugWanted("backgroundInViewCoords (metric names)", zoomFactor)
		debugLines = []
		if wantDebug:
			debugLines = [
				"layer argument: %s" % (layer,),
				"self.getScale() = %s" % zoomFactor,
			]
			debugLines.extend(self.debugContextInfo())
			debugLines.extend(self.debugViewInfo())

		if zoomFactor < 0.07: # only display names when zoomed in enough
			debugLines.append(">>> BAILING OUT: zoomFactor %s < 0.07, no names drawn <<<" % zoomFactor)
			self.debugReport("backgroundInViewCoords (metric names)", debugLines, throttleKey=zoomFactor)
			return

		if layer is None:
			layer = self.currentLayer()
			debugLines.append("currentLayer() = %s" % (layer,))
		if not layer:
			debugLines.append(">>> BAILING OUT: no layer <<<")
			self.debugReport("backgroundInViewCoords (metric names)", debugLines, throttleKey=zoomFactor)
			return
		thisMaster = layer.associatedFontMaster()
		if not thisMaster:
			debugLines.append(">>> BAILING OUT: no associated font master <<<")
			self.debugReport("backgroundInViewCoords (metric names)", debugLines, throttleKey=zoomFactor)
			return

		fontColor = self.metricColor()

		# left window border plus a fixed pixel margin, no division by the zoom factor:
		viewPortOrigin = self.controller.viewPort.origin
		xPosition = viewPortOrigin.x + 80
		# em units are the only thing that still needs to be scaled into view coordinates:
		layerOrigin = self.controller.selectedLayerOrigin
		yOrigin = layerOrigin.y

		fontSize = 10.0 * zoomFactor
		debugLines.append("xPosition = viewPort.origin.x + 80 = %s" % xPosition)
		debugLines.append("yOrigin = selectedLayerOrigin.y = %s" % yOrigin)
		debugLines.append("fontSize = 10 * zoomFactor = %s" % fontSize)
		debugLines.append("debug marker size = %s" % self.debugMarkerSize())

		# markers for the two reference points:
		self.debugMarker(viewPortOrigin, NSColor.magentaColor())
		self.debugMarker(layerOrigin, NSColor.cyanColor())

		metrics = self.metricsForMaster(thisMaster)
		debugLines.append("metrics found: %s" % len(metrics))
		if not metrics:
			debugLines.append(">>> NOTHING TO DRAW: master has no vertical metric parameters <<<")

		for thisMetric, height, alignment, isFirstAtThisHeight in metrics:
			yPosition = yOrigin + height * zoomFactor
			if "bottom" in alignment:
				yPosition += 2 # keep the name clear of the metric line

			textPosition = NSPoint(xPosition, yPosition)
			debugLines.append("  %s: height=%s align=%s -> drawing at (%.2f, %.2f)" % (
				thisMetric, height, alignment, textPosition.x, textPosition.y))

			self.debugMarker(textPosition, NSColor.redColor())

			try:
				self.drawTextAtPoint(
					"  %s  " % thisMetric,  # use old fashioned format string to make it work in Glyphs 2
					textPosition,
					fontSize=fontSize, # counters the scaling drawTextAtPoint applies
					fontColor=fontColor,
					align=alignment,
				)
			except:
				debugLines.append("  >>> drawTextAtPoint FAILED: %s" % traceback.format_exc())

		self.debugReport("backgroundInViewCoords (metric names)", debugLines, throttleKey=zoomFactor)

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
