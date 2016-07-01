import meta
import sage
from sage import player, triggers, aliases, ansi
from sage.signals import post_prompt
from sage.signals.gmcp import affliction_add, affliction_remove

class AffTracker(object):

    def __init__(self):
        self.myaffs = []
        self.thaffs = []
        self.venoms = []
        self.echo_aff=False

        self.text = ""
        self.aff_str = ""

        self.cures=[]

        self.cure_map = {
                'magnesium' : set(['paralysis','slickness']),
                'aurum' : set(['asthma','weariness','sensitivity','clumsiness']),
                'plumbum' : set(['stupidity','shyness','dizziness']),
                'ferrum' : set(['nausea','darkshade','haemophilia','addiction']),
                'realgar' : set(['disloyalty','disfigurement','slickness']),
                'argentum' : set(['recklessness']),
                'epidermal' : set(['anorexia']),
                'mending' : set(['brokenleftarm','brokenrightarm','brokenleftleg','brokenrightleg']),
                }

    def add_venom(self, venom):
        self.venoms.append(venom)

    def add_cured(self, cure, line):
        self.cures.append((cure,line))

    def confirm_cure(self, aff, line):
        for i in xrange(len(self.cures)):
            cure = self.cures[i]
            print cure, aff, self.cure_map[cure[0]]
            if aff in self.cure_map[cure[0]]:
                sage.echo(ansi.bold_green("Cured %s"%aff))
                self.echo_affs()
                del self.cures[i]
                return True
        self.cures.append(('',line))
        return False

    def echo_dstab(self, target, line):
        if(len(self.venoms) == 2):
            self.text = ansi.bold_green("You Doublestab %s : %s %s"%(target, self.venoms[0], self.venoms[1]))
        else:
            sage.echo(line)

    def echo_got_dstab(self, target, line):
        print player.afflictions
        self.text = "%s Doublestabed YOU : "%(target)
        self.got_dstab = True


    def hit_rebounding(self):
        self.text = ansi.bold_red("REBOUNDED: " + self.text)

    def echo_affs(self):
        """ Affs we care about : 
            curare, kalmia, gecko, slike, vernalius, impatience: CKGSVI
            paralysis, asthma, slickness, anorexia, weariness, impatience: PASXWI
        """
        locks = set(['paralysis','asthma','slickness','anorexia','weariness','impatience'])
        basic = set(['deafness','blindness'])
        oafs = len(player.afflictions-basic-locks)
        self.aff_str = "{par}{asth}{slick}{ano}{wear}{imp}{other}".format(
               par=   ( 'P' if 'paralysis' in player.afflictions else '_'),
               asth=  ( 'A' if 'asthma' in player.afflictions else '_'),
               slick= ( 'S' if 'slickness' in player.afflictions else '_'),
               ano=   ( 'X' if 'anorexia' in player.afflictions else '_'),
               wear=  ( 'W' if 'weariness' in player.afflictions else '_'),
               imp=   ( 'I' if 'impatience' in player.afflictions else '_'),
               other= ( oafs if oafs != 0 else "_"))
        self.echo_aff = True

    def add_thaff(self):
        self.thaffs.append("")

    def end(self, signal):
        if self.text != "":
            if self.got_dstab:
                self.got_dstab = False
                if(len(self.venoms) != 2):
                    self.text = ""
                    self.text = player.afflictions
                else:
                    self.text = ansi.bold_red(self.text +" %s %s"%(self.venoms[0], self.venoms[1]))
            sage.echo(self.text)
            self.text = ""

        if self.echo_aff:
            sage.echo(ansi.bold_yellow(self.aff_str))
            self.echo_aff = False
        if len(self.cures) > 0:
            for cure in self.cures:
                sage.echo(cure[1])
            self.cures=[]
        self.venoms=[]


tracker=AffTracker()

combat_trigs = triggers.create_group('combat', app='combat')

@combat_trigs.regex(pattern="You remove 1 [a-z]+, bringing the total in the Rift to [0-9]+.", enabled=True)
def orift(trigger):
    trigger.line.gag()
    trigger.gag_prompt=True

@combat_trigs.exact(pattern="You are already wielding that.", enabled=True)
def prewield(trigger):
    trigger.line.gag()

@combat_trigs.exact(pattern="The attack rebounds back onto you!", enabled=True)
def hit_rebounding(trigger):
    tracker.hit_rebounding()
    trigger.line.gag()

@combat_trigs.regex(pattern="^([A-Z][a-z]+) pricks you twice in rapid succession with (his|her) dirk.$", enabled=True)
def got_dstab_echo(trigger):
    trigger.line.gag()
    tracker.echo_got_dstab(trigger.groups[0], trigger.line)


@combat_trigs.regex(pattern="^You prick ([A-Z][a-z]+) twice in rapid succession with your dirk.$", enabled=True)
def dstab_echo(trigger):
    trigger.line.gag()
    tracker.echo_dstab(trigger.groups[0], trigger.line)

@combat_trigs.regex(pattern="You rub some ([a-z]+) on ([a-z,' ]+)\.", enabled=True)
def envenom(trigger):
    trigger.line.gag()
    tracker.add_venom(trigger.groups[0])

@combat_trigs.regex(pattern="Horror overcomes ([A-Z][a-z]+)'s face as (his|her) body stiffens into paralysis")
def aff_paralysis(trigger):
    if 'curare' in tracker.venoms:
        trigger.line.gag()

@combat_trigs.exact(pattern="You realise that your heroic actions can no longer continue unnoticed, and you take it upon yourself to rectify the situation.", enabled=True)
def got_eurypteria(trigger):
    if 'recklessness' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('eurypteria:reckless')
    trigger.line.gag()

@combat_trigs.exact(pattern="You gasp as your fine-tuned reflexes disappear into a haze of confusion.", enabled=True)
def got_xentio(trigger):
    if 'clumsiness' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('xentio:clumsy')
    trigger.line.gag()

@combat_trigs.exact(pattern="You feel a tightening sensation grow in your lungs.", enabled=True)
def got_kalmia(trigger):
    if 'asthma' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('kalmia')
        sage.echo((tracker.venoms))
    trigger.line.gag()

@combat_trigs.exact(pattern="You look about yourself nervously.", enabled=True)
def got_digitalis(trigger):
    if 'shyness' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('digitalis:shy')
    trigger.line.gag()


@combat_trigs.exact(pattern="Your vision is flooded with light, and your face suddenly reddens.", enabled=True)
def got_darkshade(trigger):
    if 'darkshade' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('darkshade')
    trigger.line.gag()
    
@combat_trigs.regex(pattern="You watch, in horror, as your (left|right) arm shrivels up and becomes useless.", enabled=True)
def got_epteth(trigger):
    if 'brokenleftarm' in player.afflictions or 'brokenrightarm' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('epteth:arm')
    trigger.line.gag()
    
@combat_trigs.exact(pattern="A prickly, stinging sensation spreads through your body.", enabled=True)
def got_prefarar(trigger):
    if 'sensitivity' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('prefarar')
    trigger.line.gag()
    
@combat_trigs.exact(pattern="You feel ugliness radiating from you.", enabled=True)
def got_monkshood(trigger):
    if 'disloyalty' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('monkshood:disloyal')
    trigger.line.gag()
    
@combat_trigs.exact(pattern="A sense of extreme nausea washes over you.", enabled=True)
def got_euphorbia(trigger):
    if 'nausea' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('euphorbia:nausea')
    trigger.line.gag()
    
@combat_trigs.regex(pattern="You stumble as your (left|right) leg shrivels into a useless appendage.", enabled=True)
def got_epseth(trigger):
    if 'brokenleftleg' in player.afflictions or 'brokenrightleg' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('epseth:leg')
    trigger.line.gag()
    
@combat_trigs.exact(pattern="Your mind swims as dizziness overtakes you.", enabled=True)
def got_larkspur(trigger):
    if 'dizziness' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('larkspur:dizzy')
    trigger.line.gag()
    
@combat_trigs.exact(pattern="The idea of eating or drinking is repulsive to you.", enabled=True)
def got_slike(trigger):
    if 'anorexia' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('slike:ano')
    trigger.line.gag()
    
@combat_trigs.exact(pattern="You feel incredibly tired, and fall asleep immediately.", enabled=True)
def got_delphinium(trigger):
    if 'sleeping' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('delphinium')
    trigger.line.gag()
    
@combat_trigs.exact(pattern="You feel a terrible hunger grow within you.", enabled=True)
def got_vardrax(trigger):
    if 'addiction' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('vardrax:addiction')
    trigger.line.gag()
    
@combat_trigs.exact(pattern="Hmmmm. Why must everything be so difficult to figure out?", enabled=True)
def got_aconite(trigger):
    if 'stupidity' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('aconite:stupid')
    trigger.line.gag()
    
@combat_trigs.exact(pattern="You notice that your sweat glands have begun to rapidly secrete a foul, oily substance.", enabled=True)
def got_gecko(trigger):
    if 'slickness' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('gecko:slick')
    trigger.line.gag()

@combat_trigs.exact(pattern="A prickly stinging overcomes your body, fading away into numbness.", enabled=True)
def got_curare(trigger):
    if 'paralysis' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('curare')
        sage.echo((tracker.venoms))
    trigger.line.gag()

@combat_trigs.exact(pattern="Your limbs grow heavy and you groan feebly.", enabled=True)
def got_veranalius(trigger):
    if 'weariness' in player.afflictions:
        tracker.echo_affs()
        tracker.add_venom('vernalius')
    trigger.line.gag()


#################### CURES ########################

### ARGENTUM
@combat_trigs.exact(pattern="You eat an argentum flake.")
def eat_argentum(trigger):
    tracker.add_cured('argentum', trigger.line)
    trigger.line.gag()

@combat_trigs.exact(pattern="Prudence rules your psyche once again.")
def confirm_recklessness(trigger):
    if tracker.confirm_cure('recklessness', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()


### AURUM
@combat_trigs.exact(pattern="You eat an aurum flake.")
def eat_aurum(trigger):
    tracker.add_cured('aurum', trigger.line)
    trigger.line.gag()

@combat_trigs.exact(pattern="Your bronchial tubes open up and your asthma is cured.")
def confirm_asthma(trigger):
    if tracker.confirm_cure('asthma', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()

@combat_trigs.exact(pattern="Your limbs strengthen and you feel stronger.")
def confirm_weariness(trigger):
    if tracker.confirm_cure('weariness', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()

@combat_trigs.exact(pattern="Thank Maya, the Great Mother! Your clumsiness has been cured.")
def confirm_clumsiness(trigger):
    if tracker.confirm_cure('clumsiness', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()


### PLUMBUM
@combat_trigs.exact(pattern="You eat a plumbum flake.")
def eat_plumbum(trigger):
    tracker.add_cured('plumbum', trigger.line)
    trigger.line.gag()

@combat_trigs.exact(pattern="Your shyness has been cured. You can now face the world boldly.")
def confirm_shyness(trigger):
    if tracker.confirm_cure('shyness', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()
    
@combat_trigs.exact(pattern="You are no longer dizzy.")
def confirm_dizziness(trigger):
    if tracker.confirm_cure('dizziness', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()
    
@combat_trigs.exact(pattern="You aren't such a complete idiot anymore.")
def confirm_stupidity(trigger):
    if tracker.confirm_cure('stupidity', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()




### FERRUM
@combat_trigs.exact(pattern="You eat a ferrum flake.")
def eat_ferrum(trigger):
    tracker.add_cured('ferrum', trigger.line)
    trigger.line.gag()

@combat_trigs.exact(pattern="No longer will the sunlight harm you.")
def confirm_darkshade(trigger):
    if tracker.confirm_cure('darkshade', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()


@combat_trigs.exact(pattern="Your stomach becalms itself.")
def confirm_nausea(trigger):
    if tracker.confirm_cure('nausea', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()

@combat_trigs.exact(pattern="Your terrible addiction seems to wane.")
def confirm_addiction(trigger):
    if tracker.confirm_cure('addiction', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()




### MAGNESIUM
@combat_trigs.exact(pattern="You eat a magnesium chip.")
def eat_magnesium(trigger):
    tracker.add_cured('magnesium', trigger.line)
    trigger.line.gag()

@combat_trigs.exact(pattern="Your muscles unlock; you are no longer paralysed.")
def confirm_paral(trigger):
    if tracker.confirm_cure('paralysis', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()

@combat_trigs.exact(pattern="The stinging feeling fades.")
def confirm_sensitivity(trigger):
    if tracker.confirm_cure('sensitivity', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()

### REALGAR
@combat_trigs.exact(pattern="You take a long drag of realgar off your pipe.")
def smoke_realgar(trigger):
    tracker.add_cured('realgar', trigger.line)
    trigger.line.gag()
    
@combat_trigs.exact(pattern="You no longer will inspire disloyalty among friends.")
def confirm_disloyalty(trigger):
    if tracker.confirm_cure('disloyalty', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()
    
@combat_trigs.exact(pattern="Your glands cease their oily secretion.")
def confirm_slickness(trigger):
    if tracker.confirm_cure('slickness', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()
    


### MENDING
@combat_trigs.exact(pattern="You take out some salve and quickly rub it on your arms.")
def mend_arms(trigger):
    tracker.add_cured('mending', trigger.line)
    trigger.line.gag()

@combat_trigs.exact(pattern="The bones in your left arm mend.")
def confirm_leftarm(trigger):
    if tracker.confirm_cure('brokenleftarm', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()

@combat_trigs.exact(pattern="The bones in your right arm mend.")
def confirm_rightarm(trigger):
    if tracker.confirm_cure('brokenrightarm', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()
    
@combat_trigs.exact(pattern="You take out some salve and quickly rub it on your legs.")
def mend_legs(trigger):
    tracker.add_cured('mending', trigger.line)
    trigger.line.gag()

@combat_trigs.exact(pattern="The bones in your left leg mend.")
def confirm_leftleg(trigger):
    if tracker.confirm_cure('brokenleftleg', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()

@combat_trigs.exact(pattern="The bones in your right leg mend.")
def confirm_rightleg(trigger):
    if tracker.confirm_cure('brokenrightleg', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()


### EPIDERMAL
@combat_trigs.exact(pattern="You take out some salve and quickly rub it on your body.")
def mend_body(trigger):
    tracker.add_cured('epidermal', trigger.line)
    tracker.add_cured('mending', trigger.line)
    trigger.line.gag()

@combat_trigs.exact(pattern="Food is no longer repulsive to you.")
def confirm_anorexia(trigger):
    if tracker.confirm_cure('anorexia', trigger.line):
        trigger.gag_prompt=True
    trigger.line.gag()


def echo_aff(signal,affliction):
    sage.echo(ansi.bold_red("ADDED AFFLICTION: %s"%affliction))

def echo_aff_rem(signal,affliction):
    sage.echo(ansi.bold_green("REMOVED AFFLICTION: %s"%affliction).encode('utf-8'))



### chatter
chatter_trigs = triggers.create_group('chatter', app='combat')
chatter_aliases  = aliases.create_group('chatteral', app='combat')

@chatter_aliases.exact('chatteron', enabled=True)
def chatteron(alias):
    sage.echo("Enabling filter for combat chatter")
    chatter_trigs.enable()

@chatter_aliases.exact('chatteroff', enabled=True)
def chatteroff(alias):
    sage.echo("Disabling filter for combat chatter")
    chatter_trigs.disable()

@chatter_trigs.regex(pattern="^([A-Z][a-z]+) takes a drink from .*.$", enabled=True)
def drinkstuff(trigger):
    trigger.gag_prompt=True
    trigger.line.gag()

@chatter_trigs.regex(pattern="^([A-Z][a-z]+) takes a long drag off (his|her) pipe.$", enabled=True)
def smokestuff(trigger):
    trigger.gag_prompt=True
    trigger.line.gag()

@chatter_trigs.regex(pattern="A great weight seems to have been lifted from ^([A-Z][a-z]+).$", enabled=True)
def massoff(trigger):
    trigger.gag_prompt=True
    trigger.line.gag()

@chatter_trigs.regex(pattern="^([A-Z][a-z]+)'s aura of weapons rebounding disappears.$", enabled=True)
def rebon(trigger):
    trigger.gag_prompt=True
    trigger.line.gag()

@chatter_trigs.regex(pattern="^([A-Z][a-z]+) inhales and begins holding (his|her) breath.$", enabled=True)
def holdbreathon(trigger):
    trigger.gag_prompt=True
    trigger.line.gag()

@chatter_trigs.regex(pattern="^([A-Z][a-z]+) exhales loudly.$", enabled=True)
def holdbreathoff(trigger):
    trigger.gag_prompt=True
    trigger.line.gag()


post_prompt.connect(tracker.end)
affliction_add.connect(echo_aff)
affliction_remove.connect(echo_aff_rem)

