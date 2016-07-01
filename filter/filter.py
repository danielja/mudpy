import meta
import sage
import re
from sage import player, triggers, aliases
from sage.signals import pre_shutdown
from sage.signals.gmcp import skills
import time
import MySQLdb as mysql
import MySQLdb.cursors


class FilterMap(object):
    def __init__(self):
        with open('mapper/mysql.cfg') as f:
            self.login = [x.strip().split(':') for x in f.readlines()][0]
        self.sofar = ""

    def check(self, line):
        if line.strip() == '' or line == '\n' or line == ' ':
            return (1, False)
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()
        cur.execute('SELECT `name` from achaea.rooms '
                ' WHERE %s = concat(`name`,".")', line)
        roomres = cur.fetchall()
        cur.execute('SELECT rawtxt, mytxt, regex, replace_str, hold, gag from achaea.filter '
                ' WHERE %s = rawtxt or %s rlike mytxt', (line, line))
        allres = cur.fetchall()
        cur.close()
        db.commit()
        db.close()

        if len(roomres) > 0:
            return(1,False)
        if allres is None or len(allres) != 1:
            sage.echo("No match found : %s"%len(allres))
            if (len(allres) > 1):
                for res in allres:
                    print line
                    sage.echo(line)
                    sage.echo(res)

            return (len(allres), False)

        for res in allres:
            if res['replace_str'] == "":
                return (1, res['gag']==1)
            m = re.match(res['replace_str'], line)
            if m is None:
                sage.echo("LINE NOT MATCHED!")
                return (1, False)
            newline = res['replace_str']%m.groups()
            self.sofar = self.sofar + newline + " " 
            if res['hold'] == 1:
                self.sofar = self.sofar + " " + newline
            else:
                sage.echo(self.sofar)
                selfsofar = ""
            if res['gag'] == 1:
                return (1, True)
        return (1, False)


    def add(self, line):
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()
        cur.execute('INSERT into achaea.filter'
                ' (rawtxt,count) '
                ' VALUES '
                ' (%s, %s) '
                ' ON DUPLICATE KEY UPDATE rawtxt=rawtxt, count=count+1'
                ';',(line, 1))
        cur.close()
        db.commit()
        db.close()



filter_triggers = triggers.create_group('filter', app='filter')

filt = FilterMap()

@filter_triggers.regex("^(.*)$",enabled=True)
def all_match(trigger):
    (rescount, gag) = filt.check(trigger.groups[0])
    if(rescount == 0):
        filt.add(trigger.groups[0])
    elif gag:
        trigger.line.gag()
 
