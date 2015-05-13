import MySQLdb as mysql
import MySQLdb.cursors



from time import time

from collections import deque
from collections import defaultdict
from Queue import PriorityQueue


class Map(object):

    def __init__(self, filename):
        super(Map, self).__init__()
        self.matrix = defaultdict(tuple)
        self.rooms = {}
        self.exits= {}
        self.new = 0

        load()

    def load(self):
        db = mysql.connect(host='52.24.108.112', user='danny',passwd='reidchar1',
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()
        cur.execute('SELECT roomid, name, area, environment, coords, details '
                'FROM achaea.rooms;')
        allres = cur.fetchall()

        for res in allres:
            self.rooms[res['roomid']] = res
            self.rooms[res['roomid']]['exits'] = {}
            self.rooms['updated'] = False

        cur.execute('SELECT roomid, direction, target_roomid, requires '
                'FROM achaea.exits order by roomid, target_roomid asc;')
        allres = cur.fetchall()

        for res in allres:
            self.rooms[res['roomid']]['exits'][res['target_roomid']] = res

        db.close()

        print("Mapper: Loaded %s rooms" % len(self.rooms))

    def write_to_db(self):
        db = mysql.connect(host='52.24.108.112', user='danny',passwd='reidchar1',
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()

        counter = 0
        for roomid,room in self.rooms.iter_tems():
            if room['updated']:
                counter = counter + 1
                cur.execute('INSERT into achaea.rooms '
                    '(roomid, name, area, environment, coords, details) '
                    ' VALUES '
                    ' ({roomid}, "{name}", "{area}", "{environment}", '
                    '   "{coords}", "{details}") '
                    ' ON DUPLICATE KEY UPDATE '
                    ' name=name, area=area, '
                    ' environment=environment, coords=coords, details=details '
                    ';'.format(
                        roomid=roomid,
                        name=room['name'],
                        area=room['area'],
                        environment=room['environment'],
                        coords=room['coords'],
                        details=room['details']
                        )
                    )
                for targid,exit in room['exits']:
                    cur.execute('INSERT into achaea.exits '
                        '(roomid, direction, target_roomid, requires) '
                        ' VALUES '
                        ' ({roomid}, "{direction}", {target_roomid}, "{requires}" '
                        ' ON DUPLICATE KEY UPDATE '
                        ' direction=direction, target_roomid=target_roomid, '
                        ' requires=requires'.format(
                            roomid=roomid,
                            direction=exit['direction'],
                            target_roomid=exit['target_roomid'],
                            requires=exit['requires']
                            )
                        )
        cur.commit()
        cur.close()
        db.close()

        print("Mapper: Updated %i rooms" % counter)


    def add(self, id, name, area, environment, exits, coords, details, maplink, new=True):
        if id not in self.rooms:
            self.rooms[id] = {
                'roomid ': id,
                'name': name,
                'area': area,
                'environment': environment,
                'exits': {},
                'coords': coords,
                'details': details,
                'updated': True
                }
        for targroom, direction in exit.items():
            if targroom not in self.rooms[id]['exits']:
                self.rooms['updated'] = True
                self.rooms[id]['exits'][targroom] = {
                        'roomid' : id,
                        'direction' : direction,
                        'target_roomid' : targroom,
                        'requires' : ''
                        }
        if self.rooms['updated']:
            self.new += 1


    def save(self):
        self.write_to_db()

