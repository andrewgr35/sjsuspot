#!/usr/bin/env python

# Main class that starts the WSGI webb app
# and registers handlers

import webapp2
from handlers import HomeHandler, InteractionHandler, InteractionListHandler, \
    InteractionItemHandler, NewSessionHandler, SessionListHandler, SessionHandler, SessionRecordHandler, \
    StopSessionHandler, SessionRecordListHandler,CsvHandler, InteractionRemoveHandler, RemoveInteractionItemHandler, \
    LoadDefualtInteractionHandler, RemoveAllGroupHandler, SessionNoteHandler, StudentCountHandler, SessionChartsHandler

# start app
app = webapp2.WSGIApplication([
    ('/', HomeHandler),
    ('/sessions', SessionListHandler),
    ('/session/new', NewSessionHandler),
    (r'/session/(\d+)', SessionHandler),
    (r'/session/record/(\d+)', SessionRecordHandler),
    (r'/session/count/(\d+)', StudentCountHandler),
    (r'/session/records/(\d+)', SessionRecordListHandler),
    (r'/session/stop/(\d+)', StopSessionHandler),
    (r'/session/submit/(\d+)', SessionNoteHandler),  
    (r'/session/charts/(\d+)', SessionChartsHandler),
    ('/interactions', InteractionListHandler),
    ('/interaction/group/new', InteractionHandler),
    ('/interaction/group/remove', InteractionRemoveHandler),
    ('/interaction/item/new', InteractionItemHandler),
    ('/interaction/item/remove', RemoveInteractionItemHandler),
    (r'/session/csv/(\d+)', CsvHandler),
    ('/interaction/group/default', LoadDefualtInteractionHandler),
    ('/interaction/group/remove/all', RemoveAllGroupHandler)
    
], debug=True)
