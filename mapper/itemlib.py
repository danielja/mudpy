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

    def load(self):
        db = mysql.connect(host='172.31.39.105', user='danny',passwd='reidchar1',
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
            res['areas'] = ast.literal_eval(res['areas'])
            self.items[res['itemid']] = res

        cur.execute('SELECT itemid, classified, quest_actions, room_actions '
                'FROM achaea.item_actions;')
        allres = cur.fetchall()

        for res in allres:
            self.items[res['itemid']]['classified'] = res['classified']
            self.items[res['itemid']]['quest_actions'] = res['quest_actions']
            self.items[res['itemid']]['room_actions'] = res['room_actions']

        db.close()

        print("Mapper: Loaded %s items " % len(self.items))

    def write_to_db(self):
        db = mysql.connect(host='172.31.39.105', user='danny',passwd='reidchar1',
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()

        counter = 0
        for itemid,item in self.items.iteritems():
            if item['updated']:
                counter = counter + 1
                cur.execute('INSERT into achaea.items '
                    '(itemid, name, wearable, groupable, takeable, '
                    'denizen,container,short_name,lastroom,areas) '
                    ' VALUES '
                    ' ({itemid}, "{name}", {wearable}, {groupable}, '
                    '  {takeable}, {denizen}, {container}, "{short_name}", '
                    '  {lastroom}, "{areas}" ) '
                    ' ON DUPLICATE KEY UPDATE '
                    ' name=name, wearable=wearable, groupable=groupable, '
                    ' takeable=takeable, denizen=denizen, container=container, '
                    ' short_name=short_name, lastroom=lastroom, areas=areas'
                    ';'.format(
                        itemid=item['itemid'],
                        name=item['name'],
                        wearable=item['wearable'],
                        groupable=item['groupable'],
                        takeable=item['takeable'],
                        denizen=item['denizen'],
                        container=item['container'],
                        short_name=item['short_name'],
                        lastroom=item['lastroom'],
                        areas=item['areas'],
                        )
                    )
        cur.close()
        db.commit()
        db.close()

        print("Mapper: Updated %i items" % counter)


    def add(self, id, name, roomid, wearable, groupable, takeable, denizen, dead, 
        container, area, new=True):
        if id not in self.items:
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
                'updated': True
                }
        if area not in self.items[id]['areas']:
            self.items[id]['areas'].append(area)

            
        if self.items[id]['updated']:
            self.new += 1


    def save(self):
        self.write_to_db()

