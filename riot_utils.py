__author__ = 'psakkaris'

import os
from google.appengine.ext.webapp import template

def render_template(template_name, template_values):
    path = os.path.join(os.path.dirname(__file__), template_name)
    return template.render(path, template_values)
