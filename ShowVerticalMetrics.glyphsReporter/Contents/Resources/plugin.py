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

class ShowVerticalMetrics(ReporterPlugin):

	def settings(self):
		self.menuName = Glyphs.localize({'en': u'Vertical Metrics', 'de': u'Vertikalmaße'})
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
		thisMaster = layer.associatedFontMaster()
		heightsAlreadyUsed = []
		xPosition = self.controller.viewPort.origin.x - self.controller.selectedLayerOrigin.x
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
						zoomFactor = self.getScale()
						heightsAlreadyUsed.append(height)
						line = NSBezierPath.bezierPath()
						line.moveToPoint_( NSPoint(-50000, height) )
						line.lineToPoint_( NSPoint(+50000, height) )
						line.setLineWidth_( 1.0/zoomFactor )
						line.setLineDash_count_phase_( [1.0/zoomFactor, 3.0/zoomFactor], 2, 3.5/zoomFactor )
						line.stroke()
					
					self.drawTextAtPoint(
						"  "+thisMetric+"  ", 
						NSPoint(
							(xPosition+80)/zoomFactor, 
							height+2/zoomFactor if "bottom" in alignment else height,
							),
						fontColor=defaultColor,
						align=alignment
						)

