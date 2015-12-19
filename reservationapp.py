import cgi
import urllib
import os
import uuid

from google.appengine.api import users
from google.appengine.ext import ndb
from datetime import datetime
from email import utils
import time
from datetime import timedelta
from time import sleep
from xml.etree.ElementTree import Element, SubElement, Comment
from xml.etree import ElementTree
from xml.dom import minidom

import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

DEFAULT_RESOURCEBOOK_NAME = 'ROOT'

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def resourcebook_key(resourcebook_name=DEFAULT_RESOURCEBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity.

    We use guestbook_name as the key.
    """
    return ndb.Key('ResourceAdd', resourcebook_name)

class Owner(ndb.Model):
    identity=ndb.StringProperty(indexed=False)
    email=ndb.StringProperty(indexed=False)

class Resources(ndb.Model):
    UUID=ndb.StringProperty(indexed=True)
    name=ndb.StringProperty(indexed=True)
    owner=ndb.StructuredProperty(Owner)
    startTime=ndb.DateTimeProperty(auto_now_add=False)
    endTime=ndb.DateTimeProperty(auto_now_add=False)
    lastReservedTime=ndb.DateTimeProperty(auto_now_add=False)
    tags=ndb.StringProperty(repeated=True)
    creationTime=ndb.DateTimeProperty(auto_now_add=True)
    reservation_Num=ndb.IntegerProperty(indexed=False)

class Reservations(ndb.Model):
    UUID=ndb.StringProperty(indexed=True)
    resource_UUID=ndb.StringProperty(indexed=True)
    resource_name=ndb.StringProperty(indexed=False)
    user=ndb.StructuredProperty(Owner)
    startTime=ndb.DateTimeProperty(auto_now_add=False)
    """
    endTime=ndb.DateTimeProperty(auto_now_add=False)
    """
    duration=ndb.StringProperty(indexed=False)
    creationTime=ndb.DateTimeProperty(auto_now_add=True)
    
class MainPage(webapp2.RequestHandler) :
    def get(self):
        page = self.request.get('page') if self.request.get('page') != "" else "myres"
        user=users.get_current_user()
        currYear = datetime.now().year
        resources_query=Resources.query().order(-Resources.lastReservedTime)
        allresources=resources_query.fetch()
        reservation_query = Reservations.query().order(Reservations.startTime)
        allreservations=reservation_query.fetch()
        userclicked=self.request.get('userclicked')
        resUUID = self.request.get('resUUID');
        if resUUID != "":
            reservation_del_query = Reservations.query(Reservations.UUID==resUUID)
            reservation_del = reservation_del_query.fetch()
            resource_query = Resources.query(Resources.UUID == reservation_del[0].resource_UUID)
            resource = resource_query.fetch()
            resource[0].reservation_Num = resource[0].reservation_Num - 1
            resource[0].put()
            reservation_del[0].key.delete()
            sleep(2)
            page="myres"
            query_params = {'page':page}
            self.redirect('/?'+urllib.urlencode(query_params))
        
        if user:
            url=users.create_logout_url(self.request.uri)
            url_linktext='Logout'
            user1 = user
            
            if userclicked=="yes":
                user_email = self.request.get('user_email')
                user_id = self.request.get('user_id')
                user = users.User(user_email)
            
            template_values = {
                'user': user,
                'url': url,
                'url_linktext': url_linktext,
                'page': page,
                'curryear': currYear,
                'allresources': allresources,
                'allreservations': allreservations,
                'userclicked': userclicked,
                'user_logged': user1
            }

            template = JINJA_ENVIRONMENT.get_template('index.html')
            self.response.write(template.render(template_values))

        else:
            self.redirect(users.create_login_url(self.request.uri))

class ResourcePage(webapp2.RequestHandler):
    def get(self):
        UUID=self.request.get('UUID')
        page=self.request.get('page')
        if page == "":
            page="currres"
        resource_query = Resources.query(Resources.UUID==UUID)
        resource = resource_query.fetch()
        reservation_query = Reservations.query(Reservations.resource_UUID==resource[0].UUID)
        reservations = reservation_query.fetch()
        currYear = datetime.now().year
        user=users.get_current_user()
        date=datetime.strftime(resource[0].startTime, "%m/%d/%Y")
        resource_startTime=datetime.strftime(resource[0].startTime, "%H:%M:%S")
        resource_endTime=datetime.strftime(resource[0].endTime, "%H:%M:%S")
        available_times = [(resource_startTime,resource_endTime)]
        for reservation in reservations:
            reservation_startTime = datetime.strftime(reservation.startTime, "%H:%M:%S")
            reservation_duration = reservation.duration.split(":")
            durdelta = timedelta(hours=int(reservation_duration[0]),minutes=int(reservation_duration[1]),seconds=int(reservation_duration[2]))
            endTime = reservation.startTime + durdelta
            reservation_endTime = datetime.strftime(endTime, "%H:%M:%S")
            for timeTuple in available_times:
                if timeTuple[0] <= reservation_startTime and timeTuple[1] >= reservation_endTime:
                    tupleTemp = timeTuple
                    available_times.remove(timeTuple)
                    if timeTuple[0] == reservation_startTime and timeTuple[1] > reservation_endTime:
                        tempTuple = (reservation_endTime,timeTuple[1])
                        available_times.append(tempTuple)

                    if timeTuple[0] < reservation_startTime and timeTuple[1] == reservation_endTime:
                        tempTuple = (timeTuple[0],reservation_startTime)
                        available_times.append(tempTuple)

                    if timeTuple[0] < reservation_startTime and timeTuple[1] > reservation_endTime:
                        tempTuple1 = (timeTuple[0],reservation_startTime)
                        tempTuple2 = (reservation_endTime,timeTuple[1])
                        available_times.append(tempTuple1)
                        available_times.append(tempTuple2)
        if user:
            url=users.create_logout_url(self.request.uri)
            url_linktext='Logout'                 
            template_values = {
                'user': user,
                'url': url,
                'url_linktext': url_linktext,
                'resource': resource[0],
                'resource_date': date,
                'page': page,
                'available_times': available_times,
                'curryear': currYear,
                'resource_reservations': reservations,
            }
            template = JINJA_ENVIRONMENT.get_template('resourcePage.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class ReserveAdd(webapp2.RequestHandler):
    def post(self):
        resource_name = self.request.get('resource_name')
        resource_date = self.request.get('resource_date')
        resource_UUID = self.request.get('resource_UUID')
        startHours = self.request.get('startHours')
        startMinutes = self.request.get('startMinutes')
        startSeconds = self.request.get('startSeconds')
        startMorEve = self.request.get('startMorEve')
        durHours = self.request.get('durHours')
        durMinutes = self.request.get('durMinutes')
        durSeconds = self.request.get('durSeconds')
        startTime = startHours+":"+startMinutes+":"+startSeconds+" "+startMorEve
        startDateTime24 = datetime.strptime(resource_date+" "+startTime,"%m/%d/%Y %I:%M:%S %p")
        """
        durdelta = timedelta(hours=int(durHours),minutes=int(durMinutes),seconds=int(durSeconds))
        endDateTime24 = startDateTime24 + durdelta
        """
        reservation = Reservations()
        reservation.user = Owner(
            identity=users.get_current_user().user_id(),
            email=users.get_current_user().email())
        reservation.startTime=startDateTime24
        """
        reservation.endTime=endDateTime24
        """
        duration=durHours+":"+durMinutes+":"+durSeconds
        reservation.duration=duration
        reservation.UUID=str(uuid.uuid4())
        reservation.resource_UUID=resource_UUID
        reservation.resource_name=resource_name
        reservation.put()
        resource_query = Resources.query(Resources.UUID==resource_UUID)
        resource = resource_query.fetch()
        resource[0].lastReservedTime = datetime.now()
        resource[0].reservation_Num = resource[0].reservation_Num + 1
        resource[0].put()
        sleep(2)
        page="myres"
        query_params = {'page':page}
        self.redirect('/?'+urllib.urlencode(query_params))

class SearchPage(webapp2.RequestHandler):
    def post(self):
        user=users.get_current_user()
        resName = self.request.get('resName')
        resources_query = Resources.query(Resources.name == resName)
        resources = resources_query.fetch()
        if user:
            url=users.create_logout_url(self.request.uri)
            url_linktext='Logout'
            template_values = {
                'user': user,
                'url': url,
                'url_linktext': url_linktext,
                'resources': resources,
            }

            template = JINJA_ENVIRONMENT.get_template('searchPage.html')
            self.response.write(template.render(template_values))  
        else:
            self.redirect(users.create_login_url(self.request.uri))  

class TagsPage(webapp2.RequestHandler):
    def get(self):
        user=users.get_current_user()
        tag = self.request.get('tag')
        tag_query = Resources.query(Resources.tags==tag)
        resources = tag_query.fetch()
        if user:
            url=users.create_logout_url(self.request.uri)
            url_linktext='Logout'
            template_values = {
                'user': user,
                'url': url,
                'url_linktext': url_linktext,
                'resources': resources,
            }
        
            template = JINJA_ENVIRONMENT.get_template('tagsPage.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class RSSPage(webapp2.RequestHandler):
    def get(self):
        user=users.get_current_user()
        resUUID = self.request.get('resource_UUID')
        reservations_query = Reservations.query(Reservations.resource_UUID == resUUID)
        reservations = reservations_query.fetch()

        resource_query = Resources.query(Resources.UUID == resUUID)
        resource = resource_query.fetch()

        root = Element('rss')
        root.set('version', '2.0')

        if len(reservations) != 0:
            comment = Comment("rss Page for " + reservations[0].resource_name)
            root.append(comment)

        channel = SubElement(root, 'channel')
        title = SubElement(channel, 'title')
        title.text = "RSS for "+resource[0].name
        description = SubElement(channel, 'description')
        description.text = "Owner: "+resource[0].owner.email+", Start Time: "+resource[0].startTime.strftime("%Y-%B-%d %H:%M:%S %z")+", End Time: "+resource[0].endTime.strftime("%Y-%B-%d %H:%M:%S %z")
        link = SubElement(channel, 'link')
        urlstring = str(self.request.url)
        urlstringlist = urlstring.split('/')
        urlstringlist.remove(urlstringlist[len(urlstringlist)-1])
        url = "/".join(urlstringlist)
        url += "/resourcePage?UUID="+resUUID
        
        link.text = url
        lastBuildDateStr = resource[0].lastReservedTime
        if lastBuildDateStr is None:
            lastBuildDateStr = resource[0].creationTime
        
        lastBuildDate = SubElement(channel,'lastBuildDate')
        lbdtuple = lastBuildDateStr.timetuple()
        lbdstamp = time.mktime(lbdtuple)
        lastBuildDate.text = utils.formatdate(lbdstamp)

        pubDate = SubElement(channel, 'pubDate')
        pubDateStr = resource[0].creationTime
        pubtuple = pubDateStr.timetuple()
        pubstamp = time.mktime(pubtuple)
        pubDate.text = utils.formatdate(pubstamp)

        index = 0
        for reservation in reservations:
            index = index + 1
            item = SubElement(channel, 'item')
            itemTitle = SubElement(item,'title')
            itemTitle.text = "Reservation "+str(index);
            itemDescription = SubElement(item, 'description')
            itemDescription.text = "Reserved By: "+reservation.user.email+" Reservation Time: "+reservation.startTime.strftime("%Y-%B-%d %H:%M:%S %z")+" Duration: "+reservation.duration
            itemLink = SubElement(item,'link')
            itemLink.text=url
            itemGuid = SubElement(item,'guid')
            itemGuid.set('isPermaLink', 'false')
            itemGuid.text = reservation.UUID
            itemPubDate = SubElement(item,'pubDate')
            itemPubDateStr = reservation.creationTime
            itemPubtuple = itemPubDateStr.timetuple()
            itemPubstamp = time.mktime(itemPubtuple)
            itemPubDate.text = utils.formatdate(itemPubstamp)

        if user:
            url=users.create_logout_url(self.request.uri)
            url_linktext='Logout'
            template_values = {
                'user': user,
                'url': url,
                'url_linktext': url_linktext,
                'rssfeed': prettify(root)    
            }
            template = JINJA_ENVIRONMENT.get_template('rssPage.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class ResourceAdd(webapp2.RequestHandler):
    def post(self):
        UUID = self.request.get('UUID');
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
        tags = self.request.get('tags')
        taglist = tags.split(';')
        startTime = startHours+":"+startMinutes+":"+startSeconds+" "+startMorEve
        Date = month+"/"+day+"/"+year
        startDateTime24 = datetime.strptime(Date+" "+startTime,"%m/%d/%Y %I:%M:%S %p")
        endTime = endHours+":"+endMinutes+":"+endSeconds+" "+endMorEve
        endDateTime24 = datetime.strptime(Date+" "+endTime,"%m/%d/%Y %I:%M:%S %p")
        if UUID!="":
            resource_query = Resources.query(Resources.UUID==UUID)
            resource = resource_query.fetch()
            resource[0].name=resourceName
            resource[0].startTime=startDateTime24
            resource[0].endTime=endDateTime24
            resource[0].tags=taglist
            resource[0].put()

        else:
            resource = Resources()
            resource.owner=Owner(
                identity=users.get_current_user().user_id(),
                email=users.get_current_user().email())
            resource.name=resourceName
            resource.startTime=startDateTime24
            resource.endTime=endDateTime24
            resource.UUID=str(uuid.uuid4())
            resource.tags=taglist
            resource.reservation_Num=0
            resource.put()
        sleep(2)
        page="allres"
        query_params = {'page':page}
        self.redirect('/?'+urllib.urlencode(query_params))

app = webapp2.WSGIApplication([
    ('/',MainPage),
    ('/createres',ResourceAdd),
    ('/resourcePage',ResourcePage),
    ('/reserve',ReserveAdd),
    ('/editres',ResourceAdd),
    ('/tag',TagsPage),
    ('/rss',RSSPage),
    ('/search', SearchPage),
],debug=True)
