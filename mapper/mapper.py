from sage import player, triggers, aliases
from sage.signals.gmcp import room, room_add_item
from sage.signals import pre_shutdown
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
            if long(iid) not in itemdata.items:
                item_new = True
                itemdata.add(
                    long(iid),
                    item.name,
                    long(room.id),
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
                itemdata.add_area(long(iid), long(room.id), room.area)
    else:
        item = kwargs['item']
        if long(item.id) not in itemdata.items:
            item_new = True
            itemdata.add(
                long(item.id),
                item.name,
                long(player.room.id),
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
    if long(room.id) not in mapdata.rooms:
        new = True
    mapdata.add(
            long(room.id),
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



room_triggers = triggers.create_group('room', app='mapper')
room_aliases  = aliases.create_group('room', app='mapper')
track_shortnames = False

@room_aliases.exact(pattern="imap shorton", intercept=True)
def short_on(alias):
    global track_shortnames
    track_shortnames = True

@room_aliases.exact(pattern="imap save", intercept=True)
def isave(alias):
    itemdata.write_to_db()

@room_aliases.exact(pattern="imap load", intercept=True)
def iload(alias):
    itemdata.load()

@room_aliases.exact(pattern="imap shortoff", intercept=True)
def short_off(alias):
    global track_shortnames
    track_shortnames = False


def update_room_contents(**kwargs):
    global track_shortnames
    if track_shortnames:
        room_triggers('ih').enable()
        room_triggers('ih_over').enable()
        sage.send('ih')

@room_triggers.regex("^([a-z'_-]+)([0-9]+)[ ]+.*$",enabled=False)
def ih(trigger):
    short_name = trigger.groups[0]
    itemid = long(trigger.groups[1])
    itemdata.add_shortname(itemid, short_name)
    trigger.line.gag()

@room_triggers.regex("^Number of objects: [0-9]+$",enabled=False)
def ih_over(trigger):
    room_triggers('ih').disable()
    trigger.disable()
    trigger.line.gag()

room.connect(update_room_contents)
room.connect(room_info)
room_add_item.connect(update_room_contents)
room_add_item.connect(add_items)


def init():
    mapdata.load()
    itemdata.load()


def shutdown(**kwargs):
    mapdata.save()
    itemdata.save()

pre_shutdown.connect(shutdown)

