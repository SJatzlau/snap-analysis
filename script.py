import xml.etree.ElementTree as ET
import csv
import os
import sys
import logging
import re
import numpy as np
import matplotlib.pyplot as plt
import warnings


# XXX: What code smells do we track? Dead code -> no hat, tiny vs. massive sprites -> tables, duplicate code -> blocks
# XXX: TODO: look for more code smells, maybe compare block-based smells to text-based ones!

# Ignore Warnings (such as applying log(x) to x = 0
warnings.filterwarnings("ignore")

# Suppress error/debug messages from matplotlib
mpl_logger = logging.getLogger('matplotlib')
mpl_logger.setLevel(logging.WARNING)

# Global variables
logging.basicConfig(filename='debug.log', level=logging.DEBUG, filemode='w')
evt_types = ['receiveGo', 'receiveKey', 'receiveInteraction', 'receiveMessage', 'receiveCondition', 'receiveOnClone']
errors_total = 0
coordlistx = []
coordlisty = []
tools = [
    "label %'text' of size %'size'",  # 1 in Pen

    "empty? %'data'",  # 6 in Variables
    "keep items such that %'pred' from %'data'",
    "combine with %'function' items of %'data'",
    "for each %'item' of %'data' %'action'",
    "numbers from %'from' to %'to'",
    "map %'func' over %'data'",
    "map %'function' over %'lists'",  # Could be necessary

    "if %'test' then %'true' else %'false'",  # 8 in Control
    "for %'i' = %'start' to %'end' %'action'",
    "catch %'tag' %'action'",
    "throw %'cont'",
    "catch %'tag' %'value'",
    "throw %'tag' %'value'",
    "if %'test' do %'action' and pause all $pause-1-255-220-0",
    "ignore %'x'",

    "join words %'words'",  # 6 in Operators
    "list $arrowRight sentence %'data'",
    "sentence $arrowRight list %'text'",
    "word $arrowRight list %'word'",
    "list $arrowRight word %'list'",
    "%'x'",

    "tell %'sprite' to %'action'",  # 2, not tools, but potentially wrongly listed as user-defined
    "ask %'sprite' for %'expression'"
]

# Creating the table for the projects
projectfile = open('projects.csv', 'w')
fieldnames = ['project_id',
              'projectname',
              'number_of_sprites',
              'number_userblocks_global',
              'number_nested_sprites',
              'number_variables_global']
projectwriter = csv.DictWriter(projectfile, fieldnames=fieldnames)
projectwriter.writeheader()

# Creating the table for the sprites
spritefile = open('sprites.csv', 'w')
fieldnames2 = ['project_id',
               'spritename',
               'number_scripts',
               'number_userblocks_spritelocal',
               'number_colortouch',
               'number_sensing',
               'number_localvars',
               'number_events',
               'number_events_unique',
               ]
spritewriter = csv.DictWriter(spritefile, fieldnames=fieldnames2)
spritewriter.writeheader()

# Creating the table for the scripts
scriptfile = open('scripts.csv', 'w')
fieldnames3 = ['project_id',
               'spritename',
               'isComment',
               'hasCommentAttached',
               'x_y_coordinates',
               'number_scriptvars',
               'list_of_blocks',
               'broadcasts_unique_sent',
               'broadcasts_unique_received',
               'is_hat_only',
               'has_hat'
               ]
scriptwriter = csv.DictWriter(scriptfile, fieldnames=fieldnames3)
scriptwriter.writeheader()

# Creating the table for the user-defined blocks
userblockfile = open('userblocks.csv', 'w')
fieldnames4 = ['project_id',
               'projectname',
               'blockname',
               'scope',
               'blocks_contained'
               ]
userblockwriter = csv.DictWriter(userblockfile, fieldnames=fieldnames4)
userblockwriter.writeheader()


# Remove non-ascii-characters from project names --- DONE
def remove_non_ascii(text):
    return ''.join(i for i in text if ord(i) < 128)


# Nesting --- DONE
def analysis_nesting(project):
    anchor_names = set()
    tmp = project.findall(".//*[@anchor]")
    for nest in tmp:
        anchor_names.add(nest.attrib['anchor'])
    return anchor_names


# Event types and total number --- DONE
def analysis_events(object):
    events_total = 0
    events_unique = 0
    events = {}

    for evt_type in evt_types:
        tmp = len(object.findall("./scripts/script/block[@s='" + evt_type + "']"))
        events['event_' + evt_type] = tmp or 0
        events_total += tmp
        if tmp > 0:
            events_unique += 1
    return events_total, events_unique, events


# Touching Color --- DONE
def analysis_colortouch(object):
    colortouchingcolor = len(object.findall(".//block[@s='reportColorIsTouchingColor']"))
    touchingcolor = len(object.findall(".//block[@s='reportTouchingColor']"))

    return colortouchingcolor + touchingcolor


def analysis_clones(root):
    # TODO: Redo this entire thing
    # Clone is considered 'started' if:
    # Name of Sprite A is the input for a createClone or a newClone-Block AND
    # receiveOnClone is found in code of Sprite A

    set_clones_created = set()
    set_clones_started = set()

    # What do we need to find:
    # 1) create clone and report clone: find the sprites used as inputs for these two blocks
    # 1.1) if "myself" used as input, find the sprite that uses that block
    # 2) create clone and report clone in user-defined blocks: find the sprites used as inputs for these blocks
    # 2.1) if "myself" used as input, find the sprite that uses that CUSTOM block
    # figure out: 3) What if input is a parameter that can be chosen by the user?
    # Thoughts: look at 100 sample projects and see if this is ever used. If not, exclude it and say it's an edge
    # case that is unlikely to appear, so we ignore it FOR NOW

    clones_created_and_started = set.intersection(set_clones_created, set_clones_started)
    clones_created_but_not_started = set_clones_created.difference(set_clones_started)
    clones_started_but_not_created = set_clones_started.difference(set_clones_created)

    # print("The clones created and started are: " + str())
    # print("The clones created, but not started are: " + str())
    # print("And finally, the clones started, but never created are: " + str())

    # Return the three sets
    return clones_created_and_started, clones_created_but_not_started, clones_started_but_not_created


# Broadcasts unique --- DONE
def analysis_broadcast_unique(script):
    messages_sent = []

    for x in (script.findall(".//block[@s='doBroadcast']")):
        message_text = x.find('l')
        if type(message_text) is not None:
            messages_sent.append(message_text.text)

    for x in (script.findall(".//block[@s='doBroadcastAndWait']")):
        message_text = x.find('l')
        if type(message_text) is not None:
            messages_sent.append(message_text.text)

    return set(messages_sent)


# Number of sprites --- DONE
def analysis_spritenumber(object):
    return len(object.findall(".//sprite"))


# Analyzing user blocks, returns the number of user-defined blocks, excluding tools, plus a list of them --- DONE
def analysis_user_blocks(object):
    user_defined_blocks_total = object.findall("./blocks/block-definition")

    user_defined_blocks_no_tools = []

    for definition in user_defined_blocks_total:
        tmp = definition.get('s')
        if tmp in tools:
            pass
        else:
            user_defined_blocks_no_tools.append(definition)

    return user_defined_blocks_no_tools


def analysis_user_blocks_contained_blocks(project_id, projectname, userblocklist, scope):
    for element in userblocklist:
        blocks_contained = []
        for block in element.findall(".//block"):
            if block.get('s') is not None:
                blocks_contained.append(block.get('s'))

        userblockwriter.writerow({
            'project_id': project_id,
            'projectname': projectname,
            'blockname': element.get('s'),
            'scope': scope,
            'blocks_contained': blocks_contained
        })


# Spritenames --- DONE
def analysis_spritenames(object):
    sprites_number_standard_names = 0
    spritenames = []
    for sprite in object.findall(".//sprite"):
        name = sprite.get('name')
        if re.match('Sprite', name) is not None:
            sprites_number_standard_names += 1

        spritenames.append(name)

    spritenames.append("Stage: " + object.get('name'))
    return spritenames, sprites_number_standard_names


# Count various sensing blocks --- DONE
def analysis_sensing(object):

    sensing = len(object.findall(".//block[@s='reportTouchingObject']"))
    sensing += len(object.findall(".//block[@s='reportTouchingColor']"))
    sensing += len(object.findall(".//block[@s='reportColorIsTouchingColor']"))
    sensing += len(object.findall(".//block[@s='reportMouseDown']"))
    sensing += len(object.findall(".//block[@s='reportKeyPressed']"))

    return sensing


def drawplots():
    # Heatmap and its legend
    fig, ax = plt.subplots()
    heatmap, xedges, yedges = np.histogram2d(coordlisty, coordlistx, bins=50, range=[[0, 700], [0, 700]])
    # Edges of the heatmap
    extent = [-10, 700, 700, -10]

    # Determining low, mid and high
    low = np.amin(heatmap)
    mid = np.mean(np.extract(heatmap != 0, heatmap))
    high = np.amax(heatmap)

    # Applying the logarithm so the values are normalized
    heatmap = np.log10(heatmap)

    # Showing the heatmap and the colorbar
    cax = ax.imshow(heatmap, extent=extent)
    cbar = fig.colorbar(cax, ticks=[low, mid, high], orientation='horizontal')
    cbar.ax.set_xticklabels(['Low', 'Medium', 'High'])

    # Saving the heatmap
    plt.savefig('heatmap.png', dpi=400)

    # Clear previous plot
    plt.clf()

    # Setting labels
    plt.ylabel('y')
    plt.xlabel('x')

    # Setting x and y limits (same as heatmap!)
    plt.xlim(-10, 700)
    plt.ylim(-10, 700)

    # Invert y-axis so 0 is at top, just like in Snap!
    plt.gca().invert_yaxis()

    # Plot the scatterplot
    plt.scatter(coordlistx, coordlisty, s=1.5, c='b')

    # Saving the scatterplot
    plt.savefig('scatterplot.png', dpi=400)


def checkerrors():
    # If there are any errors, display a warning
    if errors_total > 0:
        print(str(errors_total) + " errors total. Please check debug.log for details.")

    # Even If there aren't any errors, say that in the debug log
    logging.info(str(errors_total) + " errors total.")


def is_comment(script):
    # Catch non-attached comments
    if script.get('collapsed') is not None:
        return True
    else:
        return False


def inherits(inheritance_list):
    for element in inheritance_list:
        if element.text == "scripts":
            return True


def name_of_parent(object):
    parentname = ""
    parentobj = object.find("./inherit")
    if parentobj is not None:
        parentname = parentobj.get('exemplar')

    return parentname


def object_of_parent(object, stage):
    parentobj = object.find("./inherit")
    parentname = ""
    if parentobj is not None:
        parentname = parentobj.get('exemplar')
        for sprite in stage.findall(".//sprite"):
            if sprite.get('name') == parentname:
                return sprite


def analyze_script(script, objectname, ID, spritecoordlistx, spritecoordlisty):
    blocks_used = []
    has_hat = True
    is_hat_only = False
    xpos = ypos = 0
    isComment = is_comment(script)
    hasCommentAttached = False
    length_of_script = len(script.findall(".//block")) + len(script.findall(".//custom-block"))

    if length_of_script == 0:
        has_hat = False
        is_hat_only = False

    # Catch comments attached to the script we're looking at
    if script.find(".//comment") is not None:
        hasCommentAttached = True

    # Take all the blocks used in scripts and add them to blocks_used
    if not isComment:
        tmp = script.findall(".//block") + script.findall(".//custom-block")
        for i in tmp:
            blocks_used.append(i.get('s'))

    # Match the text in the script's first block against
    # the event-strings, no match means script has no hat
    if not isComment:
        x = [script.find("./block"), script.find("./custom-block")]
        x = [a for a in x if a is not None]
        if x[0].get('s') not in evt_types:
            has_hat = False
        else:
            if length_of_script == 1:
                is_hat_only = True

    if not isComment:
        xpos = round(float(script.get('x')), 5)
        ypos = round(float(script.get('y')), 5)
        if ypos < 1000:
            spritecoordlisty.append(ypos)
            spritecoordlistx.append(xpos)

    # Unique broadcast messages sent (as a set)
    broadcasts_unique_sent = analysis_broadcast_unique(script)

    # Unique broadcast messages received (also as a set)
    messages_received = set()
    for x in (script.findall(".//block[@s='receiveMessage']")):
        message_text = x.find('l')
        if type(message_text) is not None:
            messages_received.add(message_text.text)

    scriptwriter.writerow({
        'project_id': ID,
        'spritename': objectname,
        'isComment': isComment,
        'hasCommentAttached': hasCommentAttached,
        'x_y_coordinates': (xpos, ypos),
        'number_scriptvars': len(script.findall("./block[@s='doDeclareVariables']")),
        'list_of_blocks': blocks_used,
        'broadcasts_unique_sent': broadcasts_unique_sent,
        'broadcasts_unique_received': messages_received,
        'is_hat_only': is_hat_only,
        'has_hat': has_hat
    })


def analyze_object(object, ID, nameToUse):
    # XXX: For the future: Determine if a script is really a comment,
    # or contains a comment; if it does, analyze it separately
    number_scripts_in_sprite = 0
    events_total = events_unique = 0

    spritecoordlisty = []
    spritecoordlistx = []

    scripts_in_sprite = object.find(".//scripts")
    if scripts_in_sprite is not None:
        number_scripts_in_sprite += len(scripts_in_sprite)
        for script in scripts_in_sprite:
            analyze_script(script, nameToUse, ID, spritecoordlistx, spritecoordlisty)

        if len(spritecoordlistx) > 0:
            spritecoordlistx = [x - min(spritecoordlistx) for x in spritecoordlistx]
            spritecoordlisty = [y - min(spritecoordlisty) for y in spritecoordlisty]
            coordlistx.extend(spritecoordlistx)
            coordlisty.extend(spritecoordlisty)

        events_total, events_unique, events = analysis_events(object)

        tmp = filter(is_comment, scripts_in_sprite)
        for x in tmp:
            scripts_in_sprite.remove(x)  # Comment-Elements that it found in the scripts

    spritewriter.writerow({
        'project_id': ID,
        'spritename': nameToUse,
        'number_scripts': number_scripts_in_sprite,
        'number_userblocks_spritelocal': len(analysis_user_blocks(object)),
        'number_colortouch': analysis_colortouch(object),
        'number_sensing': analysis_sensing(object),
        'number_localvars': len(object.findall("./variables/variable")),
        'number_events': events_total,
        'number_events_unique': events_unique,
    })


def analyze_project(path, number_so_far, number_total):
    # In R or whatever, check who actually uses those custom blocks
    ref = ET.parse(path)
    root = ref.getroot()
    stage = root.find(".//stage")
    project_id = os.path.split(os.path.dirname(path))[1]
    project_name = remove_non_ascii(root.attrib['name'])

    # Give an estimate of the progress
    if number_so_far % 500 == 0:
        d = (float(number_so_far) / float(number_total)) * 100
        c = round(d, 2)
        b = str(c)
        a = " (" + b + "%)"
        print("Analyzing project " + str(number_so_far) + " of " + str(number_total) + a)

    analyze_object(stage, project_id, "Stage: " + stage.get('name'))
    analysis_user_blocks_contained_blocks(project_id, project_name, analysis_user_blocks(stage), scope='Stage')

    for sprite in stage.findall(".//sprite"):
        inherits_scripts = False
        # See if the sprite is a clone and inherits scripts
        inherit = sprite.findall("./inherit/list/item/")
        if inherit is not None:
            inherits_scripts = inherits(inherit)
        #  If that is the case,
            #  find the parent based on the name and analyze that instead, and use the clone's name
            if inherits_scripts:
                analyze_object(object_of_parent(sprite, stage), project_id, sprite.get('name'))
            else:
                analyze_object(sprite, project_id, sprite.get('name'))

            analysis_user_blocks_contained_blocks(project_id, project_name, analysis_user_blocks(sprite), scope=sprite.get('name'))

    analysis_user_blocks_contained_blocks(project_id, project_name, analysis_user_blocks(root), scope='global')

    projectwriter.writerow({
        'project_id': project_id,
        'projectname': project_name,
        'number_of_sprites': len(stage.findall(".//sprite")),
        'number_userblocks_global': len(analysis_user_blocks(root)),
        'number_nested_sprites': len(analysis_nesting(root)),
        'number_variables_global': len(root.findall("./variables/variable"))
    })


def collect_files(number_of_files):

    # Necessary variables
    number_collected = 0
    global errors_total
    source_dir = os.getcwd() + '/projects'

    # Traverse the projects-folder and open each directory in it
    for projectFolder in os.listdir(source_dir):
        if number_collected > int(number_of_files):
            break
        # Then, for each file, see if it is called 'project.xml'. If it is not, proceed to next file
        for file in os.listdir(source_dir + "/" + projectFolder):
            if not file.endswith('project.xml'):
                continue

            # Otherwise, create the file path for it
            xml_file_path = os.path.join(source_dir + "/" + projectFolder, file)

            try:
                analyze_project(xml_file_path, number_collected, number_of_files)

            # Catch any errors that might occur and log them
            except Exception as err:
                logging.warning('This file could not be read:' + xml_file_path)
                logging.warning(
                    "Error was: {0} \n        ---------------------------------------------".format(err))
                errors_total += 1

            # Either way, increase the number of collected files and write the results
            number_collected += 1

    # Check for errors
    checkerrors()

    # Draw the plots for the analysis
    drawplots()


# Analyze the number of files given as parameter
# If no parameter is given, default to 100
try:
    collect_files(str(sys.argv[1]))
except IndexError:
    collect_files(100)
