import meta
import sage
from sage import player, triggers, aliases, gmcp
from sage.signals import pre_shutdown
from sage.signals.gmcp import skills, skill_info
import time
import MySQLdb as mysql
import MySQLdb.cursors

SKILL_UNKNOWN = '*** You have not yet learned this ability ***'

class SkillMap(object):

    def __init__(self):
        self.skills={}

        #lets have skills be stored as
        #skills['skill']['ability']={'command','requires','require','aff','def'}
        self.all_skills={}
        self.new_skills=[]
        self.br_avail=[]
        self.last_action=0
        self.swiftcurses=0

        with open('mapper/mysql.cfg') as f:
            self.login = [x.strip().split(':') for x in f.readlines()][0]
        self.load()
        
    def show_skill_info(self, group, skill, info, **kwargs):
        info_lines = info.splitlines()
        info_map = {'known':True}
        field = "default"

        # Skills are received in order - keep track of that order
        if group not in self.skills:
            self.skills[group] = []
        if skill not in self.skills[group]:
            self.skills[group].append(skill)
        info_map['idx'] = self.skills[group].index(skill)+1
        for line in info_lines:
            if line == SKILL_UNKNOWN:
                info_map['known'] = False
            elif line.endswith(":"):
                field = line.strip(':').lower()
            elif len(line) > 0 and field in info_map:
                info_map[field] += ";%s"%line.strip()
            elif len(line) > 0:
                info_map[field] = line.strip()
            elif field not in info_map:
                info_map[field] = ''
        for field in ['works on/against', 'details','cooldown']:
            if field not in  info_map:
                info_map[field] = ''

        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()

        info_map['workson'] = info_map['works on/against']

        for key,value in info_map.iteritems():
            if key in ['syntax','details','workson','resource','drains','cooldown','idx']:
                cur.execute('INSERT into achaea.skill_info'
                    ' (skill,ability,' +key+ ') '
                    ' VALUES '
                    ' (%s, %s, %s) '
                    ' ON DUPLICATE KEY UPDATE skill=skill, ability=ability, ' +key+ '=values(' +key+ ')'
                    ';',(group, skill,value))
        cur.close()
        db.commit()
        db.close()





    def skills_update(self, **kwargs):
        print self.skills
        for skill, ablist in kwargs['skills'].iteritems():
            if skill not in self.skills:
                print skill
                self.skills[skill] = ablist
                idx = 1
                for ab in ablist:
                    self.new_skills.append((skill, ab, idx))
                    idx = idx+1
            for ab in ablist:
                if ab not in self.skills[skill]:
                    print '\t', ab

    def use_br(self, shield=False, target='', ally=''):
        if time.time() - self.last_action < 2:
            return False
        for ab in self.br_avail:
            ab = ab.strip()
            if ab in self.all_skills['battlerage']:
                entry = self.all_skills['battlerage'][ab]
                syntax = entry['syntax']
                can_use = entry['other'] and 'dmg' in entry['other']
                if shield:
                    can_use = entry['other'] and 'shld' in entry['other']
                if syntax and can_use:
                    syntax.replace("<target>", str(target))
                    syntax.replace("<ally>", str(ally))
                    sage.send(syntax)
                    self.last_action=time.time()
                    self.br_avail.remove(ab)
                    if shield:
                        return True
                    return False
            else:
                print ab
                print self.all_skills['battlerage'].keys()
                print ab in self.all_skills['battlerage'].keys()
                return False

    def load(self):
        print "loading skillmap"
        db = mysql.connect(host=self.login[0], user=self.login[1],passwd=self.login[2],
                db='achaea',cursorclass=MySQLdb.cursors.DictCursor)
        cur=db.cursor()
        cur.execute(
                'SELECT `skill`, `ability`, `syntax`, `other`,`idx` ' #`afflictions`,'
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

        for skill,ability,idx in self.new_skills:
            cur.execute('INSERT into achaea.skills'
                ' (skill,ability,idx) '
                ' VALUES '
                ' (%s, %s, %s) '
                ' ON DUPLICATE KEY UPDATE skill=skill, idx=values(idx)'
                ';',(skill, ability,idx))
        cur.close()
        db.commit()
        db.close()



smap = SkillMap()

def shutdown(**kwargs):
    smap.save()



skill_info.connect(smap.show_skill_info)
skills.connect(smap.skills_update)
pre_shutdown.connect(shutdown)


skill_triggers = triggers.create_group('skill', app='skills')
skill_aliases  = aliases.create_group('skill', app='skills')
track_shortnames = False

@skill_aliases.exact(pattern="skillsup", intercept=True)
def updateskills(alias):
    gmcp.get_skills()

@skill_aliases.exact(pattern="skills load", intercept=True)
def loadstuff(alias):
    smap.load()


@skill_aliases.exact(pattern="skills save", intercept=True)
def savestuff(alias):
    smap.save()

@skill_triggers.regex("^You can use ([A-Za-z]+) again.",enabled=True)
def enable_br(trigger):
    ab = trigger.groups[0].lower().strip()
    if ab not in smap.br_avail:
        smap.br_avail.append(ab)

@skill_triggers.regex("^\[Rage\]: \+[0-9.]+ Total: [0-9.]+ Now Available: (.*)",enabled=True)
def enable_br_init(trigger):
    all_ab = trigger.groups[0].lower().split(",")
    all_ab = [entry.strip() for entry in all_ab]
    for ab in all_ab:
        if ab not in smap.br_avail:
            smap.br_avail.append(ab)


@skill_triggers.regex("^Your rage fades away.",enabled=True)
def rage_fade(trigger):
    smap.br_avail = []

@skill_triggers.regex("^The swiftcurse is empowered with another ([0-9]*) curses.$",enabled=True)
def swiftcurse_tracker(trigger):
    smap.swiftcurses = int(trigger.groups[0])

@skill_triggers.regex("^You weave your fingers together, calling upon the swiftcurse to aid you.$",enabled=True)
def swiftcurse_tracker1(trigger):
    smap.swiftcurses = 10



