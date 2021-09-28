"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'


import datetime
from datetime import datetime
import time
import random
import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
#from paho.mqtt.client import MQTTv311, MQTTv31
#import paho.mqtt.publish as publish
#import paho.mqtt.client as paho
#from paho.mqtt.subscribe import callback
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


def lPCAgent_GM(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: LpcagentGm
    :rtype: LpcagentGm
    """
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = int(config.get('setting1', 1))
    setting2 = config.get('setting2', "some/random/topic")

    return LpcagentGm(setting1, setting2, **kwargs)


class LpcagentGm(Agent):
    """
    Document agent constructor here.
    """
    User_Command=0
    Shedding_Command=0
    Aggregrator_Command=0
    Shedding_Amount=0
    Direct_Control=0
    Direct_Control_Mode=0
    Increment_Control=0
    Increment_Amount=0


    def __init__(self, setting1=1, setting2="some/random/topic", **kwargs):
        super(LpcagentGm, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.setting1 = setting1
        self.setting2 = setting2

        self.default_config = {"setting1": setting1,
                               "setting2": setting2}

        # Set a default configuration to ensure that self.configure is called immediately to setup
        # the agent.
        self.WeMo_Actual_Status={}
        self.WeMo_Scheduled_Status={}
        self.WeMo_Priorities=defaultdict(list)
        self.WeMo_Power_Consumption_Sql={}
        self.WeMo_Topics={}
        self.Priority_Consumption={}
        self.Priority_group_Consumption={}
        self.WeMo_Consumption={}
        self.WeMo_cc={}
        self.WeMo_respond_list={}
        self.WeMo_Priority_increment={}
        self.Power_Consumption_Upper_limit=1000000
        Temp1={}
        Temp2={}
        csv_path= '/home/pi/volttron/LPCAgent_GM/Buildings_Config.csv'
        WeMo_Priorities={}
	#config_dict = utils.load_config('/home/sanka/volttron/LPCBAgent/Building_Config.csv')
        self.loads_consumption={}
        self.loads_max_consumption={}
        self.total_consumption=0
        self.event_control_trigger=0

        if os.path.isfile(csv_path):
       	 with open(csv_path, "r") as csv_device:
             pass
             reader = DictReader(csv_device)
	         
         #iterate over the line of the csv
         
             for point in reader:
                     ##Rading the lines for configuration parameters
                     Name = point.get("Name")
                     Priority = point.get("Priority")
                     Building = point.get("Building")
                     Microgrid = point.get("Microgrid")
                     Consumption = point.get("Consumption")
                     
                     

                     #This is the topic that use for RPC call
                     Topic='devices/control/'+Name+'_'+Building+'/plc/shedding'
                     print(Topic)
                     if Name=='\t\t\t':
                         pass
                     else:
                         self.WeMo_Actual_Status[Name]=0
                         self.WeMo_Priorities[int(Priority)].append([Name,int(Consumption)])
                         self.WeMo_Topics[Name]=Topic
                         self.WeMo_Consumption[Name]=Consumption
                         self.WeMo_cc[Name]=Building
                         self.WeMo_Power_Consumption_Sql[Name]=0
                         self.loads_max_consumption[Name]=0
                         self.WeMo_Priority_increment[Name]=int(Priority)
                         self.loads_consumption[Name]=0
             for x in self.WeMo_Priorities:
                temp={}
                for y in self.WeMo_Priorities[x]:
                    temp[y[0]]=0
                    
                self.Priority_Consumption[x]=temp
                self.Priority_group_Consumption[x]=0
                
            
         
			 
                             
                         
                     
        else:
            # Device hasn't been created, or the path to this device is incorrect
            raise RuntimeError("CSV device at {} does not exist".format(csv_path))
        self.core.periodic(30,self.Load_Priority)                 
        
        self.vip.config.set_default("config", self.default_config)
        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

    def configure(self, config_name, action, contents):
        """
        Called after the Agent has connected to the message bus. If a configuration exists at startup
        this will be called before onstart.

        Is called every time the configuration in the store changes.
        """
        config = self.default_config.copy()
        config.update(contents)

        _log.debug("***************Configuring Agent**************")

        try:
            setting1 = int(config["setting1"])
            setting2 = config["setting2"]
            print('##################',setting2,'################' )
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return

        self.setting1 = setting1
        self.setting2 = setting2

        for x in self.setting2:
            self._create_subscriptions(str(x))
            print(str(x))
            

    def _create_subscriptions(self, topic):
        """
        Unsubscribe from all pub/sub topics and create a subscription to a topic in the configuration which triggers
        the _handle_publish callback
        """
        self.vip.pubsub.unsubscribe("pubsub", None, None)

        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topic,
                                  callback=self._handle_publish)

    def _handle_publish(self, peer, sender, bus, topic, headers, message):
        print(sender)
       # result = topic.find("BEMS_3")
        if sender== 'platform.driver' :
            x=list(bin((message[0])['DecG1'])[2:])
            k=0
            total=0
            for y in x:
                k=k+1
                tag='G1_'+str(k)
                total=int(y)*int(self.WeMo_Consumption[tag])+total
            print(total)
            x=list(bin((message[0])['DecG2'])[2:])
            k=0
            total=0
            for y in x:
                k=k+1
                tag='G2_'+str(k)
                total=int(y)*int(self.WeMo_Consumption[tag])+total
            print(total)
            x=list(bin((message[0])['DecG3'])[2:])
            k=0
            total=0
            for y in x:
                k=k+1
                tag='G3_'+str(k)
                total=int(y)*int(self.WeMo_Consumption[tag])+total
            print(total)            
            x=list(bin((message[0])['DecG4'])[2:])
            k=0
            total=0
            for y in x:
                k=k+1
                tag='G4_'+str(k)
                total=int(y)*int(self.WeMo_Consumption[tag])+total
            print(total)            
            x=list(bin((message[0])['DecG5'])[2:])
            k=0
            total=0
            for y in x:
                k=k+1
                tag='G5_'+str(k)
                total=int(y)*int(self.WeMo_Consumption[tag])+total
            print(total)            
            
            print(list(bin((message[0])['DecG2'])[2:]))
            print(list(bin((message[0])['DecG3'])[2:]))
            print(list(bin((message[0])['DecG4'])[2:]))
            print(list(bin((message[0])['DecG5'])[2:]))
        """
        Callback triggered by the subscription setup using the topic from the agent's config file
        """
        pass

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        # Example publish to pubsub
        self.vip.pubsub.publish('pubsub', "some/random/topic", message="HI!")

        # Example RPC call
        # self.vip.rpc.call("some_agent", "some_method", arg1, arg2)
        pass

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        pass

    @RPC.export
    def rpc_method(self, arg1, arg2, kwarg1=None, kwarg2=None):
        """
        RPC method

        May be called from another agent via self.core.rpc.call
        """
        return self.setting1 + arg1 - arg2
    def Sort_WeMo_List(self):

        sorted_x= sorted(self.WeMo_Priorities.items(), key=operator.itemgetter(0),reverse=False) # Sort ascending order (The lowest priority is first)
        self.WeMo_Priorities = collections.OrderedDict(sorted_x)
        #print(self.WeMo_Priorities )


    def Check_Shedding_condition(self):
        total_consumption=self.total_consumption
        self.Power_Consumption_Upper_limit=total_consumption-int(LpcagentGm.Shedding_Amount)
        if self.Power_Consumption_Upper_limit<0:
            self.Power_Consumption_Upper_limit=0
        print('uppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppper',str(self.Power_Consumption_Upper_limit),Loadprorityagent.Shedding_Amount)
                
    
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
                           
    def Load_Priority(self):
        x=random.randrange(0,31)
        try:
            result=0
            x=x+1
            result=self.vip.rpc.call('platform.driver','set_point', 'Campus1/Benshee1/BEMS_3' ,'G1',x).get(timeout=20)
            print(result,'G1')
        except:
            print("somthing")
        try:
            result=0
            x=x+1
            result=self.vip.rpc.call('platform.driver','set_point', 'Campus1/Benshee1/BEMS_3' ,'G2',x).get(timeout=20)
            print(result,'G2')
        except:
            print("somthing")
        try:
            result=0
            x=x+1
            result=self.vip.rpc.call('platform.driver','set_point', 'Campus1/Benshee1/BEMS_3' ,'G3',x).get(timeout=20)
            print(result,'G3')
        except:
            print("somthing")
        try:
            result=0
            x=x+1
            result=self.vip.rpc.call('platform.driver','set_point', 'Campus1/Benshee1/BEMS_3' ,'G4',x).get(timeout=20)
            print(result,'G4')
        except:
            print("somthing")
        try:
            result=0
            x=x+1
            result=self.vip.rpc.call('platform.driver','set_point', 'Campus1/Benshee1/BEMS_3' ,'G5',x).get(timeout=20)
            print(result,'G5')
        except:
            print("somthing")
        """
        x=random.randrange(0,31)
        result=self.vip.rpc.call('platform.driver','set_point', 'Campus1/Benshee1/BEMS_3' ,'G2',x)
        x=random.randrange(0,31)
        result=self.vip.rpc.call('platform.driver','set_point', 'Campus1/Benshee1/BEMS_3' ,'G3',x)
        x=random.randrange(0,31)
        result=self.vip.rpc.call('platform.driver','set_point', 'Campus1/Benshee1/BEMS_3' ,'G4',x)
        x=random.randrange(0,31)
        result=self.vip.rpc.call('platform.driver','set_point', 'Campus1/Benshee1/BEMS_3' ,'G5',x)
        """
        



def main():
    """Main method called to start the agent."""
    utils.vip_main(lPCAgent_GM, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
