import meta
import sage
from sage import player, triggers, aliases
from sage.signals import pre_shutdown
from sage.signals.gmcp import skills, vitals
import time
import MySQLdb as mysql
import MySQLdb.cursors

class HealthTracker(object):

    def __init__(self):
        self.health = 100
        self.mana = 100
        self.last_health = 0
        self.last_mana = 0

        self.ema_health_gain = 0
        self.ema_health_loss = 0
        self.cur_health_gain = 0
        self.cur_health_loss = 0

        self.ema_mana_gain = 0
        self.ema_mana_loss = 0
        self.cur_mana_gain = 0
        self.cur_mana_loss = 0


    def update_health_stats(self, **kwargs):
        cur_health = kwargs['health']
        cur_mana   = kwargs['mana']
        self.health = cur_health.value
        self.mana = cur_mana.value

        if self.last_health == 0:
            self.last_health = cur_health.value
            self.last_mana = cur_mana.value
                
        d_health = cur_health.value - self.last_health
        d_mana   = cur_mana.value   - self.last_mana

        if d_health > 0:
            self.cur_health_gain = self.cur_health_gain + d_health
                
        if d_health < 0:
            self.cur_health_loss = self.cur_health_loss - d_health

        if d_mana > 0:
            self.cur_mana_gain = self.cur_mana_gain + d_mana
                
        if d_mana < 0:
            self.cur_mana_loss = self.cur_mana_loss - d_mana

        self.last_health = cur_health.value
        self.last_mana = cur_mana.value
            
    def update_health_gain(self, trigger):
        self.ema_health_gain = self.ema_health_gain *.1 + self.cur_health_gain
        self.ema_health_loss = max(self.ema_health_loss *.1 + .9 * self.cur_health_loss,
                self.cur_health_loss)
        self.cur_health_gain = 0
        self.cur_health_loss = 0

        self.ema_mana_gain = self.ema_mana_gain *.5 + self.cur_mana_gain
        self.ema_mana_loss = self.ema_mana_loss *.5 + self.cur_mana_loss
        self.cur_mana_gain = 0
        self.cur_mana_loss = 0

tracker = HealthTracker()

health_trigs = triggers.create_group('health', app='explorer')                                       
health_trigs.enable()                                                                                
@health_trigs.exact("You may drink another health or mana elixir.")                         
def snap_health(trigger):
    tracker.update_health_gain(trigger)
vitals.connect(tracker.update_health_stats)

