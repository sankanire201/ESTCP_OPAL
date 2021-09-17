"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

import datetime
import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
from paho.mqtt.client import MQTTv311, MQTTv31
import paho.mqtt.publish as publish
import paho.mqtt.client as paho
from paho.mqtt.subscribe import callback
from pprint import pformat
from csv import DictReader, DictWriter
import os
import csv
import collections
import operator
from collections import defaultdict

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def lSAgent(config_path, **kwargs):
    """Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.

    :type config_path: str
    :returns: Lsagent
    :rtype: Lsagent
    """
    try:
        config = utils.load_config(config_path)
    except StandardError:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = config.get('setting1', "some_random_path")
    setting2 = config.get('setting2', "some/random/topic")

    return Lsagent(setting1,
                          setting2,
                          **kwargs)


class Lsagent(Agent):
    Shedding_Amount=0
    """
    Document agent constructor here.
    """

    def __init__(self, setting1=1, setting2="some/random/topic",
                 **kwargs):
        super(Lsagent, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.setting1 = setting1
        self.setting2 = setting2

        self.default_config = {"setting1": setting1,
                               "setting2": setting2}

        ## reading th econfiguration files

        self.load_priorities={}
        self.current_schedule=[]
        self.updated_schedule=[]
        self.objective_threashhold=200
        self.Power_Consumption_Upper_limit=0
        self.total_load_consumption=0
        if os.path.isfile(self.setting1):
       	 with open(self.setting1, "r") as csv_device:
	     pass
             reader = DictReader(csv_device)
	         
         #iterate over the line of the csv
         
             for point in reader:
                     Name = point.get("Name")
                     Priority = point.get("Priority")
                     Building = point.get("Building")
                     Cluster_Controller = point.get("cc")
                     Consumption = point.get("Consumption")
                     if Name=='\t\t\t':
                         pass
                     else:
                         Name=Name+"_"+Cluster_Controller
                         self.load_priorities[Name]=Priority

                         
                     
        else:
            # Device hasn't been created, or the path to this device is incorrect
            raise RuntimeError("CSV device at {} does not exist".format(self.csv_path))        


        #Set a default configuration to ensure that self.configure is called immediately to setup
        #the agent.
        self.vip.config.set_default("config", self.default_config)
        #Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

    def configure(self, config_name, action, contents):
        """
        Called after the Agent has connected to the message bus. If a configuration exists at startup
        this will be called before onstart.

        Is called every time the configuration in the store changes.
        """
        config = self.default_config.copy()
        config.update(contents)

        _log.debug("Configuring Agent")

        try:
            setting1 = str(config["setting1"])
            setting2 = config["setting2"]
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return

        #self.setting1 = setting1
        self.setting2 = setting2

        for x in self.setting2:
            print(x)
            self._create_subscriptions(str(x))

    def _create_subscriptions(self, topic):
        #Unsubscribe from everything.
        self.vip.pubsub.unsubscribe("pubsub", None, None)

        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topic,
                                  callback=self._handle_publish)

    def _handle_publish(self, peer, sender, bus, topic, headers,
                                message): 
        
        if type(message) == list:
            self.current_schedule=message
            self.updated_schedule=self.updated_schedule+message
            self.current_load_consumption=self.vip.rpc.call('LoadProrityAgentagent-0.1_1','load_consumption').get(timeout=20)
            self.total_load_consumption=sum(self.current_load_consumption.values())
            estimated_power_consumption=self.estimated_power_consumption(self.updated_schedule)
            print(self.current_load_consumption,estimated_power_consumption,self.total_load_consumption)
            if estimated_power_consumption > self.objective_threashhold:
                temp=self.objective_threahhold-estimated_power_consumption
                self.Check_Shedding_condition()
                print(temp,self.current_load_consumption)
        else:
            print("schedule format is wrong")
        
    def Check_Shedding_condition(self):
        total_consumption=self.current_load_consumption
        self.Power_Consumption_Upper_limit=total_consumption-int(Lsagent.Shedding_Amount)
        if self.Power_Consumption_Upper_limit<0:
            self.Power_Consumption_Upper_limit=0
        print('uppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppper',str(self.Power_Consumption_Upper_limit),Lsagent.Shedding_Amount)
                
    
    def Schedule_Shedding_Control_WeMo(self):
        print('********************shedding control initialized****************************')
        Temp_WeMo_Schedule={}
        Temp_WeMos=defaultdict(list)
        for x in self.WeMo_Actual_Status:
              #if self.WeMo_Actual_Status[x]==0:
              Temp_WeMos[int(self.WeMo_Priority_increment[x])].append([x,int(self.loads_consumption[x])])
              #else:
                  #pass
        print(Temp_WeMos)
        consumption=self.total_consumption
        while bool(Temp_WeMos)==True:
            print(Temp_WeMos[min(Temp_WeMos.keys())])
            
            for y in Temp_WeMos[min(Temp_WeMos.keys())]:
                consumption=consumption-y[1]
                Temp_WeMo_Schedule[y[0]]=0
                del y[y.index(min(y))]
                print(consumption)
                if consumption <= self.Power_Consumption_Upper_limit:
                    break;
            if consumption <= self.Power_Consumption_Upper_limit:
               break;
            del Temp_WeMos[min(Temp_WeMos.keys())]
        print(Temp_WeMos)
        return Temp_WeMo_Schedule
                           

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        #Example publish to pubsub
        #self.vip.pubsub.publish('pubsub', "some/random/topic", message="HI!")

        #Exmaple RPC call
        #self.vip.rpc.call("some_agent", "some_method", arg1, arg2)

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        pass
    def estimated_power_consumption(self,schedule):
        temp=set(schedule)
        total=0
        for x in temp:
            total=total+self.current_load_consumption[x]
            print(total)
        return total
             


    @RPC.export
    def rpc_method(self, arg1, arg2, kwarg1=None, kwarg2=None):
        """
        RPC method

        May be called from another agent via self.core.rpc.call """
        return self.setting1 + arg1 - arg2

def main():
    """Main method called to start the agent."""
    utils.vip_main(lSAgent, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
