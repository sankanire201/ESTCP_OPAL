"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

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


def LoadProrityAgent(config_path, **kwargs):
    """Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.

    :type config_path: str
    :returns: Loadprorityagent
    :rtype: Loadprorityagent
    """
    try:
        config = utils.load_config(config_path)
    except StandardError:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = int(config.get('setting1', 1))
    setting2 = config.get('setting2', "some/random/topic")
    setting4 = config.get('setting4', '~/Config/Buildings_Config.csv')

    return Loadprorityagent(setting1,
                          setting2,setting4,
                          **kwargs)

def listen(client, userdata, message):
    global message1
    message1=message
    if message.topic=="devices/wemo_c/shed":
        Loadprorityagent.Shedding_Command=1
   	Loadprorityagent.User_Command=1
	Loadprorityagent.Shedding_Amount=message.payload
def connect(client, userdata, flags,rc):
    _log.debug("#######################MQTT client is connected###################")   

class Loadprorityagent(Agent):
    """
    Document agent constructor here.
    """
    User_Command=0
    Shedding_Command=0
    Aggregrator_Command=0
    Shedding_Amount=200

    def __init__(self, setting1=1, setting2="some/random/topic",setting4='/home/pi/Config/Buildings_Config.csv',
                 **kwargs):
        super(Loadprorityagent, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.setting1 = setting1
        self.setting2 = setting2
	self.csv_path=setting4

        self.default_config = {"setting1": setting1,
                               "setting2": setting2}
        self.client1= paho.Client("control1")
        self.client1.on_connect=connect
        self.client1.on_message=listen
        self.client1.connect("127.0.0.1",1883)
        self.client1.subscribe("devices/wemo_c/#")
        self.client1.publish("devices/wemo_c/w000",11)
        self.client1.loop_start()


        #Set a default configuration to ensure that self.configure is called immediately to setup
        #the agent.
        self.vip.config.set_default("config", self.default_config)
        #Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
        self.WeMo_Actual_Status={}
        self.WeMo_Scheduled_Status={}
        self.WeMo_Priorities=defaultdict(list)
        self.WeMo_Topics={}
        self.WeMo_Consumption={}
        self.WeMo_cc={}
        self.WeMo_respond_list={}
        self.Power_Consumption_Upper_limit=1000000
        Temp1={}
        Temp2={}
        csv_path='/home/pi/Config/Building_Config.csv'
        WeMo_Priorities={}
	config_dict = utils.load_config('/home/pi/Config/Buildings_Config.csv')

        if os.path.isfile(self.csv_path):
       	 with open(self.csv_path, "r") as csv_device:
	     pass
             reader = DictReader(csv_device)
	         
         #iterate over the line of the csv
         
             for point in reader:
                     ##Rading the lines for configuration parameters
                     Name = point.get("cc")
                     Priority = point.get("Priority")
                     Building = point.get("Building")
                     Cluster_Controller = point.get("cc")
                     Consumption = point.get("Consumption")
                     
                     #This is the topic that use for RPC call
                     Topic=Building+"/"+Name
                     if Name=='\t\t\t':
                         pass
                     else:
                         self.WeMo_Actual_Status[Name]=0
                         self.WeMo_Priorities[int(Priority)].append([Name,int(Consumption)])
                         self.WeMo_Topics[Name]=Topic
                         self.WeMo_Consumption[Name]=Consumption
			 
                             
                         
                     
        else:
            # Device hasn't been created, or the path to this device is incorrect
            raise RuntimeError("CSV device at {} does not exist".format(self.csv_path))
        self.core.periodic(10,self.Load_Priority)
                 

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
            setting1 = int(config["setting1"])
            setting2 = str(config["setting2"])
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return

        self.setting1 = setting1
        self.setting2 = setting2

        self._create_subscriptions(self.setting2)

    def _create_subscriptions(self, topic):
        #Unsubscribe from everything.
        self.vip.pubsub.unsubscribe("pubsub", None, None)

        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topic,
                                  callback=self._handle_publish)

    def _handle_publish(self, peer, sender, bus, topic, headers,
                                message):
        pass

    def Send_Request(self,WeMo,CC):
        ## Sending commandes to the wemo cluster controller
        try:
            print("sending requests to cluster controller for "+self.WeMo_Topics[WeMo])
            #self.WeMo_Scheduled_Status[WeMo]
            result=self.vip.rpc.call('platform.driver','set_point', self.WeMo_Topics[WeMo],'Control1',1).get(timeout=60)
            result=self.vip.rpc.call('platform.driver','set_point', self.WeMo_Topics[WeMo],'Control1',self.WeMo_Scheduled_Status[WeMo]).get(timeout=60)
            print('RPC call reply is '+str(result))
            return result
        except :
               print("somthing happend")
               return "error"
 

    def Sort_WeMo_List(self):
        
        sorted_x= sorted(self.WeMo_Priorities.items(), key=operator.itemgetter(0),reverse=False) # Sort ascending order (The lowest priority is first)
        self.WeMo_Priorities = collections.OrderedDict(sorted_x)
        #print(self.WeMo_Priorities )

        
    def Read_WeMo_Power_Consumption(self,WeMo):
        try:
            result=self.vip.rpc.call('platform.driver','get_point', self.WeMo_Topics[WeMo],'Inv_output_current').get(timeout=60)
            print("The Building consumption is :" + str(result))
            return result
        except :
               return 0
             
    def Read_Total_Power_Consumption(self):
        result=0
        for x in self.WeMo_Actual_Status.keys():
            result=self.Read_WeMo_Power_Consumption(x)+result

        print("##########################################Total consumption is "+str(result))
        return result
            

    def Send_WeMo_Schedule(self):
        temp={}
        if bool(self.WeMo_Scheduled_Status)==True:
            #for x in self.WeMo_Actual_Status.keys():
               # if x in   self.WeMo_Scheduled_Status:
                 #   pass
                #else :
                   # self.WeMo_Scheduled_Status[x]=1

            for y in self.WeMo_Scheduled_Status:
                WeMo=self.Send_Request(y,1)
                if WeMo=="error":
                    pass
                else :
                   self.WeMo_respond_list[y]=y
                   print("Buliding_respond_list"+str(self.WeMo_respond_list))
                
            for ybar in self.WeMo_respond_list:
                del self.WeMo_Scheduled_Status[ybar]
        self.WeMo_respond_list.clear()
        
        
    def Schedule_WeMo(self):

        Scheduled_WeMo_Consumption=0 # final wemo 
        Temp_WeMo_Schedule={}#self.WeMo_Scheduled_Status # dummy vaiable for storing weMo status after going through the priority grouping
        
        for x,y in self.WeMo_Priorities.items():
            #print(x)
           # print(y)
            Wemo_Power_Consumption_List={} # variable that stores sorted WeMo power consumption
            total=0
            for P in y:
                result=self.Read_WeMo_Power_Consumption(P[0])
                Wemo_Power_Consumption_List[P[0]]=result
                total=result+total
            
            Pval=Wemo_Power_Consumption_List.values()
            Pkey=Wemo_Power_Consumption_List.keys()
            Scheduled_Total__WeMo_Consumption=int(self.Power_Consumption_Upper_limit)+int(Loadprorityagent.Shedding_Amount)
            print("WeMoooooo consumptionnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn"+str(self.Power_Consumption_Upper_limit)+"hhhhhhhhhhhh"+str(Loadprorityagent.Shedding_Amount))
            

            for y in Wemo_Power_Consumption_List.values():
                Scheduled_Total__WeMo_Consumption= Scheduled_Total__WeMo_Consumption-min(Pval) # Allocate the load consumption to the current load consumption based on the priority and the amount of the power consumption of the WeMO variable
                Temp_WeMo_Schedule[Pkey[Pval.index(min(Pval))]]=0
                del Pkey[Pval.index(min(Pval))]
                del Pval[Pval.index(min(Pval))]
                if int(self.Power_Consumption_Upper_limit)>Scheduled_Total__WeMo_Consumption:
                   				 break
                

                 
            if int(self.Power_Consumption_Upper_limit)>Scheduled_Total__WeMo_Consumption:
                   			break

        return Temp_WeMo_Schedule
    
    def Check_Shedding_condition(self):
        total_consumption=self.Read_Total_Power_Consumption()
        self.publish_to_sql(self.Power_Consumption_Upper_limit,total_consumption,Loadprorityagent.Shedding_Amount)
        if Loadprorityagent.Shedding_Command == 1 :
            self.Power_Consumption_Upper_limit=total_consumption-int(Loadprorityagent.Shedding_Amount)
        if self.Power_Consumption_Upper_limit<0:
            self.Power_Consumption_Upper_limit=0
        if total_consumption>int(self.Power_Consumption_Upper_limit):
            return 1
        else:
            return 0
        
    def publish_to_sql(self,Power_Consumption_Upper_limit,total,Shedding_Amount):
        utcnow = utils.get_aware_utc_now()
        Header= {
    # python code to get this is
    # from datetime import datetime
    # from volttron.platform.messaging import headers as header_mod
    # from volttron.platform.agent import utils
    # now = utils.format_timestamp( datetime.utcnow())
    # {
    #     headers_mod.DATE: now,
    #     headers_mod.TIMESTAMP: now
    # }
         "Date": utils.format_timestamp(utcnow),
         "TimeStamp":utils.format_timestamp(utcnow)
        }

        #headers['time'] = utils.format_timestamp(utcnow)
       # Message={"Total_WeMo_Consumption": {"Readings": [utils.format_timestamp(utcnow),total],"Units": "Kw","tz": "UTC","data_type": "int"}}
        Message= {"Total_WeMo_Power_Consumption": total,"Power_Consumption_Upper_limit":Power_Consumption_Upper_limit,"Shedding_Amount":Shedding_Amount}
        self.vip.pubsub.publish(peer='pubsub',topic= 'devices/BMS/WeMO/all',headers=Header, message=Message)

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

    @RPC.export
    def rpc_method(self, arg1, arg2, kwarg1=None, kwarg2=None):
        """
        RPC method

        May be called from another agent via self.core.rpc.call """
        return self.setting1 + arg1 - arg2
    def Load_Priority(self):
        ### This function runs the GROUP NIRE'S load's priority algorithem
        
        over_consumption_flag=self.Check_Shedding_condition()
        ## Sort the WeMos based on the priority ratings
        #self.Read_Total_Power_Consumption()
        self.Sort_WeMo_List()
        

        if Loadprorityagent.Shedding_Command == 1 or over_consumption_flag==1:
            
            self.WeMo_Scheduled_Status=self.Schedule_WeMo()
            
            Loadprorityagent.Shedding_Command=0
            print(self.WeMo_Scheduled_Status)
        else:
            pass
        
        self.Send_WeMo_Schedule()
                        
        print(str(Loadprorityagent.Shedding_Command)+'*******************************end of the function*************************'+str(self.WeMo_Scheduled_Status))
        
def main():
    """Main method called to start the agent."""
    utils.vip_main(LoadProrityAgent, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
