from sage.signals.gmcp import room, room_add_item
from sage.signals import pre_shutdown
from sage import player
import meta

from maplib import Map
from itemlib import ItemMap
#from warelib import WaresMap

from sage import echo, ansi
import sage


mapdata = Map(meta.path + '/mapdata.json.gz')
itemdata = ItemMap(meta.path + '/itemdata.json.gz')
#waresdata = WaresMap(meta.path + '/waresdata.json.gz')

def add_items(**kwargs):
    if('room' in kwargs):
        room = kwargs['room']
        for iid,item in room.items.iteritems():
            item_new = False
            if item.name not in itemdata.items:
                item_new = True
                itemdata.add(
                    iid,
                    item.name,
                    room.id,
                    item.wearable,
                    item.groupable,
                    item.takeable,
                    item.denizen,
                    item.dead,
                    item.container,
                    room.area,
                    item_new
               )
            else:
                itemdata.addArea(item.name, room.id, room.area)
    else:
        item = kwargs['item']
        if item.name not in itemdata.items:
            item_new = True
            itemdata.add(
                item.id,
                item.name,
                player.room.id,
                item.wearable,
                item.groupable,
                item.takeable,
                item.denizen,
                item.dead,
                item.container,
                player.room.area,
                item_new
           )
 
                



def room_info(**kwargs):
    new = False
    room = kwargs['room']
    room.name = room.name.replace("Flying above ","").replace("In the trees above ","")
    if room.id not in mapdata.rooms:
        new = True
    mapdata.add(
            room.id,
            room.name,
            room.area,
            room.environment,
            {int(v):k for k, v in room.exits.items()},
            room.coords,
            room.details,
            room.map,
            new
        )
    add_items(**kwargs)

    def ql_info(room, new):
        for line in sage.buffer:
            if line[:-1] == room.name:
                line.output += ansi.grey(' (%s) (%s)' % (room.area, room.id))
                if new:
                    line.output += ansi.grey(' [new]')



    sage.defer_to_prompt(ql_info, room, new)


room.connect(room_info)
room_add_item.connect(add_items)


def init():
    mapdata.load()
    itemdata.load()


def shutdown(**kwargs):
    mapdata.save()
    itemdata.save()

pre_shutdown.connect(shutdown)

