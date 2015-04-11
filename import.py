#!/usr/bin/env python

import sys
import oauth2 as oauth
import simplejson
import urlparse
from py2neo import  Node, Relationship, Graph

PERSON = "person"
LINKEDIN = "linkedin"

if len(sys.argv) < 4:
	print "Usage:\t./import.py consumer_key consumer_secret oauth_token oauth_token_secret"
	sys.exit(1)

KEY = sys.argv[1]
SECRET = sys.argv[2]
OAUTH_TOKEN = sys.argv[3]
OAUTH_TOKEN_SECRET = sys.argv[4]

nodes = dict() 

if __name__ == '__main__':

	# configure oauth
	consumer = oauth.Consumer(key=KEY, secret=SECRET)
	token = oauth.Token(key=OAUTH_TOKEN, secret=OAUTH_TOKEN_SECRET)
	client = oauth.Client(consumer, token)

	print "[Linkedin API]\t Geting your profile information"
	resp, content = client.request('http://api.linkedin.com/v1/people/~?format=json')
 	subjectProfile = simplejson.loads(content)

  
	#get connections
	print "[Linkedin API]\t Geting your connections"
	resp, content = client.request('http://api.linkedin.com/v1/people/~/connections?format=json')
	results = simplejson.loads(content)    

	#Attach to the graph db instance
	graph_db = Graph()
	print "[Neo4j]\t Graph initialized"

	myname = ("%s %s" % (subjectProfile["firstName"].replace(",", " "), subjectProfile["lastName"].replace(",", " "))).encode('utf-8').strip()
	me = graph_db.create(Node(PERSON, name=myname)) # Comma unpacks length-1 tuple.

	nodes[myname] = me 


	# iterate over all the links
	print "[Linkedin API]\t looping on connections"
	for result in results["values"]:
		link = ("%s %s" % (result["firstName"].replace(",", " "), result["lastName"].replace(",", " "))).encode('utf-8').strip()

		if link == 'private private':
			# skip private people
			continue

		if link not in nodes:
			# Create node for this connection
			other = graph_db.create(Node(PERSON, name=link))
			nodes[link] = other
			print "-----> [Neo4j]\t created node\t" + link

			# Create path from subject to one of the subject's links
			graph_db.create(Relationship(me[0], LINKEDIN, other[0]))
			print "-----> [Neo4j]\t created link\t" + link + "<-->" + myname

# iterate over all the links
	print "[Linkedin API]\t getting shared connections for all connections"
	for result in results["values"]:
		link = ("%s %s" % (result["firstName"].replace(",", " "), result["lastName"].replace(",", " "))).encode('utf-8').strip()

		# Get shared connections
		print "-----> [Linkedin API]\t looking for\t" + link + " connections"
		sharedUrl = "https://api.linkedin.com/v1/people/%s:(relation-to-viewer:(related-connections))?format=json" % result["id"]
		resp, content = client.request(sharedUrl)
		rels = simplejson.loads(content)

		try:
			for rel in rels['relationToViewer']['relatedConnections']['values']:
				sec = ("%s %s" % (rel["firstName"].replace(",", " "), rel["lastName"].replace(",", " "))).encode('utf-8').strip()
				if sec == 'private private':
					# skip private people
					continue

				print "-----> | -----> [Linkedin API]\t found\t" + link + "<--->" + sec
				# nodes[sec] = graph_db.create(Node(PERSON, name=sec))
				
				# Create path among 1st degree links
				try:
					graph_db.create(Relationship(nodes[link][0], LINKEDIN, nodes[sec][0]))
					print "-----> | -----> [Neo4j]\t created link\t" + link + "<-->" + sec
				except KeyError:
					pass
		except KeyError:
			pass