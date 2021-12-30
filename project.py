#!/usr/bin/env python3

import sqlite3
from sqlite3.dbapi2 import IntegrityError
import pyparsing as pp
import sys
import time

ppc = pp.pyparsing_common

con = sqlite3.connect(':memory:')

cur = con.cursor()

# run program from command line as `./project.py`, see `help` command for commands
# and run `demo` to see a demo

SCHEMA = """
PRAGMA foreign_keys = ON;
-- locations have an ID and name
CREATE TABLE location ( 
	id                   integer NOT NULL  PRIMARY KEY  ,
	name                 varchar(100) NOT NULL     
 );

-- players have a name, id, and location
-- they must be in one location (total participation)
CREATE TABLE player ( 
	name                 varchar(100) NOT NULL    ,
	id                   integer NOT NULL  PRIMARY KEY  ,
	location_id          integer DEFAULT 0 NOT NULL,
	FOREIGN KEY ( location_id ) REFERENCES location( id ) ON DELETE SET DEFAULT
 );

-- locations link from one to another
-- one directional, locations can have many links to and from each other  
-- many to many self join table
CREATE TABLE loc_join ( 
	from_id              integer,
	to_id                integer,
  -- this is created as two foreign keys because it seems that we cannot 
  -- reference the same column twice in a foreign key constraint
	CONSTRAINT pk_join PRIMARY KEY ( from_id, to_id ) 
	FOREIGN KEY ( from_id) REFERENCES location( id ) ON DELETE CASCADE ,
	FOREIGN KEY ( to_id ) REFERENCES location( id ) ON DELETE CASCADE
 );
"""

SCHEMA_LIST = SCHEMA.split(sep=";")

for statement in SCHEMA_LIST:
  cur.execute(statement)

DATABASE_START = """
INSERT INTO LOCATION(id, name) VALUES (0, "start");

"""

DATABASE_START_LIST = DATABASE_START.split(sep=";")

for statement in DATABASE_START_LIST:
  cur.execute(statement)

con.commit()


# We create a grammar for user database operations
# Define from top down because otherwise things won't be initialized
# when we reference them

# name = word
name = pp.Word(pp.alphas)
# p_name = name
p_name = name
# l_name = name
l_name = name
# id = ppc.integer
id = ppc.integer
# from_id = id
from_id = id
# to_id = id 
to_id = id

# location = "location" name
location = pp.Keyword("location") + name
# player = "player" name
player = pp.Keyword("player") + name
# link = "link" from_id to_id
link = pp.Keyword("link") + from_id + to_id

# loc_id = "location" id
loc_id = pp.Keyword("location") + id
# player_id = "player" id
player_id = pp.Keyword("player") + id

# create = "create" (location | player | link)
create = pp.Keyword("create") + (location | player | link)
# remove = "remove" (loc_id | player_id | link)
remove = pp.Keyword("remove") + (loc_id | player_id | link)


# info = "info" (location | player | player_id | loc_id)
info = pp.Keyword("info") + (location | player | player_id | loc_id | "all")
# move = "move" player_id (l_name | loc_id )
move = pp.Keyword("move") + player_id + (location | loc_id)
# look = "look" player_id 
look = pp.Keyword("look") + player_id
# help = "help"
help = pp.Keyword("help")
# quit = "quit"
quit = pp.Keyword("quit")

# admin_command = (create | remove)
admin_command = (create | remove)

# user_command = (info | move | help | quit)
user_command = (info | move | look | help | quit)
# command = (admin_command | user_command)
command = (admin_command | user_command)


# constraints on commands
# all constraints beyond naming are checked in functions 

# create location
# name is required, single word, duplicates are fine, disambiguated by id

def create_location(name):
  command = f"INSERT INTO location(name) VALUES ('{name}')"
  cur.execute(command)

# create player
# name is required, single word, duplicates are fine, disambiguated by id
# will be initialized to location 0
def create_player(name):
  # start player in 0, which is the default
  command = f"INSERT INTO player(name) VALUES ('{name}')"
  cur.execute(command)

# create link
# from_id and to_id are required, integers, must exist as location id 
def create_link(from_id, to_id):
  # make sure both destinations exist 
  # this should be enforced in the foreign key constraint on the table
  # but for some reason it doesn't work
  command = f"INSERT INTO loc_join(from_id, to_id) VALUES ({from_id}, {to_id})"
  try:
    cur.execute(command)
  except sqlite3.IntegrityError:
    print("Links already exists, or references non-existent location")

# remove location
# id is required, integer, must exist as location id
# also removes all links, should be automatic because of cascade behavior
def remove_loc(id):
  command = f"DELETE FROM location WHERE id = {id}"
  cur.execute(command)

# remove player
# id is required, integer, must exist as player id
def remove_player(id):
  command = f"DELETE FROM player WHERE id = {id}"
  cur.execute(command)

# remove link
# from_id and to_id are required, integers, link must exist
def remove_link(from_id, to_id):
  command = f"DELETE FROM loc_join WHERE from_id = {from_id} AND to_id = {to_id}"
  cur.execute(command)

# info location
# name is required, returns all locations with that name
def info_loc(name):
  command = f"SELECT * FROM location WHERE name = '{name}'"
  cur.execute(command)
  print(cur.fetchall())

# info loc_id
# id is required, integer, must exist as location id
# returns location with that id, all players in that location, 
# and all links from that location
def info_lid(id):
  loc_command = f"SELECT * FROM location WHERE id = {id}"
  loc = cur.execute(loc_command)
  print(loc.fetchone())
  player_command = f"SELECT * FROM player WHERE location_id = {id}"
  players = cur.execute(player_command)
  print(players.fetchall())
  link_command = f"SELECT * FROM loc_join WHERE from_id = {id}"
  links = cur.execute(link_command)
  print(links.fetchall())

# info player
# name is required, returns all players with that name
def info_pname(name):
  command = f"SELECT * FROM player WHERE name = '{name}'"
  cur.execute(command)
  print(cur.fetchall())

# info player_id
# id is required, integer, must exist as player id
# returns player with that id, and location that player is in
def info_pid(id):
  command = f"""SELECT * FROM player 
  INNER JOIN location ON player.location_id = location.id
  WHERE player.id = {id}"""
  cur.execute(command)
  print(cur.fetchone())

# info all
# returns all locations, players, and links
def info_all():
  locs = "SELECT * FROM location"
  players = "SELECT * FROM player"
  links = "SELECT * FROM loc_join"
  res = cur.execute(locs)
  print("Locations (Id, name):")
  for l in res:
    print(l)
  res = cur.execute(players)
  print("Players (Name, id, location_id):")
  for l in res:
    print(l)
  res = cur.execute(links)
  print("Links (From, to):")
  for l in res:
    print(l)
  
# look player_id
# player must exist, returns rooms with links from current room
def look(pid):
  command = f"""SELECT location.name, location.id FROM player 
  INNER JOIN loc_join ON player.location_id = loc_join.from_id
  INNER JOIN location ON location.id = loc_join.to_id
  WHERE player.id = {pid}"""
  res = cur.execute(command)
  for l in res:
    print(l)

# move player_id l_name
# player_id is required, integer, must exist as player id, 
# l_name is required, single word, checks rooms with links from current for any with matching name

# move player_id loc_id
# player_id is required, integer, must exist as player id, 
# loc_id is required, integer, must exist as location id for room with link from current room
def move(pid, loc):
  if isinstance(loc, str):
    # find locations with links from player's current room with matching name, 
    # and update player location to that location
    command = f"""UPDATE player SET location_id = (
      SELECT location.id FROM location WHERE id IN
      (SELECT to_id FROM loc_join WHERE
      from_id = (SELECT location_id FROM player WHERE id = {pid}))
      AND location.name = '{loc}'
      ORDER BY id DESC LIMIT 1)"""
  # Because parsing succeeded, this must be an int
  else: 
    # find locations with links from player's current room with matching id,
    # and update player location to that location
    command = f"""UPDATE player SET location_id = (
      SELECT location.id FROM location WHERE id IN
      (SELECT to_id FROM loc_join WHERE
      from_id = (SELECT location_id FROM player WHERE id = {pid}))
      AND location.id = '{loc}')"""
    pass
  try:
    res = cur.execute(command)
  except IntegrityError:
    con.rollback()
    print("No destination found from current location")

# help
# unary command, displays help
def help():
  print("""
  Commands:
    create location <name>
    create player <name>
    create link <from_id> <to_id>
    remove location <id>
    remove player <id>
    remove link <from_id> <to_id>
    info location <name>
    info location <id>
    info player <name>
    info player <id>
    info all
    move <player_id> <l_name>
    move <player_id> <loc_id>
    help
    quit
  """)

# quit 
# unary command, quits program
def quit():
  sys.exit("Thanks for playing!")


def commandAction(s, loc, toks):
  # create command switching
  # the token at [1] is the switch to which command to use, 
  # then the rest of the tokens are the arguments to that command
  if toks[0] == "create":
    if toks[1] == "location":
      create_location(toks[2])
    elif toks[1] == "player":
      create_player(toks[2])
    elif toks[1] == "link":
      create_link(toks[2], toks[3])

  # remove command switching
  # the token at [1] is the switch to which command to use,
  # then the rest of the tokens are the arguments to that command
  elif toks[0] == "remove":
    if toks[1] == "location":
      remove_loc(toks[2])
    elif toks[1] == "player":
      remove_player(toks[2])
    elif toks[1] == "link":
      remove_link(toks[2], toks[3])
      
  # info command switching

  elif toks[0] == "info":
    # first check if command is all
    if toks[1] == "all":
      info_all()
    # then check if lookup is by name
    elif isinstance(toks[2], int):
      # then if it's a player or location
      if toks[1] == "player":
        info_pid(toks[2])
      elif toks[1] == "location":
        info_lid(toks[2])
    # or by id
    elif isinstance(toks[2], str):
      # then if it's a player or location
      if toks[1] == "location":
        info_loc(toks[2])
      elif toks[1] == "player":
        info_pname(toks[2])

  # look command takes a player id in [2]
  elif toks[0] == "look":
    look(toks[2])

  # move command takes a player id in [2] and a location name or id in [3]
  elif toks[0] == "move":
    move(toks[2], toks[4])

  elif toks[0] == "help":
    help()

  elif toks[0] == "quit":
    quit()

  else:
    print("Command was parsed as valid but had no implementation")
  con.commit()

command.addParseAction(commandAction)

# example commands
# create location home
# create player bob
# create link 1 2
# remove location 1
# remove player 1
# remove link 1 2
# info location 1
# info player bob
# info player 1
# info location 1
# look player 1
# move player 1 home
# help
# quit


demo = """help
  info location home
  info location work
  create link 1 2
  look player 1
  info all
  info player 1
  info location home
  move player 1 location start
  info player 1
  info location start
  remove location 1
  remove link 1 2
  info all"""

def main():
  command.parseString("create location work")
  command.parseString("create location home")
  command.parseString("create player bob")
  command.parseString("create link 0 1")
  command.parseString("create link 0 2")
  command.parseString("create link 2 0")
  command.parseString("create link 1 0")

  while True:
    print("Enter a command:")
    cmd_input = input()
    if cmd_input == "raw":
      print("Enter a raw command:")
      cmd_input = input()
      cur.execute(cmd_input)
      print(cur.fetchall())
    elif cmd_input == "demo":
      for line in demo.splitlines():
        print(line)
        command.parseString(line)
        time.sleep(0.5)
    else: 
      try:
        command.parseString(cmd_input)
      except pp.ParseException as pe:
        print(pe)

if __name__ == "__main__":
  main()