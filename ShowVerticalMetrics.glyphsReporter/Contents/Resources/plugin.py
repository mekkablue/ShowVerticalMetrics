# encoding: utf-8

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


from GlyphsApp.plugins import *
from GlyphsApp import GSLayer
	
class ShowVerticalMetrics(ReporterPlugin):
	lowestGlyphName = None
	tallestGlyphName = None
	
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': u'Vertical Metrics',
			'de': u'Vertikalmaße',
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
		
	def background(self, layer):
		# define color:
		defaultColor = NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.4, 0.8, 0.4, 1 )
		if Glyphs.defaults["com.mekkablue.ShowVerticalMetrics.color"]:
			rgba = [
				defaultColor.redComponent(),
				defaultColor.greenComponent(),
				defaultColor.blueComponent(),
				defaultColor.alphaComponent(),
			]
			colorpref = Glyphs.defaults["com.mekkablue.ShowVerticalMetrics.color"].split(",")
			for i in range( min( 4, len(colorpref) ) ):
				try:
					colorvalue = float( colorpref[i].strip() )
					if colorvalue > 1.0:
						colorvalue /= 100.0
					rgba[i] = colorvalue % 1.0
				except:
					print "\nWarning: could not convert '%s' into %s value." % (colorpref[i], ("red","green","blue","alpha")[i])
					print "com.mekkablue.ShowVerticalMetrics.color takes comma-separated numbers between 0.0 and 1.0 (or 0 and 100)."
			defaultColor = NSColor.colorWithRed_green_blue_alpha_( rgba[0], rgba[1], rgba[2], rgba[3] )
		defaultColor.set()
		
		# draw vertical metrics:
		thisMaster = layer.associatedFontMaster()
		heightsAlreadyUsed = []
		
		# query current view settings:
		zoomFactor = self.getScale()
		xPosition = self.controller.viewPort.origin.x - self.controller.selectedLayerOrigin.x
		shiftToWindowBorder = xPosition / zoomFactor
		
		if thisMaster:
			for thisMetric in self.verticalMetrics:
				height = thisMaster.customParameters[thisMetric]
				if height:
					if thisMetric == "winDescent":
						height *= -1

					alignment = "bottomright"
					if height in heightsAlreadyUsed:
						alignment = "topright"
						if "win" in thisMetric:
							alignment = "bottomleft"
					else:
						heightsAlreadyUsed.append(height)
						line = NSBezierPath.bezierPath()
						line.moveToPoint_( NSPoint(-50000, height) )
						line.lineToPoint_( NSPoint(+50000, height) )
						line.setLineWidth_( 1.0/zoomFactor )
						line.setLineDash_count_phase_( [1.0/zoomFactor, 3.0/zoomFactor], 2, 3.5/zoomFactor )
						line.stroke()
					
					# draw metric names:
					if zoomFactor >= 0.07: # only display names when zoomed in enough
						self.drawTextAtPoint(
							"  "+thisMetric+"  ", 
							NSPoint(
								(xPosition+80)/zoomFactor, 
								height+2/zoomFactor if "bottom" in alignment else height,
								),
							fontColor=defaultColor,
							align=alignment
							)
					
			# draw tallest and lowest glyphs:
			if False: #Glyphs.defaults["com.mekkablue.ShowVerticalMetrics.displayExtremeGlyphs"]:
				extremeBezierPaths = self.extremeLayerBezierPathsForFont( thisMaster.font() )
				
				if extremeBezierPaths:
					# shift to the left side
					try:
						lsbShift = extremeBezierPaths.bounds().origin.x/zoomFactor
					except:
						lsbShift = 0
					shift = NSAffineTransform.transform()
					shift.translateXBy_yBy_(shiftToWindowBorder-lsbShift,0)
					extremeBezierPaths.transformUsingAffineTransform_(shift)
					
					# draw outline:
					NSColor.colorWithRed_green_blue_alpha_(1.0, 0.1, 0.3, 0.2).set()
					if zoomFactor >= 0.07:
						extremeBezierPaths.setLineWidth_( 1.0/zoomFactor )
						extremeBezierPaths.stroke()
					else:
						extremeBezierPaths.fill()
				else:
					pass
					# print "No extreme paths drawn." # DEBUG
						
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
				elif tallLayer.bounds.origin.y+tallLayer.bounds.size.height > tallestLayer.bounds.origin.y+tallestLayer.bounds.size.height:
					tallestLayer = tallLayer
		
			for lowLayer in lowestGlyph.layers:
				if lowestLayer is None:
					lowestLayer = lowLayer
				elif lowLayer.bounds.origin.y < lowestLayer.bounds.origin.y:
					lowestLayer = lowLayer
		
		extremeBeziers = NSBezierPath.bezierPath()
		for extremeLayer in (lowestLayer, tallestLayer):
			if extremeLayer:
				extremeBezier = extremeLayer.completeBezierPath
				if extremeBezier:
					extremeBeziers.appendBezierPath_(extremeBezier)
				else:
					pass
					# print "Cannot get bezierPath for %s." % repr(extremeLayer) # DEBUG
			else:
				pass
				# print "Extreme Layer empty." # DEBUG
			
		return extremeBeziers
	
	def updateExtremeLayersForFont(self, thisFont):
		for thisMaster in thisFont.masters:
			self.updateExtremeLayersForMaster(thisMaster)
	
	def updateExtremeLayersForMaster(self, thisMaster):
		thisFont = thisMaster.font()
		mID = thisMaster.id
		lowest, highest = 0, 0
		for thisGlyph in thisFont.glyphs:
			if thisGlyph.export:
				thisLayer = thisGlyph.layers[mID]
				theseBounds = thisLayer.bounds
				if (not self.lowestGlyphName) or theseBounds.origin.y < lowest:
					self.lowestGlyphName = thisGlyph.name
					lowest = theseBounds.origin.y
				if (not self.tallestGlyphName) or (theseBounds.origin.y+theseBounds.size.height) > highest:
					self.tallestGlyphName = thisGlyph.name
					highest = (theseBounds.origin.y+theseBounds.size.height)
