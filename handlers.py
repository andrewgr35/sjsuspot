import models
import riot_utils
import webapp2
import json
import logging
import datetime
import time
from types import *

from google.appengine.api import users

''' This converts UTC to PST time '''
class Pacific_tzinfo(datetime.tzinfo):
    """Implementation of the Pacific timezone."""
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-8) + self.dst(dt)

    def _FirstSunday(self, dt):
        """First Sunday on or after dt."""
        return dt + datetime.timedelta(days=(6-dt.weekday()))

    def dst(self, dt):
        # 2 am on the second Sunday in March
        dst_start = self._FirstSunday(datetime.datetime(dt.year, 3, 8, 2))
        # 1 am on the first Sunday in November
        dst_end = self._FirstSunday(datetime.datetime(dt.year, 11, 1, 1))

        if dst_start <= dt.replace(tzinfo=None) < dst_end:
            return datetime.timedelta(hours=1)
        else:
            return datetime.timedelta(hours=0)
    def tzname(self, dt):
        if self.dst(dt) == datetime.timedelta(hours=0):
            return "PST"
        else:
            return "PDT"


"""
    This is the C part of MVC. Put all logic for controllers here. Url
    patterns will map to controllers defined in this module.
"""

# mappings for /
class HomeHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.response.write(riot_utils.render_template('templates/home.html', {
                'user': user,
                'test': 'loof'
            }))
        else:
            self.redirect(users.create_login_url(self.request.uri))

# mappings for /session/new
class NewSessionHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.response.write(riot_utils.render_template('templates/new_session.html', {}))
        else:
            self.redirect(users.create_login_url(self.request.uri))

    def post(self):
        user = users.get_current_user()
        observee = self.request.get('observee')
        course = self.request.get('course')
        location = self.request.get('location')

        if not user:
            self.response.write(json.dumps({'error': 'You must be logged in'}))
        if observee is None or not len(observee):
            self.response.write(json.dumps({'error': 'You must specify an observee'}))

        # checks pass, create new session
        session = models.Session(observee=observee, observer=user.email(), date=datetime.datetime.now())
        session.course = course
        session.location = location

        session.put()
        self.response.write(json.dumps({'session_id': session.key().id()}))

# mappings for /sessions
class SessionListHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            sessions = models.get_sessions_for_user(user)
	    sessions.sort(key=lambda x: x.date)
	    
	    # Convert from UTC to PST
	    for session in sessions:
		date_utc = session.date
		date_pst = datetime.datetime.fromtimestamp(time.mktime(date_utc.timetuple()), Pacific_tzinfo())
		session.date = date_pst
		session.put()
		
            self.response.write(riot_utils.render_template('templates/sessions.html', {
                'sessions': sessions
            }))
        else:
            self.redirect(users.create_login_url(self.request.uri))

# mappings for /session/id
class SessionHandler(webapp2.RequestHandler):
    def get(self, sessionId):
        user = users.get_current_user()
	
	#Code to package a grid to send to session template 
	grid_dimension = 10
	Num_students = grid_dimension**2
	student_list = []
	student_grid = []
	for i in range(0,Num_students):
	    student_list.append('Student '+str(i+1))    
	grid_counter = 0
	for i in range(0,grid_dimension):
	    grid_entry = []
	    for j in range(0,grid_dimension):
		grid_entry.append(student_list[grid_counter])
		grid_counter += 1
	    student_grid.append(grid_entry)
	# End code to package a grid to send to session template
	
        if user:
            session = models.Session.get_by_id(int(sessionId))
            if session and user.email() == session.observer:
                query = models.InteractionGroup.all()
                interactionGroups = query.run()
                interactions = []
		choral_response = []

                for interaction in interactionGroups:
                    interactionItems = models.InteractionItem.all().order("order").ancestor(interaction).fetch(1000)
                    interactions.append(InteractionGroupItems(interaction, interactionItems))
		    for item in interactionItems:
			if item.name == "Small group time":
			    groupId = item.parent().key().id()
			    itemId = item.key().id()
			    color = item.color
			    sg_time = [groupId,itemId,color]
			    
                self.response.write(riot_utils.render_template('templates/session.html', {
                    'session': session,
                    'interactions': interactions,
		    'students': student_grid,
		    'sg_time': sg_time
		    
                }))
            else:
                self.response.write({'error': 'invalid session id'})
        else:
            self.redirect(users.create_login_url(self.request.uri))


# /session/record/{sessionId} mapping
class SessionRecordHandler(webapp2.RequestHandler):
    def post(self, sessionId):
        user = users.get_current_user()
        if user:
            session = models.Session.get_by_id(int(sessionId))
            if not session:
                self.response.write({'error': 'no session with id: ' + sessionId})
                return
            if not session.observer == user.email():
                self.response.write({'error': 'not authorized'})
                return

            # checks pass
            models.deactivate_active_records_for_session(session)
            groupId = self.request.get('groupId')
            itemId = self.request.get('itemId')
	    actor = self.request.get('actor')
	    mode = self.request.get('mode')
	    color = self.request.get('color')

	    
            if is_blank(groupId):
                self.response.write({'error': 'You must provide an interaction group id'})
                return
            if is_blank(itemId):
                self.response.write({'error': 'You must provide an interaction item id'})
                return

            interactionItem = models.get_interaction_item(int(groupId), int(itemId))
            if interactionItem is None:
                self.response.write({'error': 'No iteraction item with groupId: ' + groupId +
                                              ' and itemId: ' + itemId})

            models.activate_session_record(session, interactionItem, mode, actor, color)
            self.response.write({'success': True})
        else:
            self.response.write({'error': 'must be logged in'})


# /session/stop/{sessionId} mapping
class StopSessionHandler(webapp2.RequestHandler):
    def post(self, sessionId):
        user = users.get_current_user()
        if user:
            session = models.Session.get_by_id(int(sessionId))
	    numstud = self.request.get('numstud')
	    if numstud == '':
		numstud = 0
	    session.numstud = int(numstud)
            session.put()
            if not session:
                self.response.write({'error': 'no session with id: ' + sessionId})
                return
            if not session.observer == user.email():
                self.response.write({'error': 'not authorized'})
                return
            # checks pass
            models.deactivate_active_records_for_session(session)

        else:
            self.response.write({'error': 'must be logged in'})


# mappings for /session/records/{sessionId}
class SessionRecordListHandler(webapp2.RequestHandler):
    def get(self, sessionId):
        user = users.get_current_user()
        if user:
            session = models.Session.get_by_id(int(sessionId))
            if session and session.observer == user.email():
                session_records = models.SessionRecord.all().ancestor(session).fetch(1000)
		session_records.sort(key=lambda x: x.startTime)
		
		# Check to see if a note was placed, if not, insert a default placeholder value
		if isinstance(session.notes, NoneType) == True:
		    session.notes = ''
		    session_notes = ["No Comments$$N/A"]
		else:
		# Split session.notes string into separate entries (all notes are stored in ONE string)
		    session_notes = session.notes.split("##")
		for i in range(0, len(session_notes)):
		    session_notes[i] = session_notes[i].split("$$")
		    
                for sr in session_records:
                    sr.totalSeconds = sr.endTime - sr.startTime
                self.response.write(riot_utils.render_template('templates/session_records.html', {
                    'session': session,
                    'session_records': session_records,
		    'session_notes': session_notes		    
                }))
            else:
                self.response.write({'error': 'invalid session id'})
        else:
            self.redirect(users.create_login_url(self.request.uri))


# mappings for /interactions
class InteractionListHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            query = models.InteractionGroup.all()
            interactionGroups = query.run()
            interactions = []
            for interaction in interactionGroups:
                interactionItems = models.InteractionItem.all().ancestor(interaction).fetch(1000)
                interactions.append(InteractionGroupItems(interaction, interactionItems))

            self.response.write(riot_utils.render_template('templates/interactions.html', {
                'user': user,
                'interactions': interactions
            }))
        else:
            self.redirect(users.create_login_url(self.request.uri))


# mappings for /interaction/group/new
class InteractionHandler(webapp2.RequestHandler):
    def post(self):
        name = self.request.get('name')
        results = models.get_interaction_group_by_name(name)
        print results.__dict__
        if len(list(results)):
            self.response.write(json.dumps({'error': 'Interaction group with name: ' + name + ' already exists'}))
        else:
            ig = models.InteractionGroup(name=name, color=color)
            ig.put()
            self.response.write(json.dumps(ig.__dict__))


# mappings for /interaction/item/new
class InteractionItemHandler(webapp2.RequestHandler):
    def post(self):
        parentId = self.request.get('parentId')
        name = self.request.get('name')
        if parentId is None or not len(parentId):
            self.response.write({'error': 'You must specify the parent id'})
            return
        if name is None or not len(name):
            self.response.write({'error': 'You must specify a name'})

        # grab parent interaction group
        parentGroup = models.InteractionGroup.get_by_id(int(parentId))
        if parentGroup is None:
            self.response.write({'error': 'No group with id ' + parentId})
        else:
            item = models.InteractionItem(parent=parentGroup, name=name)
            item.put()
            self.response.write(json.dumps({"success": True}))

#class CsvHandler(webapp2.RequestHandler):
class CsvHandler(webapp2.RequestHandler):
    def get(self, sessionId):
        user = users.get_current_user()
        if user:
            session = models.Session.get_by_id(int(sessionId)) 
            if session and session.observer == user.email():
                session_records = models.SessionRecord.all().ancestor(session).fetch(1000)
                for sr in session_records:
                    sr.totalSeconds = sr.endTime - sr.startTime

                self.response.write(riot_utils.render_template('templates/csv_export.html', {
                    'session': session,
                    'session_records': session_records
                }))
            else:
                self.response.write({'error': 'invalid session id'})
        else:
            self.redirect(users.create_login_url(self.request.uri))
    
 # mappings for /interaction/group/remove
class InteractionRemoveHandler(webapp2.RequestHandler):
    def post(self):
        name = self.request.get('removeName')
        results = models.get_interaction_group_by_name(name)
        print results.__dict__
        if len(list(results)):
            models.remove_interaction_group_by_name(name)
            self.response.write(json.dumps({"success": True}))
        else:
            self.response.write(json.dumps({'error': 'Interaction group with name: ' + name + ' does not exist'}))
 # mappings for /interaction/item/remove

class RemoveInteractionItemHandler(webapp2.RequestHandler):
    def post(self):
        name = self.request.get('removeInteractionItemName')
        results = models.get_interaction_item_by_name(name)
        print results.__dict__
        if len(list(results)):
            models.remove_interaction_item_by_name(name)
            self.response.write(json.dumps({"success": True}))
        else:
            self.response.write(json.dumps({'error': 'Interaction group with name: ' + name + ' does not exist'}))
class LoadDefualtInteractionHandler(webapp2.RequestHandler):
    def post(self):
	#List of groups
	groups = ["Whole Group","Individual","Small group/ pairs","Teacher Actions"]
	
	# List of interactions (for each group)
	interactions = [[("Asking a question","btn-lightgreen"),("Answering a question","btn-green"),("Contributes an idea","btn-darkgreen"),("Student presentation","btn-blue"),("Other (please describe in notes)","btn-grey"),("Shout out","btn-success"),("Choral response","btn-success")],
	                [("Informal assessment (clickers)","btn-green"),("Observing phenomenon/ video","btn-lightblue"),("Writing","btn-grey"), ("Reading","btn-grey"),("Problem solving","btn-grey"),("Other (please describe in notes)","btn-grey")],
	                [("Small group time", "btn-blue"),("Discussion with peers","btn-green"),("Observing phenomenon","btn-lightblue"),("Explaining (student presentation)","btn-blue"),("Building/Manipulating","btn-lightpurple"),("Problem solving","btn-lightpurple"),("Reading","btn-grey")],
	                [("Explaining","btn-red"),("Clarifying instruction","btn-orange"),("Asking closed question","btn-green"),("Asking open question","btn-lightgreen"),("Waiting","btn-purple"),("Presenting a Demo or Video","btn-lightblue")]]
	
	#zip up interactions and groups, this makes it easy to loop through and place the interactions into their corresponding groups
	igzip = zip(groups,interactions)
	
	#loop through and place interactions/groups into server database
	for entry in igzip:
	    group = entry[0]
	    interactions = entry[1][0]
	    results = models.get_interaction_group_by_name(group)
	    print results.__dict__
	    if len(list(results)):
		self.response.write(json.dumps({'error': 'Interaction group with name: ' + group + ' already exists'}))
	    else:
		ig = models.InteractionGroup(name=group)
		ig.put()
		parentGroup = ig
		counter = 0
		for interaction in entry[1]:
		    item = models.InteractionItem(parent=parentGroup, name=interaction[0],color=interaction[1], order=counter+1)
		    item.put()
		    counter += 1      
        self.response.write(json.dumps({"success": True}))

class RemoveAllGroupHandler(webapp2.RequestHandler):
    def post(self):
	user = users.get_current_user()
        if user:
            query = models.InteractionGroup.all()
            interactionGroups = query.run()
	    for interaction in interactionGroups:
		models.remove_interaction_group_by_name(interaction.name)
            self.response.write(json.dumps({"success": True}))
    
class SessionNoteHandler(webapp2.RequestHandler):
    def post(self, sessionId):
	user = users.get_current_user()
        if user:
	    session = models.Session.get_by_id(int(sessionId))
	    session_note = self.request.get('note')
	    session_time = self.request.get('time')
	    if isinstance(session.notes, NoneType) == True:
		session.notes = ''
	    session.notes += str(session_note)
	    session.notes += "$$"
	    session.notes += str(session_time)
	    session.notes += "##"	    
	    if not session:
		self.response.write({'error': 'no session with id: ' + sessionId})
		return
	    if not session.observer == user.email():
		self.response.write({'error': 'not authorized'})
		return
	    # checks pass
	    session.put()
	else:
	    self.response.write({'error': 'must be logged in'})	
	    
# mapping for session/count handler	    
class StudentCountHandler(webapp2.RequestHandler):
    def post(self, sessionId):
	user = users.get_current_user()
        if user: 
	    session = models.Session.get_by_id(int(sessionId))
	    student_id = self.request.get('actor')
	    
	    # The code below stores student participation counts in a dictionary data structure
	    if session.studentcounts:
		if student_id in session.studentcounts:
		    session.studentcounts[student_id] += 1
		else:
		    session.studentcounts[student_id] = 1
	    else: 
		session.studentcounts = {}
		session.studentcounts[student_id] = 1

	    if not session:
		self.response.write({'error': 'no session with id: ' + sessionId})
		return
	    if not session.observer == user.email():
		self.response.write({'error': 'not authorized'})
		return
	    # checks pass
	    session.put()
	else:
	    self.response.write({'error': 'must be logged in'})	

# mapping for session/charts/ 
class SessionChartsHandler(webapp2.RequestHandler):
    def get(self, sessionId):
	user = users.get_current_user()
        if user: 
	    session = models.Session.get_by_id(int(sessionId)) 
	    session_count_array = []
	    for i in range(1,101):
		if ('Student' + ' '+ str(i) ) in session.studentcounts:
		    session_count_array.append( ( ( session.studentcounts[ ('Student' + ' '+ str(i) ) ] ), 'btn-black' ) )
		else:
		    session_count_array.append((0,'btn-grey'))
	    session_count_map = []
	    for i in range(0,100,10):
		session_count_map.append( (session_count_array[i:i+10] ) )

	    if session and session.observer == user.email():
		session_records = models.SessionRecord.all().ancestor(session).fetch(1000)
		session_records.sort(key = lambda x:x.startTime)
		session_start = session_records[0].startTime
		session_end = session_records[-1].endTime
		session_dur = session_end - session_start	
		student_counts = session.studentcounts
		
		color_map = {} #Create the color mappings, for converting names like btn-red to hex codes for plotting
		color_map["btn-grey"] = "#a5a5a5"
		color_map["btn-blue"] = "#0084cc"
		color_map["btn-lightblue"] = "#bbd5dc"
		color_map["btn-green"] = "#5e933d"
		color_map["btn-darkgreen"] = "#435a3e"
		color_map["btn-lightgreen"] = "#92bc89"
		color_map["btn-red"] = "#f40000"
		color_map["btn-orange"] = "#e58900"
		color_map["btn-yellow"] = "#e4e11f"
		color_map["btn-black"] = "#000000"
		color_map["btn-purple"] = "#dc18b5"
		color_map["btn-lightpurple"] = "#d7a8ff"
		color_map["btn-success"] = "#62c462"
		
		# These lists below are for timelines
		student_actions = []
		student_colors = []
		teacher_actions = []
		teacher_colors = []
		ind_student_actions = []
		
		# These are for pie charts (dictionaries/arrays)
		mode_dict = {}
		mode_plot = []
		student_activity = {}
		student_activity_plot = []
		teacher_activity = {}
		teacher_activity_plot = []
		
		# Create dict for time spent between student/teacher
		student_teacher = {}
		student_teacher["Teacher"] = 0
		student_teacher["Students"] = 0
		student_teacher_plot = []
		
		# Create student participation array for pie chart
		student_plot = []
		for item in student_counts:
		    student_plot.append([item,student_counts[item]])
		    
		session_start = session_records[0].startTime
		counter = 0
		for sr in session_records:
		    # Get relevant information from each session record
		    int_start = sr.startTime - session_start
		    int_end = sr.endTime - session_start
		    int_dur = str(int_start)+'-'+str(int_end)+' s'
		    total_seconds = sr.endTime - sr.startTime
		    int_item = sr.interactionItem.name
		    actor = sr.actor
		    mode = sr.mode
		    color = color_map[sr.color]
		    #print int_item, sr.color, color
		    
		    # Sum up all the times spent in each mode
		    if mode in mode_dict:
			mode_dict[mode] += total_seconds
		    else:
			mode_dict[mode] = total_seconds

		    if actor == "Students" or actor.split()[0] == "Student":
			# Add time into student teacher times
			student_teacher["Students"] += total_seconds
			# add up student interaction times
			
			if (int_item,color) in student_activity:
			    student_activity[(int_item,color)] += total_seconds
			else:
			    student_activity[(int_item,color)] = total_seconds
			    
			# Fill arrays for TOTAL student timeline
			if int_start != 0 and len(student_actions) == 0: 
			    student_actions.append(("Students", counter, 0, int_start, "transparent"))
			    counter -= 1

			student_actions.append(("Students",int_item+' ('+int_dur+ ')',int_start, int_end, color))

			#Fill in dictionary for INDIVIDUAL student timeline
			if actor.split()[0] == "Student":
			    ind_student_actions.append((actor, int_item+' ('+int_dur+ ')', int_start, int_end, color))
		
		    elif actor == "Teacher": 
			student_teacher["Teacher"] += total_seconds # Add time into student teacher times
			if (int_item,color) in teacher_activity:
			    teacher_activity[(int_item,color)] += total_seconds
			else:
			    teacher_activity[(int_item,color)] = total_seconds
			if int_start != 0 and len(teacher_actions) == 0: 
			    teacher_actions.append(("Teacher", counter, 0, int_start,"transparent"))
			    counter -= 1
			teacher_actions.append(("Teacher",int_item+' ('+int_dur+ ')',int_start,int_end,color))
		    counter += 1
		# Add in the last whitespace between end of last session entry and absolute end of session
		if len(student_actions) != 0:
		    if student_actions[-1][3] != session_dur:   
			last_end_time = student_actions[-1][3]
			student_actions.append(("Students", counter,last_end_time, session_dur,"transparent"))
		else:
		    student_actions = [("Students","None",0,0,"transparent")]	
		    
		if len(teacher_actions) != 0:
		    if teacher_actions[-1][3] != session_dur:
			last_end_time = teacher_actions[-1][3]
			teacher_actions.append(("Teacher", counter, last_end_time, session_dur,"transparent"))
		else:
		    teacher_actions = [("Teacher","None",0,0,"transparent")]	
		
		# Place dictionary items in a list for easier plotting via javascript
		for key in mode_dict:
		    mode_plot.append([key,mode_dict[key]])
		for key in student_teacher:
		    student_teacher_plot.append([key,student_teacher[key]])
		for key in student_activity:
		    student_activity_plot.append([key,student_activity[key]])
		for key in teacher_activity:
		    teacher_activity_plot.append([key,teacher_activity[key]])
		
		# Sort the arrays in which color IS important, this helps keep the plot colors in order
		ind_student_actions = sorted(ind_student_actions, key=lambda x: x[0])
		student_activity_plot = sorted(student_activity_plot, key=lambda x: x[0][1])
		teacher_activity_plot = sorted(teacher_activity_plot, key=lambda x: x[0][1])
		
		self.response.write(riot_utils.render_template('templates/session_charts.html', {
		    'student_actions': student_actions,
		    'teacher_actions': teacher_actions,
		    'ind_student_actions': ind_student_actions,
		    'mode_plot': mode_plot,
		    'student_plot': student_plot,
		    'student_teacher_plot': student_teacher_plot,
		    'student_activity_plot': student_activity_plot,
		    'teacher_activity_plot': teacher_activity_plot,
		    'session_count_map': session_count_map
		}))
		
	    if not session:
		self.response.write({'error': 'no session with id: ' + sessionId})
		return
	    if not session.observer == user.email():
		self.response.write({'error': 'not authorized'})
		return
	    # checks pass

	else:
	    self.response.write({'error': 'must be logged in'})	
# Session Charts Handler
	    
###################################################################
#                   HELPER CLASSES
###################################################################
class InteractionActorModeItems():
    def __init__(self, interactionActor, interactionModes, interactionItems):
        self.actor = interactionActor
        self.modes = interactionModes
	self.items = interactionItems
class InteractionGroupItems():
    def __init__(self, interactionGroup, interactionItems):
        self.group = interactionGroup
        self.items = interactionItems

###################################################################
#                  HELPER METHODS
###################################################################

def is_blank(str):
    return str is None or len(str) == 0
