import meta
import sage
import mapper
import re
import time
import pprint

import MySQLdb as mysql
import MySQLdb.cursors

import cleverbot
import thread

from sage import echo, ansi
from sage import player, triggers, aliases
from sage.signals import player_connected

from sage.signals.gmcp import ping

from sage.signals.gmcp import room, room_changed, room_items, room_add_item, room_remove_item
from sage.signals.gmcp import room_add_player, room_remove_player, room_players
from sage.signals.gmcp import comms


from mapper.mapper import itemdata
inames = [item['name'].lower() for item in itemdata.items.values() if 'name' in item]

login_info = None
last_pull_time = time.time()
do_pull = True
convos = {}
last_response=0
dotalk = False

with open('mapper/mysql.cfg') as f:
      login_info = [x.strip().split(':') for x in f.readlines()][0]

def pull_comms():
    global login_info
    global last_pull_time
    update_time = False
    db = mysql.connect(host=login_info[0], user=login_info[1],passwd=login_info[2],
            db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
    cur=db.cursor()
    cur.execute('select `char`, `talker`, `channel`, `message` from achaea.messages_heard '
                ' where `time` > %s and `char` != %s', (last_pull_time, player.name))
    allres = cur.fetchall()
    if len(allres) > 0:
        update_time = True
    for res in allres:
        output = '%s heard %s say on %s : %s' % (res['char'],  res['talker'],
                res['channel'], res['message'])
        sage.echo(output)

    cur.execute('select `from_char`, `message` from achaea.messages_sent'
                ' where `time` > %s and `to_char` = %s', (last_pull_time, player.name))
    allres = cur.fetchall()
    if len(allres) > 0:
        update_time = True
    for res in allres:
        sage.echo(res['from_char'] + " said do " + res['message'])
        sage.send(res['message'])

    if(update_time):
        last_pull_time = time.time()

    cur.close()
    db.commit()
    db.close()

    if do_pull:
        sage.delay(5, pull_comms)


def echo_comms(talker, channel, text, **kwargs):
    global login_info
    global inames
    db = mysql.connect(host=login_info[0], user=login_info[1],passwd=login_info[2],
            db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
    cur=db.cursor()
    query = (time.time(), player.name, talker, channel, text)
    if(len(inames) == 0):
        from mapper.mapper import itemdata
        inames = [item['name'].lower() for item in itemdata.items.values() if 'name' in item]

    if talker.lower() not in inames and talker != 'You':
        cur.execute('INSERT into achaea.messages_heard '
                    ' ( `time`, `char`, `talker`, `channel`, `message` ) '
                    ' VALUES '
                    ' (%s, %s, %s, %s, %s) ;', query)
        cur.close()
        db.commit()
    db.close()

def chatstuff(talker, channel, text, **kwargs):
    global convos
    global last_response
    global talkon
    if talker.lower() == player.name.lower() or talker.lower() == 'you' or not talkon:
         return
    thread.start_new_thread(chatstuffThreaded, (talker, channel, ansi.filter_ansi(text)))

def chatstuffThreaded(talker, channel, text):
    global convos
    global last_response
    global talkon
    key = (talker, channel)
    if (player.name in text) or (channel == 'says') or (channel.startswith('tell')):
        if (talker, channel) not in convos:
            sage.echo("Starting a new convo")
            val = {
                    'time' : time.time(),
                    'response' : '',
                    'bot' : cleverbot.Cleverbot()
                   }
            convos[key] = val
        val = convos[key]
        response = ''
        if channel == 'says':
            response = 'say '
        elif channel.startswith('clt'):
            response = 'clan switch %s;clt '%(re.sub('clt','',channel))
        elif channel.startswith('tell'):
            response = channel + ' '
        else:
            sage.echo("SOMEONE SAID MY NAME OVER %s!!!"%channel)
            return
        sage.echo(re.sub('"','',re.sub('.*, "','',text)))
        sage.echo(talker)
        sage.echo(channel)
        response = response + ' ' + val['bot'].ask(text)

        last_response = max(time.time(), last_response)
        time_to_type = len(response)/5.0
        last_response = last_response + time_to_type
        sage.delay(last_response-time.time(), sage.send, response)

comms.connect(echo_comms)
comms.connect(chatstuff)
pull_comms()

comm_triggers = triggers.create_group('comm', app='communication')
comm_aliases  = aliases.create_group('comm', app='communication')

@comm_aliases.startswith (pattern="talkon", intercept=True)
def talkon(alias):
    global talkon
    talkon = True
    sage.echo("Enabling chatter")

@comm_aliases.startswith (pattern="talkoff", intercept=True)
def talkoff(alias):
    global talkon
    talkon = False
    sage.echo("Disabling chatter")

@comm_aliases.startswith (pattern="comm do ", intercept=True)
def comm_do(alias):
    global login_info
    target = alias.line.split(' ')[2]
    text = alias.line.split(':')[1]
    db = mysql.connect(host=login_info[0], user=login_info[1],passwd=login_info[2],
            db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
    cur=db.cursor()
    query = (time.time(), player.name, target, text)
    print query
    cur.execute('INSERT into achaea.messages_sent'
                ' ( `time`, `from_char`, `to_char`, `message` ) '
                ' VALUES '
                ' (%s, %s, %s, %s) ;', query)
    cur.close()
    db.commit()
    db.close()







