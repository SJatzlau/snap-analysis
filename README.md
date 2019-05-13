# snap-analysis


HOW TO USE:

1. Put projects to be analyzed into the "projects"-folder.
2. In terminal, use "python3 script.py [number of projects to analyze, default = 100]"
3. Results of analysis will be sorted into the following files:
* debug.log - contains error messages
* heatmap.png - shows RELATIVE coordinates of scripts in projects
* scatterplot.png - shows ABSOLUTE coordinates of scripts in projects
* projects.csv - contains results on project-wide level, i. e.: ID, name, number of sprites, number of globally-visible user-defined blocks, number of (unique) nested sprites, number of globally-visible variables
* sprites.csv - contains results on sprite-wide level, i. e.: ID and name of project it belongs to, number of scripts, number of local user-defined blocks, number of local variables, number of events, number of unique events
* scripts.csv - contains results on script-wide level, i. e.: ID of project and name of sprite it belongs to, whether it's a comment or not, whether it has a comment attached, coordinates, number of script-local variables, list of blocks in the script, unique messages being broadcast from this script, unique messages received in this script, flags on whether it only consist of a hat, or has no hat
* userbocks.csv - contains results on user-defined blocks, i. e.: ID and name of project it belongs to, name given to block, scope (either "global", or name of sprite it belongs to), list of blocks it contains
	

The idea is that because the corresponding IDs and names of projects and sprites are always passed down, the tables can be easily matched using data analysis programs, such as R. 
