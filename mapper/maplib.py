import ast
import MySQLdb as mysql
import MySQLdb.cursors

from time import time

from collections import deque
from collections import defaultdict
from Queue import PriorityQueue
from sage import echo


class Map(object):

    def __init__(self, filename):
        super(Map, self).__init__()
        self.matrix = defaultdict(tuple)
        self.rooms = {}
        self.exits= {}
        self.new = 0
        with open('mapper/mysql.cfg') as f:
              self.login = [x.strip().split(':') for x in f.readlines()][0]

    def load(self):
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()
        cur.execute('SELECT roomid, name, area, environment, coords, details '
                'FROM achaea.rooms;')
        allres = cur.fetchall()

        for res in allres:
            res['coords'] = ast.literal_eval(res['coords'])
            res['details'] = ast.literal_eval(res['details'])
            self.rooms[res['roomid']] = res
            self.rooms[res['roomid']]['exits'] = {}
            self.rooms[res['roomid']]['updated'] = False

        cur.execute('SELECT roomid, direction, target_roomid, requires '
                'FROM achaea.exits order by roomid, target_roomid asc;')
        allres = cur.fetchall()

        for res in allres:
            self.rooms[res['roomid']]['exits'][res['target_roomid']] = res

        db.close()

        print("Mapper: Loaded %s rooms" % len(self.rooms))

    def write_to_db(self):
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()

        counter = 0
        for roomid,room in self.rooms.iteritems():
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
                for targid,exit in room['exits'].iteritems():
                    cur.execute('INSERT into achaea.exits '
                        '(roomid, direction, target_roomid, requires) '
                        ' VALUES '
                        ' ({roomid}, "{direction}", {target_roomid}, "{requires}") '
                        ' ON DUPLICATE KEY UPDATE '
                        ' direction=values(direction), target_roomid=values(target_roomid), '
                        ' requires=values(requires) ;'.format(
                            roomid=roomid,
                            direction=exit['direction'],
                            target_roomid=exit['target_roomid'],
                            requires=exit['requires']
                            )
                        )
        cur.close()
        db.commit()
        db.close()

        print("Mapper: Updated %i rooms" % counter)


    def add(self, id, name, area, environment, exits, coords, details, maplink, new=True):
        id = long(id)
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
        to_remove = []
        updated_exit_list = [x[0] for x in exits.items()]
        for targroom, val in self.rooms[id]['exits'].iteritems():
            if targroom not in updated_exit_list:
                to_remove.append(targroom)
            elif val['direction'] != exits[targroom]:
                to_remove.append(targroom)

        if len(to_remove) > 0:
            print 'removing room because exits changed!'
            db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                    db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
            cur=db.cursor()
            cur.execute('delete from achaea.exits where roomid = %s',id)
            cur.close()
            db.commit()
            db.close()

        for removeid in to_remove:
            del self.rooms[id]['exits'][removeid]

        for targroom, direction in exits.items():
            targroom = long(targroom)
            if targroom not in self.rooms[id]['exits']:
                self.rooms[id]['updated'] = True
                self.rooms[id]['exits'][targroom] = {
                        'roomid' : id,
                        'direction' : direction,
                        'target_roomid' : targroom,
                        'requires' : ''
                        }



        if self.rooms[id]['updated']:
            self.new += 1


    def save(self):
        self.write_to_db()

    def path_to_area(self, start, area, blocked=[]):
        #print "find a path to a room"
        start = long(start)
        # maintain a queue of paths
        queue = deque()
        visited = set()

        # scoping optimization tricks
        q_append = queue.append
        q_pop = queue.popleft
        v_add = visited.add
        matrix = self.matrix

        # push the first path into the queue
        q_append([start])

        while queue:
            # get the first path from the queue
            path = q_pop()
            # get the last node from the path
            node = path[-1]

            if (node in visited):
                continue

            # path found
            if node in self.rooms and self.rooms[node]['area'] == area:
                return Path(path, self)

            v_add(node)

            # enumerate all adjacent nodes, construct a new path and push it into the queue
            if node in self.rooms:
                for adjacent in self.rooms[node]['exits'].keys():
                    if (adjacent not in blocked):
                        new_path = path[:]
                        new_path.append(adjacent)
                        q_append(new_path)
        echo("No path found")
        return None

    def find_rooms_exact(self, name):
        res = []
        for roomid,room in self.rooms.iteritems():
            if name.lower() == room['name'].lower():
                res.append(roomid)
        return res

    def find_room_like(self, name, doecho=False):
        res = []
        counter=1
        for roomid,room in self.rooms.iteritems():
            if name in room['name']:
                res.append(roomid)
                if doecho:
                    echo("%s#%s : (%s) %s"%(counter,roomid,room['area'],room['name']))
                    counter = counter+1
        return res

    def limit_room_dist(self, start, room_list,  maxdist, blocked=[]):
        rooms_near = []
        for room in room_list:
            res = self.path_to_room(start, room)
            if res is None or len(res.route) > maxdist:
                continue
            rooms_near.append(room)
        return rooms_near
 

    def find_rooms_near(self, room_list,  maxdist, blocked=[]):
        rooms_near = []
        visited = set(room_list)
        new_set = set(room_list)
        for i in range(0,6):
            cur_set = new_set
            new_set = set()
            for node in cur_set:
                if node in self.rooms:
                    for adjacent in self.rooms[node]['exits'].keys():
                        if adjacent in self.rooms:
                            can_prosp = (
                                    self.rooms[adjacent]['environment'].lower() 
                                    in ['desert','mountains','hills','mountain','polar','tundra','valley'])
                            if (adjacent not in visited) and can_prosp:
                                visited.add(adjacent)
                                new_set.add(adjacent)

        return visited - set(room_list)
           



    def path_to_room(self, start, end, blocked=[]):
        #print "find a path to a room"
        start = long(start)
        end = long(end)
        # maintain a queue of paths
        queue = deque()
        visited = set()

        # scoping optimization tricks
        q_append = queue.append
        q_pop = queue.popleft
        v_add = visited.add
        matrix = self.matrix

        # push the first path into the queue
        q_append([start])

        while queue:
            # get the first path from the queue
            path = q_pop()
            # get the last node from the path
            node = path[-1]

            if (node in visited):
                continue

            # path found
            if node == end:
                return Path(path, self)

            v_add(node)

            # enumerate all adjacent nodes, construct a new path and push it into the queue
            if node in self.rooms:
                for adjacent in self.rooms[node]['exits'].keys():
                    if (adjacent not in blocked):
                        new_path = path[:]
                        new_path.append(adjacent)
                        q_append(new_path)
        echo("No path found")
        return None


    def path_to_room_in_set(self, start, already_visited, area, blocked=[]):
        start = long(start)
        allpaths = []
        for room in (area-already_visited):
            p = self.path_to_room(start, room)
            if p is not None:
                allpaths.append(p)
        allpaths.sort(key=lambda p : len(p.route))
        if(len(allpaths) == 0):
            echo("No path found")
            return None
        return allpaths[0]


    def path_to_new_room(self, start, already_visited, area, blocked=[]):
        start = long(start)
        # maintain a queue of paths
        queue = deque()
        visited = set()
        cur_room = self.rooms[start]
        area = None
        if('area' in cur_room):
            area = self.rooms[start]['area'];
        else:
            print cur_room

        # scoping optimization tricks
        q_append = queue.append
        q_pop = queue.popleft
        v_add = visited.add
        matrix = self.matrix

        # push the first path into the queue
        q_append([start])

        while queue:
            # get the first path from the queue
            path = q_pop()
            # get the last node from the path
            node = path[-1]

            if (node in visited):
                continue

            # path found
            if node not in already_visited:
                return Path(path, self)

            v_add(node)

            # enumerate all adjacent nodes, construct a new path and push it into the queue
            for adjacent in self.rooms[node]['exits'].keys():
                if (((adjacent not in self.rooms) or (self.rooms[adjacent]['area'] == area))
                        and (adjacent not in blocked)):
                    new_path = path[:]
                    new_path.append(adjacent)
                    q_append(new_path)
        echo("No path found")
        return None

class Path(object):

    def __init__(self, route, map):

        self.map = map
        self.route = route
        self.directions = self.get_directions(route)
        self.step = 0

    def get_directions(self, route):
        directions = []

        i = 0
        for step in route:
            if i > 0 and i < (len(route)):
                directions.append(self.map.rooms[route[i-1]]['exits'][route[i]]['direction'])
            i += 1

        return directions

