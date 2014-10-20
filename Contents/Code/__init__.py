import urllib2, base64, simplejson, time, pyq
json = simplejson

# Static text. 
TEXT_NAME = 'TV-Headend Next Generation'
TEXT_TITLE = 'TV-Headend' 

# Image resources.
ICON_DEFAULT = 'icon-default.png'
ART_DEFAULT = 'art-default.jpg'

ICON_ALLCHANS = R('icon_allchans.png')
ICON_BOUQUETS = R('icon_bouquets.png')

# Other definitions.
PLUGIN_PREFIX = '/video/tvheadend-ng'
debug = True
debug_epg = False 
debug_gn = False
req_api_version = 15

####################################################################################################

def Start():
	ObjectContainer.art = R(ART_DEFAULT)
	HTTP.CacheTime = 1

####################################################################################################

@handler(PLUGIN_PREFIX, TEXT_TITLE, ICON_DEFAULT, ART_DEFAULT)
def MainMenu():
	oc = ObjectContainer(no_cache=True)	

	result = checkConfig()
	if result['status'] == True:
		if debug == True: Log("Configuration OK!")
		oc.title1 = TEXT_TITLE
		oc.header = None
		oc.message = None 
		oc = ObjectContainer(title1=TEXT_TITLE, no_cache=True)
		if Prefs['tvheadend_allchans'] != False:
			oc.add(DirectoryObject(key=Callback(getChannels, title=L('allchans')), title=L('allchans'), thumb=ICON_ALLCHANS))
		if Prefs['tvheadend_tagchans'] != False:
			oc.add(DirectoryObject(key=Callback(getChannelsByTag, title=L('tagchans')), title=L('tagchans'), thumb=ICON_BOUQUETS))
		oc.add(PrefsObject(title=L('preferences')))
	else:
		if debug == True: Log("Configuration error! Displaying error message: " + result['message'])
		oc.title1 = None
		oc.header = L('header_attention')
                oc.message = result['message']
		oc.add(PrefsObject(title=L('preferences')))

	return oc

####################################################################################################

def checkConfig():
	global req_api_version
	result = {
		'status':False,
		'message':''
	}

	if Prefs['tvheadend_user'] != "" and Prefs['tvheadend_pass'] != "" and Prefs['tvheadend_host'] != "" and Prefs['tvheadend_web_port'] != "":
		# To validate the tvheadend connection and api version.
		json_data = getTVHeadendJson('getServerVersion', '')
		if json_data != False:
			if json_data['api_version'] == req_api_version:
				result['status'] = True
				result['message'] = ''
				return result
			else:
				result['status'] = False
				result['message'] = L('error_api_version')
				return result
		else:
			result['status'] = False
			result['message'] = L('error_unknown')
			return result
	else:
		result['status'] = False
		result['message'] = L('error_connection')
		return result

def getTVHeadendJson(apirequest, arg1):
	if debug == True: Log("JSON-Request: " + apirequest)
	api = dict(
		getChannelGrid='api/channel/grid?start=0&limit=999999',
		getEpgGrid='api/epg/grid?start=0&limit=1000',
		getIdNode='api/idnode/load?uuid=' + arg1,
		getServiceGrid='api/mpegts/service/grid?start=0&limit=999999',
		getMuxGrid='api/mpegts/mux/grid?start=0&limit=999999',
		getChannelTags='api/channeltag/grid?start=0&limit=999999',
		getServerVersion='api/serverinfo'
	)

	try:
                base64string = base64.encodestring('%s:%s' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'])).replace('\n', '')
                request = urllib2.Request("http://%s:%s/%s" % (Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], api[apirequest]))
                request.add_header("Authorization", "Basic %s" % base64string)
                response = urllib2.urlopen(request)

                json_tmp = response.read().decode('utf-8')
                json_data = json.loads(json_tmp)
	except Exception, e:
		if debug == True: Log("JSON-Request failed: " + str(e))
		return False
	if debug == True: Log("JSON-Request successfull!")
	return json_data

####################################################################################################

def getEPG():
	json_data = getTVHeadendJson('getEpgGrid','')
	if json_data != False:
		if debug_epg == True: Log("Got EPG: " + json.dumps(json_data))
	else:
		if debug_epg == True: Log("Failed to fetch EPG!")	
	return json_data

def getChannelInfo(uuid, services, json_epg):
	result = {
		'iconurl':'',
		'epg_title':'',
		'epg_description':'',
		'epg_duration':0,
		'epg_start':0,
		'epg_stop':0,
		'epg_summary':'',
	}

	json_data = getTVHeadendJson('getIdNode', uuid)
	if json_data['entries'][0]['params'][2].get('value'):
		result['iconurl'] = json_data['entries'][0]['params'][2].get('value')

	# Check if we have data within the json_epg object.
	if json_epg != False and json_epg.get('events'):
		for epg in json_epg['events']:
			if epg['channelUuid'] == uuid and time.time() > int(epg['start']) and time.time() < int(epg['stop']):
				if epg.get('title'):
					 result['epg_title'] = epg['title'];
				if epg.get('description'):
					 result['epg_description'] = epg['description'];
				if epg.get('duration'):
					result['epg_duration'] = epg['duration']*1000;
				if epg.get('start'):
					result['epg_start'] = time.strftime("%H:%M", time.localtime(int(epg['start'])));
				if epg.get('stop'):
					result['epg_stop'] = time.strftime("%H:%M", time.localtime(int(epg['stop'])));
	return result

####################################################################################################

def getChannelsByTag(title):
	json_data = getTVHeadendJson('getChannelTags', '')
	tagList = ObjectContainer(no_cache=True)

	if json_data != False:
		tagList.title1 = L('tagchans')
		tagList.header = None
		tagList.message = None
		for tag in sorted(json_data['entries'], key=lambda t: t['name']):
			if debug == True: Log("Getting channellist for tag: " + tag['name'])
			tagList.add(DirectoryObject(key=Callback(getChannels, title=tag['name'], tag=tag['uuid']), title=tag['name']))
	else:
		if debug == True: Log("Could not create tagelist! Showing error.")
		tagList.title1 = None
		tagList.header = L('error')
		tagList.message = L('error_request_failed') 

	if debug == True: Log("Count of configured tags within TV-Headend: " + str(len(tagList)))
	if ( len(tagList) == 0 ):
		tagList.header = L('attention')
		tagList.message = L('error_no_tags')
	return tagList 

def getChannels(title, tag=int(0)):
	json_data = getTVHeadendJson('getChannelGrid', '')
	json_epg = getEPG()
	channelList = ObjectContainer(no_cache=True)

	if json_data != False:
		channelList.title1 = title
		channelList.header = None
		channelList.message = None
		for channel in sorted(json_data['entries'], key=lambda t: t['number']):
			if tag > 0:
				tags = channel['tags']
				for tids in tags:
					if (tag == tids):
						if debug == True: Log("Got channel with tag: " + channel['name'])
						chaninfo = getChannelInfo(channel['uuid'], channel['services'], json_epg)
						channelList.add(createTVChannelObject(channel, chaninfo, Client.Product, Client.Platform))
			else:
				chaninfo = getChannelInfo(channel['uuid'], channel['services'], json_epg)
				channelList.add(createTVChannelObject(channel, chaninfo, Client.Product, Client.Platform))
	else:
		if debug == True: Log("Could not create channellist! Showing error.")
		channelList.title1 = None;
		channelList.header = L('error')
		channelList.message = L('error_request_failed')
       	return channelList

####################################################################################################

def addMultiResMediaObjects(vco, vurl, channelname):
	if debug == True: Log("Content will be transcoded/remuxed for client")
	# Create media object for a 576px resolution.
	mo384 = MediaObject(
		container = 'mpegts',
		video_codec = VideoCodec.H264,
		audio_codec = AudioCodec.AAC,
		audio_channels = 2,
		optimized_for_streaming = False,
		video_resolution = 384,
		parts = [PartObject(key = vurl + "&resolution=384")]
	)
	vco.add(mo384)
	if debug == True: Log("Creating MediaObject with vertical resolution: 384")
	if debug == True: Log("Providing Streaming-URL: " + vurl + "&resolution=384")

	# Create media object for a 576px resolution.
	mo576 = MediaObject(
		container = 'mpegts',
		video_codec = VideoCodec.H264,
		audio_codec = AudioCodec.AAC,
		audio_channels = 2,
		optimized_for_streaming = False,
		video_resolution = 576,
		parts = [PartObject(key = vurl + "&resolution=576")]
	)
	vco.add(mo576)
	if debug == True: Log("Creating MediaObject with vertical resolution: 576")
	if debug == True: Log("Providing Streaming-URL: " + vurl + "&resolution=576")

	# Create mediaobjects for hd tv-channels.
	if channelname.endswith('HD'):
		mo768 = MediaObject(
			container = 'mpegts',
			video_codec = VideoCodec.H264,
			audio_codec = AudioCodec.AAC,
			audio_channels = 2,
			optimized_for_streaming = False,
			video_resolution = 768,
			parts = [PartObject(key = vurl + "&resolution=768")]
		)
		mo1080 = MediaObject(
			container = 'mpegts',
			video_codec = VideoCodec.H264,
			audio_codec = AudioCodec.AAC,
			audio_channels = 2,
			optimized_for_streaming = False,
			video_resolution = 1080,
			parts = [PartObject(key = vurl)]
		)
		vco.add(mo768)
		if debug == True: Log("Creating MediaObject with vertical resolution: 768")
		if debug == True: Log("Providing Streaming-URL: " + vurl + "&resolution=768")
		vco.add(mo1080)
		if debug == True: Log("Creating MediaObject with vertical resolution: 1080")
		if debug == True: Log("Providing Streaming-URL: " + vurl + "&resolution=1080")
	return vco

def addRemuxedMediaObjects(vco, vurl):
	monat = MediaObject(
			optimized_for_streaming = False,
			parts = [PartObject(key = vurl)]
		)
	vco.add(monat)
	if debug == True: Log("Creating MediaObject for remuxed streaming")
	if debug == True: Log("Providing Streaming-URL: " + vurl)
	return vco

def addNativeMediaObjects(vco, vurl):
	monat = MediaObject(
			optimized_for_streaming = False,
			parts = [PartObject(key = vurl)]
		)
	vco.add(monat)
	if debug == True: Log("Creating MediaObject for native streaming")
	if debug == True: Log("Providing Streaming-URL: " + vurl)
	return vco

def createTVChannelObject(channel, chaninfo, cproduct, cplatform, container = False):
	if debug == True: Log("Creating TVChannelObject. Container: " + str(container))
	name = channel['name'] 
	icon = ""
	if chaninfo['iconurl'] != "":
		icon = chaninfo['iconurl']
	id = channel['uuid'] 
	summary = ''
	duration = 0

	# Add epg data. Otherwise leave the fields blank by default.
	if chaninfo['epg_title'] != "" and chaninfo['epg_start'] != 0 and chaninfo['epg_stop'] != 0 and chaninfo['epg_duration'] != 0:
		if container == False:
			name = name + " (" + chaninfo['epg_title'] + ") - (" + chaninfo['epg_start'] + " - " + chaninfo['epg_stop'] + ")"
			summary = ""
		if container == True:
			summary = chaninfo['epg_title'] + "\n" + chaninfo['epg_start'] + " - " + chaninfo['epg_stop'] + "\n\n" + chaninfo['epg_description'] 
		duration = chaninfo['epg_duration']
		#summary = '%s (%s-%s)\n\n%s' % (chaninfo['epg_title'],chaninfo['epg_start'],chaninfo['epg_stop'], chaninfo['epg_description'])

	# Build streaming url.
	url_structure = 'stream/channel'
	url_base = 'http://%s:%s@%s:%s/%s/' % (Prefs['tvheadend_user'], Prefs['tvheadend_pass'], Prefs['tvheadend_host'], Prefs['tvheadend_web_port'], url_structure)
	url_transcode = '?mux=mpegts&acodec=aac&vcodec=H264&transcode=1'
	vurl = url_base + id + url_transcode

	# Create raw VideoClipObject.
	vco = VideoClipObject(
		key = Callback(createTVChannelObject, channel = channel, chaninfo = chaninfo, cproduct = cproduct, cplatform = cplatform, container = True),
		rating_key = id,
		title = name,
		summary = summary,
		duration = duration,
		thumb = icon,
	)

	stream_defined = False
	# Decide if we have to stream for native streaming devices or if we have to transcode the content.
	if stream_defined == False and (cproduct == "Plex Home Theater" or cproduct == "PlexConnect"):
		vco = addNativeMediaObjects(vco, url_base + id) 
		stream_defined = True

	if stream_defined == False and Prefs['tvheadend_force_remuxed'] == True:
		vco = addRemuxedMediaObjects(vco, url_base + id + '?mux=mpegts&transcode=1')
		stream_defined = True

	if stream_defined == False and (cplatform == "iOS" or cplatform == "Android"):
		vco = addMultiResMediaObjects(vco, vurl, channel['name'])
		stream_defined = True

	if stream_defined == False and Prefs['tvheadend_force_remuxed'] == False:
		vco = addMultiResMediaObjects(vco, vurl, channel['name'])
		stream_defined = True

	# Log the product and platform which requested a stream.
	if cproduct != None and cplatform != None:
		if debug == True: Log("Created VideoObject for plex product: " + cproduct + " on " + cplatform)
	else:
		if debug == True: Log("Created VideoObject for plex product: UNDEFINED")

	if container:
		return ObjectContainer(objects = [vco])
	else:
		return vco
	return vco
