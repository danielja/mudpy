import meta
import sage
import time
import mapper
import re
import pprint

import MySQLdb as mysql
import MySQLdb.cursors

from sage import echo


from sage import player, triggers, aliases
from sage.signals import player_connected

from sage.signals.gmcp import ping

from sage.signals.gmcp import room, room_changed, room_items, room_add_item, room_remove_item
from sage.signals.gmcp import room_add_player, room_remove_player, room_players
from sage.signals.gmcp import skills

#from sage.signals.gmcp import defences, defence_add, defence_remove
#from sage.signals.gmcp import afflictions, affliction_add, affliction_remove

class State:
    STOP = 0
    EXPLORE = 1
    QUEST = 2
    REST = 2

class Explorer(object):

    def __init__(self):
        super(Explorer, self).__init__()
        #keep track of available attack abilities

        from mapper.mapper import mapdata, itemdata
        self.cur_target = None
        self.break_shield = False
        self.map = mapdata
        self.imap = itemdata
        self.state = State.STOP
        self.path = None
        self.can_move = True
        self.canAttack = True
        self.action_idle_wait = 0.5
        self.allies=[]
        self.took_items=[]
        self.unquest_items=[]
        self.cur_room=0

        self.my_hps=100

        self.explore_area=[]
        self.explore_loop=False

        self.visited = set()
        self.blocked= []

        self.times = {'last_room':0, 'last_scope':0, 'time':0, 'last_action': 0, 'last_ping' : 0}
        self.do_scope = True
        self.can_attack = True
        self.can_take_stuff = True
        self.block_can_take_stuff = False

        with open('mapper/mysql.cfg') as f:
            self.login = [x.strip().split(':') for x in f.readlines()][0]

        self.load_allies()

    def load_allies(self):
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
            db='achaea')
        cur=db.cursor()
        cur.execute('select `ally` from achaea.allies')
        allres = cur.fetchall()
        for ally in allres:
            self.allies.append(ally[0].lower())
        print "Allies: ", self.allies

    def clear(self):
        self.cur_target = None
        self.state = State.STOP
        self.path = None
        self.can_move = True
        self.canAttack = True
        self.took_items=[]
        self.explore_area = []
        self.explore_loop = False
        self.visited = set()
        self.blocked = []
        self.unquest_items=[]

    def connect(self, **kwargs):
        print "connected"
        #load character preferences from db:
        #  healthshop, restroom, class skills, etc

    def skills_update(self, **kwargs):
        #print kwargs['skills']
        self.my_hps = 100

    def ping(self, **kwargs):
        self.times['last_ping'] = time.time()

    def room_updated(self, **kwargs):
        self.do_scope = True
        self.times['last_ping'] = time.time()
        self.times['last_room'] = time.time()
        if self.state == State.EXPLORE:
            self.visited.add(long(player.room.id))

    def on_begin(self):
        self.times['time'] = time.time()

    def on_end(self):
        self.times['time'] = time.time()

    def other(self):
        #print self.times
        idle_time = self.times['time'] - self.times['last_action']
        action_idle = self.times['time'] - self.times['last_action']
        idle_time = min(idle_time, self.times['time'] - self.times['last_room'])
        lagging = self.times['last_ping'] < self.times['last_action']

        if self.path is not None and len(self.path.route) < self.path.step:
            self.path = None

        if(idle_time > 10 and self.path is not None and self.state != State.REST):
            if(len(self.path.route) > self.path.step and
                    player.room.id != self.path.route[self.path.step]):
                print ("Blocking room ", self.path.route[self.path.step],
                        ", current room ", player.room.id,
                        ", path: ", self.path.route)
                self.blocked.append(self.path.route[self.path.step])
                self.visited.add(self.path.route[self.path.step])
                self.times['last_action'] = time.time()
            self.path = None

        go_to_rest = ((self.state != State.REST) and
                ((player.willpower.value < 200) or (player.endurance.value < 200)))

        find_new_quest = ((self.state == State.QUEST) and
                ((self.path is None) or (self.path.route[-1] == player.room.id)))

        find_new_room = ((self.state == State.EXPLORE) and
                ((self.path is None) or (self.path.route[-1] == player.room.id)
                    or (idle_time > 20)) and
                len(self.explore_area) > 0)
        #print find_new_room, self.state, self.path, self.explore_area

        if go_to_rest:
            self.path = self.map.path_to_room( player.room.id, 6838, self.blocked)
            find_new_quest = find_new_room = False

        if find_new_room:
            self.visited.add(player.room.id)
            if player.room.area == self.explore_area[0]:
                self.path = self.map.path_to_new_room( player.room.id, self.visited,
                    self.explore_area[0], self.blocked)
            else:
                self.path = self.map.path_to_area( player.room.id,
                    self.explore_area[0], self.blocked)

            if self.path is None:
                echo ("Done exploring area: %s" % self.explore_area[0])
                self.took_items = []
                self.state = State.QUEST
                self.visited = set()
                old_area = self.explore_area.pop(0)
                if self.explore_loop:
                    self.explore_area.append(old_area)

        if find_new_quest:
            items = [self.imap.items[iid] for iid in player.inv.keys() if iid in self.imap.items]
            items = [item for item in items if item['quest_actions'] != ''
                    and item['quest_actions'] is not None
                    and item['itemid'] not in self.unquest_items]
            found_quest = False
            for item in items:
                print "command: ", item['quest_actions']
                commands = item['quest_actions'].split(';')
                for command in commands:
                    action = command.split(' ')[0]
                    if(action == 'give'):
                        target = command.split(' ')[2]
                        targ_item = self.imap.items[long(target)]
                        if targ_item['lastroom'] != player.room.id:
                            self.path = self.map.path_to_room(
                                player.room.id, targ_item['lastroom'], self.blocked)
                            found_quest = True
                            if self.path is None:
                                self.unquest_items.append(item['itemid'])
                                found_quest = False
                            elif self.state == State.QUEST:
                                break
            if not found_quest and len(self.explore_area) > 0:
                self.state = State.EXPLORE
            

        #if('shop' in player.room.details):
        #    check_shop()

        if self.path is None:
            return

        if ((self.path is not None) and (player.room.id == self.path.route[-1])):
            self.visited.add(player.room.id)
            echo("We appear to be at the end of our route:"
                    "{end},{cur}".format(end=self.path.route[-1], cur=player.room.id))
            self.path.step = self.path.step+1
            return

        do_move = ((self.state == State.EXPLORE or self.state == State.QUEST)
                    and idle_time > 0.5 and not lagging and self.can_move
                    and action_idle > self.action_idle_wait)
        if self.path.step >= len(self.path.route):
            self.path = None
            return

        if(player.room.id == self.path.route[self.path.step] and do_move):
            sage.send(self.path.directions[self.path.step])
            self.path.step = self.path.step+1
            #self.times['last_action'] = self.times['time']
            self.times['last_move'] = self.times['time']

    #only need to scope it out if we've just entered a room or something has changed
    def scope_it_out(self):
        if not self.do_scope:
            return

        self.do_scope=False
        just_entered = False

        if player.room.id != self.cur_room:
            self.cur_room = player.room.id
            just_entered = True
        just_entered = just_entered and (self.times['last_room'] > self.times['last_scope'])

        others_here = [p.lower() for p in player.room.players]
        allies_here = list(set(others_here) & set(self.allies))
        others_here = list(set(others_here) - set(self.allies))

        room_dps = len([iid for iid,item in player.room.items.iteritems() if item.denizen])

        if just_entered:
            #print 'just entered'
            self.canAttack = True

        if just_entered and len(others_here) != 0:
            #print 'people here'
            self.canAttack = False
            self.can_take_stuff = False
        elif just_entered:
            self.can_take_stuff = not self.block_can_take_stuff

        if room_dps > self.my_hps * (1 + len(self.allies)):
            print 'dps too high'
            self.canAttack = False
        self.times['last_scope'] = self.times['time']

    def room_actions(self):
        items = [self.imap.items[iid] for iid in player.room.items.keys() if iid in self.imap.items]
        is_hindered = 'webbed' in player.afflictions or 'paralyzed' in player.afflictions
        has_balance = player.balance.is_on() and player.equilibrium.is_on()

        self.can_move = not is_hindered and has_balance 

        if self.can_take_stuff:
            for item in items:
                if item['takeable'] and item['itemid'] not in self.took_items and self.can_move:
                    sage.send('take %s' % item['itemid'])
                    self.took_items.append(item['itemid'])
                if player.room.items[item['itemid']].dead:
                    sage.send('take %s' % item['itemid'])
                    self.took_items.append(item['itemid'])
        
        #figure out if we should take any actions
        # did we just get here, has anything been added
        
    def quest_actions(self):
        is_hindered = 'webbed' in player.afflictions or 'paralyzed' in player.afflictions
        has_balance = player.balance.is_on() and player.equilibrium.is_on()

        self.can_move = not is_hindered and has_balance 

        items = [self.imap.items[iid] for iid in player.inv.keys() if iid in self.imap.items]
        items = [item for item in items if item['quest_actions'] != ''
                    and item['quest_actions'] is not None
                    and item['itemid'] not in self.unquest_items]
        room_items = player.room.items.keys()
        for item in items:
            commands = item['quest_actions'].split(';')
            for command in commands:
                action = command.split(' ')[0]
                if(action == 'give' and self.can_move):
                    target = long(command.split(' ')[2])
                    if target in room_items:
                        sage.send('give %s to %s' % (item['itemid'], target))
                    #else:
                    #    print "Adding item to ignored list : ", target, room_items
                    #    self.unquest_items.append(item['itemid'])
                    
            
        # Can we complete any quests in the current room
        # refresh only if we just got here or anything new happened

    def attacks(self):
        is_hindered = 'webbed' in player.afflictions or 'paralyzed' in player.afflictions
        has_balance = player.balance.is_on() and player.equilibrium.is_on()

        self.can_move = not is_hindered and has_balance 

        items = [self.imap.items[iid] for iid in player.room.items.keys() if iid in self.imap.items]
        to_attack = []
        for item in items:
            if 'classified' in item:
                if item['classified'] and 'kill' in item['classified']:
                    to_attack.append(item)
            else:
                print 'item not classified'

        to_attack = [item for item in items if item['classified'] and 'kill' in item['classified']]
        lagging = self.times['last_action'] > self.times['last_ping']

        if len(to_attack) == 0 or self.canAttack == False or lagging or self.state == State.QUEST:
            return

        if not self.cur_target or self.cur_target not in player.room.items.keys():
            self.cur_target = to_attack[0]['itemid']
            sage.send('st %s' % self.cur_target)

        from skills.skills import smap
        if smap.use_br(target=self.cur_target, shield=self.break_shield):
            self.break_shield = False

        if has_balance and not is_hindered:
            if(player.combatclass.lower() == 'shaman') and (smap.swiftcurses < 2):
                sage.send('swiftcurse')
            elif (player.combatclass.lower() == 'shaman'):
                sage.send('swiftcurse %s bleed' % self.cur_target)
            else:
                sage.send('kill %s' % self.cur_target)
            self.times['last_action'] = time.time()

            
    def shield(self, target):
        if ((self.cur_target in self.imap.items) and
                (self.imap.items[self.cur_target]['name'].lower() == target)):
            self.break_shield = True


            

#defences.connect(expl.forceloop)
#defences_add.connect(expl.forceloop)
#defences_remove.connect(expl.forceloop)

#afflictions.connect(expl.forceloop)
#afflictions_add.connect(expl.forceloop)
#afflictions_remove.connect(expl.forceloop)

#prompt_stats.connect(expl.forceloop)

#ping.connect(expl.forceloop)

#player_connected.connect(expl.forceloop)

explr = Explorer()
do_loop = True

def action_loop():
    global do_loop
    if do_loop:
        explr.on_begin()
        explr.scope_it_out()
        explr.room_actions()
        explr.quest_actions()
        explr.attacks()
        explr.other()
        #explr.on_end()
        sage.delay(0.1, action_loop)

xplr_triggers = triggers.create_group('xplr', app='explorer')
xplr_aliases  = aliases.create_group('xplr', app='explorer')

@xplr_triggers.regex('^A nearly invisible magical shield forms around (.*).', enabled=True)
def xplr_shld(trigger):
    explr.shield(trigger.groups[0].lower())

@xplr_aliases.exact(pattern="xplr help", intercept=True)
def xplr_help(alias):
    sage.echo("xplr Commands: ")
    sage.echo("     start ")
    sage.echo("     pause ")
    sage.echo("     stop ")
    sage.echo("     clear ")
    sage.echo("     clear path ")
    sage.echo("     takeoff ")
    sage.echo("     takeon ")
    sage.echo("     loop ")
    sage.echo("     ally <target> ")
    sage.echo("     delay <target> ")
    sage.echo("     add <target> ")

@xplr_aliases.exact(pattern="xplr start", intercept=True)
def xplr_start(alias):
    global do_loop
    do_loop = True
    action_loop()

@xplr_aliases.exact(pattern="xplr pause", intercept=True)
def xplr_pause(alias):
    global do_loop
    do_loop = False
    explr.explore_loop=False

@xplr_aliases.exact(pattern="xplr stop", intercept=True)
def xplr_stop(alias):
    global do_loop
    do_loop = False
    explr.explore_loop=False
    explr.explore_area=[]

@xplr_aliases.exact(pattern="xplr takeoff", intercept=True)
def xplr_takeoff(alias):
    explr.block_can_take_stuff = True

@xplr_aliases.exact(pattern="xplr takeon", intercept=True)
def xplr_takeon(alias):
    explr.block_can_take_stuff = False

@xplr_aliases.exact(pattern="xplr clear", intercept=True)
def xplr_clear(alias):
    explr.clear()

@xplr_aliases.exact(pattern="xplr clear path", intercept=True)
def xplr_clear_path(alias):
    explr.explore_area = []
    explr.path = None


@xplr_aliases.exact(pattern="xplr loop", intercept=True)
def xplr_loop(alias):
    explr.explore_loop=True

@xplr_aliases.startswith(pattern="xplr ally ", intercept=True)
def xplr_ally(alias):
    query = alias.line.split()[2].lower()
    explr.allies.append(query)
    sage.send('ally %s' %query)

@xplr_aliases.startswith(pattern="xplr delay ", intercept=True)
def xplr_delay(alias):
    query = alias.line.split()[2]
    explr.action_idle_wait  = float(query)
    sage.echo('setting delay to %s' %query)

@xplr_aliases.startswith(pattern="xplr add ", intercept=True)
def xplr_add(alias):
    query = alias.line.split()[2]
    sage.echo("Searching for area: %s " % query)
    areas = set([room['area'] for room in explr.map.rooms.values()])
    matches = [area for area in areas if query.lower() in area.lower()]
    sage.echo("Matches for area: %s" % matches)

    if len(matches) == 1:
        explr.explore_area.append(matches[0])
        sage.echo("Area added.")
    else:
        sage.echo("Need only one area to match. Nothing added.")


@xplr_aliases.exact(pattern="thing1", intercept=True)
def dothing1(alias):
    explr.path=None
    explr.times['last_action'] = time.time()
    explr.explore_area=[]
    explr.state = State.EXPLORE
    explr.explore_area.append(player.room.area)

@xplr_aliases.exact(pattern="thing2", intercept=True)
def dothing2(alias):
    explr.path=None
    explr.state = State.QUEST
    explr.explore_area.append(player.room.area)



player_connected.connect(explr.connect)
ping.connect(explr.ping)

room.connect(explr.room_updated)
room_add_item.connect(explr.room_updated)
room_add_player.connect(explr.room_updated)
room_remove_item.connect(explr.room_updated)
room_remove_player.connect(explr.room_updated)
skills.connect(explr.skills_update)



