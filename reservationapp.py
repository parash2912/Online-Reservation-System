import cgi
import urllib
import os

from google.appengine.api import users
from google.appengine.ext import ndb
from datetime import datetime
from time import sleep

import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

DEFAULT_RESOURCEBOOK_NAME = 'ROOT'

def resourcebook_key(resourcebook_name=DEFAULT_RESOURCEBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity.

    We use guestbook_name as the key.
    """
    return ndb.Key('ResourceAdd', resourcebook_name)

class Owner(ndb.Model):
    identity=ndb.StringProperty(indexed=False)
    email=ndb.StringProperty(indexed=False)

class Resources(ndb.Model):
    name=ndb.StringProperty(indexed=True)
    owner=ndb.StructuredProperty(Owner)
    startTime=ndb.DateTimeProperty(auto_now_add=False)
    endTime=ndb.DateTimeProperty(auto_now_add=False)
    lastReservedTime=ndb.DateTimeProperty(auto_now_add=False)

class MainPage(webapp2.RequestHandler) :
    def get(self):
        page = self.request.get('page') if self.request.get('page') != "" else "myres"
        user=users.get_current_user()
        currYear = datetime.now().year
        currMonth = datetime.now().month
        currDate = datetime.now().day
        currHour = datetime.now().hour
        currMinute = datetime.now().minute
        currSecond = datetime.now().second
        resources_query=Resources.query().order(-Resources.lastReservedTime)
        allresources=resources_query.fetch()
        
        if user:
            url=users.create_logout_url(self.request.uri)
            url_linktext='Logout'

            template_values = {
                'user': user,
                'url': url,
                'url_linktext': url_linktext,
                'page': page,
                'curryear': currYear,
                'currmonth': currMonth,
                'currdate': currDate,
                'currhour': currHour,
                'currminute': currMinute,
                'currsecond': currSecond,
                'allresources': allresources
            }

            template = JINJA_ENVIRONMENT.get_template('index.html')
            self.response.write(template.render(template_values))

        else:
            self.redirect(users.create_login_url(self.request.uri))

class ResourcePage(webapp2.RequestHandler):
    def get(self):
        resourceName = self.request.get('resourceName')
        ROOT=self.request.get('resourceKey')
        owner_id=self.request.get('owner_id')
        page=self.request.get('page')
        if ROOT=="":
            ROOT=resourceName+owner_id
        resource_query = Resources.query(ancestor=resourcebook_key(ROOT))
        resource = resource_query.fetch()
        user=users.get_current_user()
        template_values = {
            'user': user,
            'resource': resource,
            'resourceKey': ROOT,
            'page': page
        }
        template = JINJA_ENVIRONMENT.get_template('resourcePage.html')
        self.response.write(template.render(template_values))

class ResourceAdd(webapp2.RequestHandler):
    def post(self):
        year = self.request.get('year')
        resourceName = self.request.get('resourceName')
        month = self.request.get('month')
        day = self.request.get('day')
        startHours = self.request.get('startHours')
        startMinutes = self.request.get('startMinutes')
        startSeconds = self.request.get('startSeconds')
        startMorEve = self.request.get('startMorEve')
        endHours = self.request.get('endHours')
        endMinutes = self.request.get('endMinutes')
        endSeconds = self.request.get('endSeconds')
        endMorEve = self.request.get('endMorEve')
        startTime = startHours+":"+startMinutes+":"+startSeconds+" "+startMorEve
        Date = month+"/"+day+"/"+year
        startDateTime24 = datetime.strptime(Date+" "+startTime,"%m/%d/%Y %I:%M:%S %p")
        endTime = endHours+":"+endMinutes+":"+endSeconds+" "+endMorEve
        endDateTime24 = datetime.strptime(Date+" "+endTime,"%m/%d/%Y %I:%M:%S %p")
        ROOT=resourceName+users.get_current_user().user_id()
        resource = Resources(parent=resourcebook_key(ROOT))
        resource.owner=Owner(
            identity=users.get_current_user().user_id(),
            email=users.get_current_user().email())
        resource.name=resourceName
        resource.startTime=startDateTime24
        resource.endTime=endDateTime24
        resource.put()
        sleep(2)
        page="allres"
        query_params = {'page':page}
        self.redirect('/?'+urllib.urlencode(query_params))

app = webapp2.WSGIApplication([
    ('/',MainPage),
    ('/createres',ResourceAdd),
    ('/resourcePage',ResourcePage),
],debug=True)
