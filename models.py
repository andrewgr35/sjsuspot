__author__ = 'areid'

"""
    This is the M part of MVC. Put all model definitions here
    and data access methods as well
"""
import datetime
import time
from google.appengine.ext import db
import pickle

# Create the dictionary property (don't mess with code below)
class DictProperty(db.Property):
  data_type = dict

  def get_value_for_datastore(self, model_instance):
    value = super(DictProperty, self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(value))

  def make_value_from_datastore(self, value):
    if value is None:
      return dict()
    return pickle.loads(value)

  def default_value(self):
    if self.default is None:
      return dict()
    else:
      return super(DictProperty, self).default_value().copy()

  def validate(self, value):
    if not isinstance(value, dict):
      raise db.BadValueError('Property %s needs to be convertible '
                         'to a dict instance (%s) of class dict' % (self.name, value))
    return super(DictProperty, self).validate(value)

  def empty(self, value):
    return value is None
  
class InteractionGroup(db.Model):
    name = db.StringProperty(required=True)
    
# interaction items belong to Interaction groups
class InteractionItem(db.Model):
    name = db.StringProperty(required=True)
    order = db.IntegerProperty(required=False)
    color = db.StringProperty(required=False)
    
class Session(db.Model):
    observer = db.StringProperty(required=True)
    observee = db.StringProperty(required=True)
    date = db.DateTimeProperty(required=True)
    location = db.StringProperty(required=False)
    course = db.StringProperty(required=False)
    notes = db.TextProperty(required=False)
    studentcounts = DictProperty(required=False)
    numstud = db.IntegerProperty(required=False)

class SessionRecord(db.Model):
    interactionItem = db.ReferenceProperty(reference_class=InteractionItem, required=True)
    startTime = db.IntegerProperty(required=True)
    endTime = db.IntegerProperty()
    mode = db.StringProperty(required=False)
    actor = db.StringProperty(required=False)
    color = db.StringProperty(required=False)
    dateCreated = db.DateTimeProperty(required=True)



#######################
### Access Methods ####
#######################

""" Get an interaction group by name will return a list of results but should
    contain only one item
"""
    

def get_interaction_group_by_name(name):
    query = db.GqlQuery("SELECT * FROM InteractionGroup " +
                        "WHERE name = :1", name)
    return query.run()
def remove_interaction_group_by_name(removename):
    query = db.GqlQuery("SELECT * FROM InteractionGroup " +
                        "WHERE name = :1", removename)
    result = query.run()
    db.delete(result)   
    
""" Get all sessions started by a specific observer
"""
def get_sessions_for_user(user):
    if user:
        query = db.GqlQuery("SELECT * FROM Session " +
                            "WHERE observer = :1", user.email())
        return query.fetch(1000)
    else:
        return []

def deactivate_active_records_for_session(session):
    if session is not None:
        # TODO: can make this more efficient by querying which SessionRecord
        # dont have an endtime set but good enough for now
        sessionRecords = SessionRecord.all().ancestor(session).fetch(1000)
        for sr in sessionRecords:
            if sr.endTime is None or sr.endTime < 1:
                sr.endTime = int(time.time())
                sr.put()
  

                
def get_interaction_item(groupId, itemId):
    group = InteractionGroup.get_by_id(int(groupId))
    if group is not None:
        return InteractionItem.get_by_id(itemId, parent=group)
    else:
        return None
## NEW ##
def get_interaction_item_by_name(name):
    query = db.GqlQuery("SELECT * FROM InteractionItem " +
                        "WHERE name = :1", name)
    return query.run()
## NEW ##     
def remove_interaction_item_by_name(removeInteractionItemName):
    query = db.GqlQuery("SELECT * FROM InteractionItem " +
                        "WHERE name = :1", removeInteractionItemName)
    result = query.run()
    db.delete(result)    

def activate_session_record(session, interactionItem, m, a, c):
    if m == 'wg':
        mode = 'Whole group'
    if m == 'sg':
        mode = 'Small group/ pairs'
    if m == 'i':
        mode = 'Individual'
    nowSecs = int(time.time())
    now = datetime.datetime.now()
    sessionRecord = SessionRecord(parent=session, interactionItem=interactionItem,
                                  startTime=nowSecs, dateCreated=now, mode=mode, actor=a, color = c)
    sessionRecord.put()
    

