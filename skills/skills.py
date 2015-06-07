import meta
import sage
from sage import player, triggers, aliases
from sage.signals import pre_shutdown
from sage.signals.gmcp import skills
import time
import MySQLdb as mysql
import MySQLdb.cursors

class SkillMap(object):

    def __init__(self):
        self.skills={}

        #lets have skills be stored as
        #skills['skill']['ability']={'command','requires','require','aff','def'}
        self.all_skills={}
        self.new_skills=[]
        self.br_avail=[]
        self.last_action=0

        with open('mapper/mysql.cfg') as f:
            self.login = [x.strip().split(':') for x in f.readlines()][0]
        self.load()
        
    def skills_update(self, **kwargs):
        #print self.skills
        for skill, ablist in kwargs['skills'].iteritems():
            if skill not in self.skills:
                print skill
                self.skills[skill] = ablist
                for ab in ablist:
                    self.new_skills.append((skill, ab))
            for ab in ablist:
                if ab not in self.skills[skill]:
                    print '\t', ab

    def use_br(self, target='', ally=''):
        if time.time() - self.last_action < 2:
            return
        for ab in self.br_avail:
            entry = self.all_skills['battlerage'][ab]
            syntax = entry['syntax']
            if syntax:
                syntax.replace("<target>", str(target))
                syntax.replace("<ally>", str(ally))
                sage.send(syntax)
                self.last_action=time.time()
                self.br_avail.remove(ab)
                return

    def get_avail_br(self):
        res = []
        for br in self.br_avail:
            entry = self.all_skills['battlerage'][br]
            if entry['other'] and (entry['other'] == 'dmg'):
                res.append(entry['syntax'])

            

    def load(self):
        print "loading skillmap"
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()
        cur.execute(
                'SELECT `skill`, `ability`, `syntax`, `other` ' #`afflictions`,'
                #' `heals`, `requires`, `require`, `other` '
                ' from achaea.skills'
                )
        allres = cur.fetchall()

        for res in allres:
            skill = res['skill']
            ab = res['ability']
            if res['skill'] not in self.all_skills:
                self.all_skills[res['skill']] = {}
            self.all_skills[skill][ab] = res
        cur.close()
        db.close()
        print self.all_skills['battlerage']


    def save(self):
        print "Saving skillmap"
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()

        for skill,ability in self.new_skills:
            cur.execute('INSERT into achaea.skills'
                ' (skill,ability) '
                ' VALUES '
                ' (%s, %s) '
                ' ON DUPLICATE KEY UPDATE skill=skill'
                ';',(skill, ability))
        cur.close()
        db.commit()
        db.close()



smap = SkillMap()

def shutdown(**kwargs):
    smap.save()

skills.connect(smap.skills_update)
pre_shutdown.connect(shutdown)


skill_triggers = triggers.create_group('skill', app='skills')
skill_aliases  = aliases.create_group('skill', app='skills')
track_shortnames = False

@skill_aliases.exact(pattern="skills load", intercept=True)
def loadstuff(alias):
    smap.load()


@skill_aliases.exact(pattern="skills save", intercept=True)
def savestuff(alias):
    smap.save()

@skill_triggers.regex("^You can use ([A-Za-z]+) again.",enabled=True)
def enable_br(trigger):
    ab = trigger.groups[0].lower()
    print smap.all_skills['battlerage'][ab]['syntax']
    if ab not in smap.br_avail:
        smap.br_avail.append(ab)

@skill_triggers.regex("^\[Rage\]: \+[0-9.]+ Total: [0-9.]+ Now Available: (.*)",enabled=True)
def enable_br_init(trigger):
    all_ab = trigger.groups[0].lower().split(",")
    for ab in all_ab:
        if ab not in smap.br_avail:
            smap.br_avail.append(ab)


@skill_triggers.regex("^Your rage fades away.",enabled=True)
def enable_br(trigger):
    smap.br_avail = []

