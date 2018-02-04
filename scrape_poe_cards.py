#! python3
"""
scrape_poe_cards.py - scrapes poe divination cards from the wiki using the API.
"""

import requests, re, datetime, time, json, os

SCRIPTDIR = os.path.dirname(os.path.abspath(__file__))

# Regex magic! I recommend using https://regex101.com to make it more readable.

regex_wikilinks = re.compile(r'\[\[([^\]\|]*)\]\]|\[\[[^\]\|]*\|([^\]\|]*)\]\]')
"""
matches formats "[[text]]" or "[[wikipage|text]] and stores "text" as capture group 1 or 2, respectively.
[[The Harvest (area)|The Harvest]] -> The Harvest
Sold by [[Zana]] -> Zana
Drops in [[map]]s -> map

Since only one capture group is filled each time, using all together in a replacement like r'\1\2' turns
all match variants into the desired text.
"""

def remove_wiki_formats_dropareas(text):
	if not text:
		return None
	
	text = text.replace('[[', '').replace(']]', '')
	list = text.split(' \u2022 ')
	
	return list


def remove_wiki_formats_droptext(text):
	if not text:
		return None
	
	text = text.replace(']], [[', ']]><[[')
	list = text.split('><')
	# Splitting the text into a list/array without removing the [[ ]] link syntax, so that the regex below has delimiters.
	# Simply splitting on ', ' does not work because there can be entries with a comma in the name.
	for index, entry in enumerate(list):
		list[index] = regex_wikilinks.sub(r'\1\2', entry)	# remove wiki links with regular expression. See the start of the script.
	
	return list


def clean_up_api_results(api_results):
	"""
	Takes the API result and turns it into a list of json objects.
	At this stage the entries are still in the original wiki format, which get removed here.
	"""
	
	#item_names = list(api_results.keys())
	#item_names.sort()
	
	partial_item_list = []
	for result in api_results:
		itemdata = result['title']
		obj = {}
		obj['name'] = itemdata['name']
		
		dropareas = itemdata['drop areas html']		# returns a string, which is a list with ' \u2022 ' as separators.
		if not dropareas:
			dropareas = None
		obj['dropareas'] = remove_wiki_formats_dropareas(dropareas)
		
		droptext = itemdata['drop text']	# returns a string, which CAN be a list with ', ' as separators.
		if not droptext:
			droptext = None
		obj['droptext'] = remove_wiki_formats_droptext(droptext)
		
		partial_item_list.append(obj)
	
	return partial_item_list


def get_api_results(item_category):
	"""
	This function gets the wiki data for given unique item categories.
	It uses the wiki's API and requests json format.
	See this HTML version to get a better idea how the API response is structured:
	https://pathofexile.gamepedia.com/api.php?action=cargoquery&format=json&limit=500&tables=items&fields=name%2Cdrop_areas_html%2Cdrop_text&where=class%3D%22Divination%20Card%22&group_by=items._pageName&formatversion=1
	"""
	
	print('Getting data for ' + item_category)
	r = requests.get('https://pathofexile.gamepedia.com/api.php?action=cargoquery&format=json&limit=500&tables=items&fields=name%2Cdrop_areas_html%2Cdrop_text&where=class%3D%22' + item_category + '%22&group_by=items._pageName&formatversion=1')
	rj = r.json()
	api_results = rj['cargoquery']
	
	return clean_up_api_results(api_results)


def get_wiki_data(item_categories):
	data_list = []
	for category in item_categories:
		data_list.extend(get_api_results(category))
	
	print('')
	return data_list


def convert_to_AHK_script_format(all_data):
	"""
	This function takes the raw API data and converts it into lines that are readable by the PoE ItemInfo Script.
	"""
	
	new_data = []
	for card in all_data:
		line = 'divinationCardList["' + card['name'] + '"] := "'
		
		if card['dropareas']:
			line += 'Drop Locations:'
			loc_map = []
			loc_oldmap = []
			loc_area = []
			for loc in card['dropareas']:
				if re.search('(War for the Atlas)', loc):
					loc_map.append(loc.replace(' (War for the Atlas)', ''))
				elif re.search('(Atlas of Worlds)', loc):
					loc_oldmap.append(loc.replace(' (Atlas of Worlds)', ''))
				else:
					loc_area.append(loc)
			
			loc_additional_old = []
			for loc in loc_oldmap:
				if loc not in loc_map:
					loc_additional_old.append(loc)
			if (loc_map + loc_area):
				line += '`n ' + '`n '.join(loc_map + loc_area)
			else:
				line += '`n No current record. Generic sources like Diviner\'s Strongboxes,`n The Eternal Labyrinth or The Putrid Cloister still apply.'
			
			if loc_additional_old:
				line += '`n`nAdditionally these locations were recorded in 3.0:'
				line += '`n ' + '`n '.join(loc_additional_old)
			
		else:
			if not card['droptext']:
				line += 'No drop information available'
		
		if card['droptext']:
			if card['dropareas']:
				line += '`n`n'
			line += 'Drop Restrictions:'
			for restr in card['droptext']:
				line += '`n ' + restr.strip()
		
		line += '"'
		new_data.append(line)
	
	return new_data


def define_file_header():
	"""
	info headers for DivinationCards.txt

	:return: list
	"""
	data = []
	d = datetime.datetime.now()
	now_time = d.strftime('%Y-%m-%d at %H:%M:%S')
	data.append('; Data from https://pathofexile.gamepedia.com/Path_of_Exile_Wiki using the API.')
	data.append('; Comments can be made with ";", blank lines will be ignored.')
	data.append(';')
	data.append('; This file was auto-generated by scrape_poe_cards.py on {}'.format(now_time) + '\n')
	data.append('divinationCardList := Object()\n')
	data.append('divinationCardList["Unknown Card"] := "Card not recognised or not supported"\n')

	return data


def write_list_to_lines(new_data):
	file = open(SCRIPTDIR + '\\DivinationCardList.txt', 'a+b')  # opens file for writing
	for row in new_data:
		file.write(row.encode('cp1252'))
		file.write(b'\n')
	file.close()


def main():
	item_categories = ['Divination Card']
	open(SCRIPTDIR + '\\DivinationCardList.txt', 'w').close()  # create file (or overwrite it if it exists)
	write_list_to_lines(define_file_header())
	data_list = get_wiki_data(item_categories)
	new_data = convert_to_AHK_script_format(data_list)
	write_list_to_lines(new_data)


startTime = datetime.datetime.now()
main()
print('\nProgram execution time: ',(datetime.datetime.now() - startTime))
