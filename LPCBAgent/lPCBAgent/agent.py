"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

import datetime
from datetime import datetime
import time
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


def lPCBAgent(config_path, **kwargs):
    """Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.

    :type config_path: str
    :returns: Lpcbagent
    :rtype: Lpcbagent
    """
    try:
        config = utils.load_config(config_path)
    except StandardError:
        config = {}
        

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = int(config.get('setting1', 1))
    setting2 = config.get('setting2', "some/random/topic")

    return Lpcbagent(setting1,
                          setting2,
                          **kwargs)


class Lpcbagent(Agent):
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

    def __init__(self, setting1=1, setting2="some/random/topic",
                 **kwargs):
        super(Lpcbagent, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.setting1 = setting1
        self.setting2 = setting2

        self.default_config = {"setting1": setting1,
                               "setting2": setting2}
        self.vip.config.set_default("config", self.default_config)
        #Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
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
        csv_path='/home/sanka/volttron/LPCBAgent/Buildings_Config.csv'
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
                         Name=Name+"_"+Building
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
            setting1 = int(config["setting1"])
            setting2 = config["setting2"]
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return

        self.setting1 = setting1
        self.setting2 = setting2

        for x in self.setting2:
            self._create_subscriptions(str(x))
            print(str(x))
            

    def _create_subscriptions(self, topic):
        #Unsubscribe from everything.
        self.vip.pubsub.unsubscribe("pubsub", None, None)

        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topic,
                                  callback=self._handle_publish,all_platforms=True)

    def _handle_publish(self, peer, sender, bus, topic, headers,
                                message):
        now = utils.format_timestamp(datetime.utcnow())
        utcnow = utils.get_aware_utc_now()
 
        header = {
        #    headers_mod.CONTENT_TYPE: headers_mod.CONTENT_TYPE.PLAIN_TEXT,
            "Date": utils.format_timestamp(utcnow),
            "TimeStamp":utils.format_timestamp(utcnow)
        }
        x=topic.find('Monitor')
        if x>0:
            BEMStag=topic.split("/")
            index=BEMStag[-2]
            self.loads_consumption[index]=int((message[0])['Main_P'])
            self.WeMo_Actual_Status[index]=int((message[0])['Main_S'])
            if self.loads_max_consumption[index]< self.loads_consumption[index]:
                self.loads_max_consumption[index]=self.loads_consumption[index]
           # print(self.loads_max_consumption)
           
            
            values=self.loads_consumption.values()
            self.total_consumption=sum(values)
            self.Priority_Consumption[self.WeMo_Priority_increment[index]][index]=int((message[0])['Main_P'])
            self.Priority_group_Consumption[self.WeMo_Priority_increment[index]]=sum(self.Priority_Consumption[self.WeMo_Priority_increment[index]].values())
        

            topics = "devices/Centralcontrol/Monitor/prioritygroupconsumption/"+str(self.WeMo_Priority_increment[index])+'/all'
            Message={"value":self.Priority_group_Consumption[self.WeMo_Priority_increment[index]],"Total_group_sum":self.total_consumption}
            result = self.vip.pubsub.publish(peer='pubsub',topic=topics, headers=header,message= Message)          
            print("########################################################################Power Consumption for Building############################", self.Priority_Consumption,self.Priority_group_Consumption,self.total_consumption)
        else:
            pass
        if topic=="control/plc/shedding":
            self.event_control_trigger=1
            Lpcbagent.Shedding_Command=1
            Lpcbagent.User_Command=1
            Lpcbagent.Shedding_Amount=int(message)
            self.Check_Shedding_condition()
            self.Sort_WeMo_List()            
            self.WeMo_Scheduled_Status=self.Schedule_Shedding_Control_WeMo()
            print(self.WeMo_Scheduled_Status)
            self.Send_WeMo_Schedule()
            
            print("########################################################################Shedding Signal Recived############################",int(message))
            self.event_control_trigger=0
        if topic=="control/plc/directcontrol":
            self.event_control_trigger=1
            Lpcbagent.Shedding_Command=1
            Lpcbagent.User_Command=1
            Lpcbagent.Direct_Control_Mode=int(message)
            self.Check_Shedding_condition()
            self.Sort_WeMo_List()            
            self.WeMo_Scheduled_Status=self.Schedule_Direct_Control_WeMo()
            self.Send_WeMo_Schedule()
            print(self.WeMo_Scheduled_Status)
            print("########################################################################Direct control Signal Recived############################",int(message))
            self.event_control_trigger=0
        if topic=="control/plc/increment":
            self.event_control_trigger=1
            Lpcbagent.Increment_Control=1
            Lpcbagent.Increment_Amount=int(message)
            self.Check_Shedding_condition()
            self.Sort_WeMo_List()  
            self.WeMo_Scheduled_Status=self.Schedule_Increment_Control_WeMo()
            self.Send_WeMo_Schedule()
            print(self.WeMo_Scheduled_Status)
            
            print("########################################################################Increment control Signal Recived############################",int(message))
            self.event_control_trigger=0
        else:
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
        #Example publish to pubsub
        #self.vip.pubsub.publish('pubsub', "some/random/topic", message="HI!")

        #Exmaple RPC call
        #self.vip.rpc.call("some_agent", "some_method", arg1, arg2)


    def Send_Request(self,WeMo,CC):
        now = utils.format_timestamp(datetime.utcnow())
        utcnow = utils.get_aware_utc_now()
 
        header = {
        #    headers_mod.CONTENT_TYPE: headers_mod.CONTENT_TYPE.PLAIN_TEXT,
            "Date": utils.format_timestamp(utcnow),
            "TimeStamp":utils.format_timestamp(utcnow)
        }
 
        ## Sending commandes to the wemo cluster controller
        try:
                            
            topics=self.WeMo_Topics[WeMo]
            result = self.vip.pubsub.publish(peer='pubsub',topic=topics,headers=header, message=self.WeMo_Scheduled_Status[WeMo])
            '''if self.WeMo_Scheduled_Status[WeMo]==0:
                result = self.vip.pubsub.publish(peer='pubsub',topic=topics,headers=header, message=1)
                time.sleep(.2)
                result = self.vip.pubsub.publish(peer='pubsub',topic=topics,headers=header, message=0)
                print("off") 
            if self.WeMo_Scheduled_Status[WeMo]==1:
                result = self.vip.pubsub.publish(peer='pubsub',topic=topics,headers=header, message=0)
                time.sleep(.2)
                result = self.vip.pubsub.publish(peer='pubsub',topic=topics,headers=header, message=1)
                print("on") '''
            
#            if result['status']==11:
#                print('Wemo is not responded')
#                return 0
            
                #del self.WeMo_Scheduled_Status[WeMo]
            print(self.WeMo_Scheduled_Status)
            return WeMo
        except:
            print("somthing happend")
            return 0
 

    def Send_WeMo_Schedule(self):
       
        if bool(self.WeMo_Scheduled_Status)==True:
            #for x in self.WeMo_Actual_Status.keys():
                #if x in   self.WeMo_Scheduled_Status:
                 #   pass
                #else :
                  #  self.WeMo_Scheduled_Status[x]=1

            for y in self.WeMo_Scheduled_Status:            
                WeMo=self.Send_Request(y,1)
                if WeMo==0:
                #print('*************************************************************Recieved1*************************************************************')
                    pass
                else :
                #print(y+'*************************************************************Recieved2*************************************************************'+WeMo)
                   self.WeMo_respond_list[WeMo]=WeMo
                   print("WeMo_respond_list"+str(self.WeMo_respond_list))
                
            for ybar in self.WeMo_respond_list:
                # print(ybar+'*************************************************************deleting*************************************************************')
                     print(self.WeMo_Scheduled_Status)
                     del self.WeMo_Scheduled_Status[ybar]
            Lpcbagent.Shedding_Amount=0
                 
        self.WeMo_respond_list.clear()

    def Sort_WeMo_List(self):

        sorted_x= sorted(self.WeMo_Priorities.items(), key=operator.itemgetter(0),reverse=False) # Sort ascending order (The lowest priority is first)
        self.WeMo_Priorities = collections.OrderedDict(sorted_x)
        #print(self.WeMo_Priorities )

    def Check_Shedding_condition(self):
        total_consumption=self.total_consumption
        self.Power_Consumption_Upper_limit=total_consumption-int(Lpcbagent.Shedding_Amount)
        if self.Power_Consumption_Upper_limit<0:
            self.Power_Consumption_Upper_limit=0
        print('uppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppper',str(self.Power_Consumption_Upper_limit),Lpcbagent.Shedding_Amount)
                

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
    def Schedule_Direct_Control_WeMo(self):
        print('********************direct control initialized****************************')
        Temp_WeMo_Schedule={}#self.WeMo_Scheduled_Status # dummy vaiable for storing weMo status after going through the priority grouping
        
        for y in self.WeMo_Actual_Status:
            #print(x)
            #print(y)
            
            if Lpcbagent.Direct_Control_Mode==1:
                    Temp_WeMo_Schedule[y]=1 
            if Lpcbagent.Direct_Control_Mode==0:
                    Temp_WeMo_Schedule[y]=0
            if Lpcbagent.Direct_Control_Mode==2:
                    Temp_WeMo_Schedule[y]=2
            else:
                    pass
        return Temp_WeMo_Schedule
                    
    def Schedule_Increment_Control_WeMo(self):
        print('********************Increment control initialized****************************')
        Temp_WeMo_Schedule={}
        Temp_Off_WeMos=defaultdict(list)
        for x in self.WeMo_Actual_Status:
              if self.WeMo_Actual_Status[x]==0:
                  Temp_Off_WeMos[int(self.WeMo_Priority_increment[x])].append([x,int(self.loads_max_consumption[x])])
              else:
                  pass
         #if bool(Temp_Off_WeMos[x])==True:
        consumption=0
        while bool(Temp_Off_WeMos)==True:
            for y in Temp_Off_WeMos[max(Temp_Off_WeMos.keys())]:
                consumption=y[1]+consumption
                
                if consumption >= Lpcbagent.Increment_Amount:
                    break;
                Temp_WeMo_Schedule[y[0]]=2
            if consumption >= Lpcbagent.Increment_Amount:
                break;
            
            del Temp_Off_WeMos[max(Temp_Off_WeMos.keys())]
        print('consumption',consumption,self.loads_max_consumption)
        print('off_wemos',Temp_Off_WeMos)
        return Temp_WeMo_Schedule

                           
               
        

    def Load_Priority(self):
        ### This function runs the GROUP NIRE'S load's priority algorithem
      print('*************************************************************Startingggggg*************************************************************',str(self.total_consumption))


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
    @RPC.export
    def direct_load_control(self, arg1, kwarg1=None, kwarg2=None):
        """
        RPC methodself.WeMo_Scheduled_Status
        
        May be called from another agent via self.core.rpc.call """
        k=0
        print('herer is the message@@@@@@@@@@@@@@@@@@',arg1)
        for y in arg1:
            k=k+1
            p='BEMS_'+str(k)
            self.WeMo_Scheduled_Status[p]=y
            print(self.WeMo_Scheduled_Status[p])
        self.Send_WeMo_Schedule()
        
        return 1
    

def main():
    """Main method called to start the agent."""
    utils.vip_main(lPCBAgent, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
