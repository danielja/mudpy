import ast
import MySQLdb as mysql
import MySQLdb.cursors





from time import time

from collections import deque
from collections import defaultdict
from Queue import PriorityQueue


class ItemMap(object):

    def __init__(self, filename):
        super(ItemMap, self).__init__()
        self.items = {}
        self.new = 0
        with open('mapper/mysql.cfg') as f:
              self.login = [x.strip().split(':') for x in f.readlines()][0]

    def load(self):
        self.items={}
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()
        cur.execute(
                'SELECT itemid, name, wearable, '
                'groupable,takeable,denizen, '
                'container,short_name,lastroom,areas '
                'FROM achaea.items;'
                )
        allres = cur.fetchall()

        for res in allres:
            res['updated'] = False
            res['classified'] = ''
            res['quest_actions'] = ''
            res['room_actions'] = ''
            res['areas'] = res['areas'].split("|")
            self.items[res['itemid']] = res

        cur.execute('SELECT itemid, long_name, short_name, classified, quest_actions, room_actions '
                'FROM achaea.item_actions;')
        allres = cur.fetchall()

        for res in allres:
            res['classified'] = res['classified'] if res['classified'] is not None else ''
            res['quest_actions'] = res['quest_actions'] if res['quest_actions'] is not None else ''
            res['room_actions'] = res['room_actions'] if res['room_actions'] is not None else ''
            if res['itemid'] != 0:
                self.items[res['itemid']]['classified'] = res['classified']
                self.items[res['itemid']]['quest_actions'] = res['quest_actions']
                self.items[res['itemid']]['room_actions'] = res['room_actions']
            elif res['long_name'] != '':
                itemids = [itemid for itemid, item in self.items.iteritems() 
                        if item['name'] == res['long_name']
                        and item['classified'] == '']
                for itemid in itemids:
                    self.items[itemid]['classified'] = res['classified']
                    self.items[itemid]['quest_actions'] = res['quest_actions']
                    self.items[itemid]['room_actions'] = res['room_actions']


        db.close()

        print("Mapper: Loaded %s items " % len(self.items))

    def write_to_db(self):
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()

        counter = 0
        for itemid,item in self.items.iteritems():
            if item['updated']:
                counter = counter + 1
                if item['denizen']:
                    cur.execute('INSERT into achaea.item_actions '
                        ' (long_name) '
                        ' VALUES '
                        ' (%s) '
                        ' ON DUPLICATE KEY UPDATE long_name=long_name'
                        ';',(item['name']))
                vals = (
                        item['itemid'],
                        item['name'],
                        item['wearable'],
                        item['groupable'],
                        item['takeable'],
                        item['denizen'],
                        item['container'],
                        item['short_name'],
                        item['lastroom'],
                        '|'.join(item['areas']),
                        )
                cur.execute('INSERT into achaea.items '
                    '(itemid, name, wearable, groupable, takeable, '
                    'denizen,container,short_name,lastroom,areas) '
                    ' VALUES '
                    ' (%s, %s, %s, %s, '
                    '  %s, %s, %s, %s, '
                    "  %s, %s ) "
                    ' ON DUPLICATE KEY UPDATE '
                    ' name=name, wearable=wearable, groupable=groupable, '
                    ' takeable=takeable, denizen=denizen, container=container, '
                    ' short_name=values(short_name), lastroom=lastroom, areas=values(areas)'
                    ';', vals)
        cur.close()
        db.commit()
        db.close()

        print("Mapper: Updated %i items" % counter)

    def find_rooms_with(self, shortname):
        res = {}
        for itemid,item in self.items.iteritems():
            if shortname in item['name']:
                if item['name'] in res:
                    res[item['name']].append(item['lastroom'])
                else:
                    res[item['name']] = [item['lastroom']]
        for name, rooms in res.iteritems():
            print name, rooms
            return rooms


    def add_shortname(self, id, shortname):
        id = long(id)
        if id in self.items and self.items[id]['short_name'] == '':
            self.items[id]['short_name'] = shortname
            self.items[id]['updated'] = True

    def add_area(self, id, roomid, roomarea):
        if id not in self.items:
            return
        item = self.items[id]
        roomid = long(roomid)
        if roomarea not in self.items[id]['areas']:
            item['areas'].append(roomarea)
            item['updated'] = True
        item['lastroom'] = roomid


    def add(self, id, name, roomid, wearable, groupable, takeable, denizen, dead, 
        container, area, new=True):
        if denizen and dead:
            return
        id = long(id)
        if (id in self.items and name != self.items[id]['name']):
            print name, self.items[id]['name']
        if (id not in self.items
                or name != self.items[id]['name']):
            self.items[id] = {
                'itemid':id,
                'name':name,
                'wearable':wearable,
                'groupable':groupable,
                'takeable':takeable,
                'denizen':denizen,
                'container':container,
                'short_name':'',
                'lastroom':roomid,
                'areas':[area],
                'updated': True,
                'classified' : '',
                'quest_actions' : '',
                'room_actions' : '',
                }
        if area not in self.items[id]['areas']:
            self.items[id]['areas'].append(area)

        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()
        cur.execute('SELECT itemid, long_name, short_name, classified, quest_actions, room_actions '
                'FROM achaea.item_actions where long_name=%s;',self.items[id]['name'])
        allres = cur.fetchall()
        for res in allres:
            res['classified'] = res['classified'] if res['classified'] is not None else ''
            res['quest_actions'] = res['quest_actions'] if res['quest_actions'] is not None else ''
            res['room_actions'] = res['room_actions'] if res['room_actions'] is not None else ''
            if res['itemid'] == self.items[id]['itemid']:
                self.items[id]['classified'] = res['classified']
                self.items[id]['quest_actions'] = res['quest_actions']
                self.items[id]['room_actions'] = res['room_actions']
            elif res['long_name'] != self.items[id]['name']:
                self.items[id]['classified'] = res['classified']
                self.items[id]['quest_actions'] = res['quest_actions']
                self.items[id]['room_actions'] = res['room_actions']
        db.close()



            
        if self.items[id]['updated']:
            self.new += 1


    def save(self):
        self.write_to_db()

