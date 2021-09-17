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
    setting4 = config.get('setting4', '/home/sanka/volttron/LoadPrority/WeMo_Config.csv')

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
    Shedding_Amount=0
    Direct_Control=0
    Direct_Control_Mode=0


    def __init__(self, setting1=1, setting2="some/random/topic",setting4='/home/sanka/volttron/LoadPrority/WeMo_Config2.csv',
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
        self.client1.connect("192.168.10.52",1883)
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
        self.WeMo_Power_Consumption_Sql={}
        self.WeMo_Topics={}
        self.WeMo_Consumption={}
        self.WeMo_cc={}
        self.WeMo_respond_list={}
        self.Power_Consumption_Upper_limit=1000000
        Temp1={}
        Temp2={}
        csv_path='/home/sanka/volttron/LoadPrority/WeMo_Config2.csv'
        WeMo_Priorities={}
	config_dict = utils.load_config('/home/sanka/volttron/LoadPrority/WeMo_Config2.csv')
	self.loads_consumption={}
        self.total_consumption=0

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
                     Cluster_Controller = point.get("cc")
                     Consumption = point.get("Consumption")
                     
                     

                     #This is the topic that use for RPC call
                     Topic="acquisition/loads/"+"building"+Cluster_Controller+"/"+Name
                     if Name=='\t\t\t':
                         pass
                     else:
                         Name=Name+"_"+Cluster_Controller
                         self.WeMo_Actual_Status[Name]=0
                         self.WeMo_Priorities[int(Priority)].append([Name,int(Consumption)])
                         self.WeMo_Topics[Name]=Topic
                         self.WeMo_Consumption[Name]=Consumption
                         self.WeMo_cc[Name]=Cluster_Controller
                         self.WeMo_Power_Consumption_Sql[Name]=0
			 
                             
                         
                     
        else:
            # Device hasn't been created, or the path to this device is incorrect
            raise RuntimeError("CSV device at {} does not exist".format(self.csv_path))
        self.core.periodic(30,self.Load_Priority)
                 

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

        for x in self.setting2:
            self._create_subscriptions(str(x))
            
        self.vip.pubsub.subscribe(peer='pubsub',prefix='Wemo_Schedule',callback=self.handle_wemo_schedule_publish)
        

    def _create_subscriptions(self, topic):
        #Unsubscribe from everything.
        self.vip.pubsub.unsubscribe("pubsub", None, None)

        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topic,
                                  callback=self._handle_publish)
        print("########################################################################shedding signal recived############################",topic)

    def handle_wemo_schedule_publish(self, peer, sender, bus, topic, headers,message):
        print("########################################################################WeMO SCHEDULE RECIEVE ############################",topic)

  

    def _handle_publish(self, peer, sender, bus, topic, headers,
                                message):
        result=0
        result = topic.find('loads')
        if result >0:
            load_tag=topic.split("/")
            if load_tag[-3]=="building1":
                index=load_tag[-2]+"_1"
                self.loads_consumption[index]=int((message[0])['power'])/1000
               # mqqt_topic='devices/acquisition/loads/'+load_tag[-3]+'/'+load_tag[-2]+'/power'
               # self.client1.publish(mqqt_topic,int(self.loads_consumption[index]))
            if load_tag[-3]=="building2":
                index=load_tag[-2]+"_2"
                self.loads_consumption[index]=int((message[0])['power'])/1000
               # mqqt_topic='devices/acquisition/loads/'+load_tag[-3]+'/'+load_tag[-2]+'/power'
                #self.client1.publish(mqqt_topic,int(self.loads_consumption[index]))
            if load_tag[-3]=="building3":
                index=load_tag[-2]+"_3"
                self.loads_consumption[index]=int((message[0])['power'])/1000
                #mqqt_topic='devices/acquisition/loads/'+load_tag[-3]+'/'+load_tag[-2]+'/power'
                #self.client1.publish(mqqt_topic,int(self.loads_consumption[index]))
            
            values=self.loads_consumption.values()
            self.total_consumption=sum(values)
            print("########################################################################Power Consumption for WeMo############################",len(self.WeMo_Power_Consumption_Sql), len(self.loads_consumption),int(self.loads_consumption[load_tag[-2]]))
        else:
            pass
        if topic=="control/plc/shedding":
            Loadprorityagent.Shedding_Command=1
            Loadprorityagent.User_Command=1
            Loadprorityagent.Shedding_Amount=int(message)
            print("########################################################################Shedding Signal Recived############################",int(message))
        if topic=="control/plc/directcontrol":
            Loadprorityagent.Direct_Control=1
            Loadprorityagent.Direct_Control_Mode=int(message)
            print("########################################################################Direct control Signal Recived############################",int(message))

        else:
            pass

    def Send_Request(self,WeMo,CC):
        ## Sending commandes to the wemo cluster controller
        try:
            EP='WeMo_cc_'+self.WeMo_cc[WeMo]
            print("sending requests to cluster controller for "+EP)
            result=self.vip.rpc.call('platform.driver','set_point', self.WeMo_Topics[WeMo],'status',self.WeMo_Scheduled_Status[WeMo],external_platform=EP).get(timeout=20)
            #result=self.vip.rpc.call('platform.driver','get_point', self.WeMo_Topics[WeMo],'status',external_platform='WeMo_cc_1').get(timeout=60)
	    #print(result)
            if result['status']==11:
                print('Wemo is not responded')
                return 0
            else:
                #del self.WeMo_Scheduled_Status[WeMo]
                print(self.WeMo_Scheduled_Status)
                return WeMo
        except:
            print("somthing happend")
            return 0
 

    def Sort_WeMo_List(self):

        sorted_x= sorted(self.WeMo_Priorities.items(), key=operator.itemgetter(0),reverse=False) # Sort ascending order (The lowest priority is first)
        self.WeMo_Priorities = collections.OrderedDict(sorted_x)
        #print(self.WeMo_Priorities )

        
    def Read_WeMo_Power_Consumption(self,WeMo):
        try:
            EP='WeMo_cc_'+self.WeM_cc[WeMo]
        
            result=self.vip.rpc.call('platform.driver','get_point', self.WeMo_Topics[WeMo],'status',EP).get(timeout=60)
            return result
        except :
                return 0
    def Read_Total_Power_Consumption(self):
        for x in self.WeMo_Actual_Status.keys():
            result=self.Read_WeMo_Power_Consumption(x)
            if result=="error":
                pass
            else:
                mqqt_topic='devices/'+self.WeMo_Topics[WeMo]+'/power'
                self.client1.publish(mqqt_topic,result)
                print('Read_WeMO'+' '+str(mqqt_topic)+' '+str(result))
            
    def Read_WeMo_from_sql(self,WeMo):
        readtopic=self.WeMo_Topics[WeMo]+'/power'
        end = str(datetime.datetime.utcnow()) 
        start = str(datetime.datetime.utcnow()+datetime.timedelta(minutes=-1))
        try:
            WeMo_power=self.vip.rpc.call( 'platform.historian','query',readtopic,start,end, None, None,0,None,'LAST_TO_FIRST').get(timeout=10)
            
            #print(WeMo_power.get('values',None)[0][1])
            return WeMo_power.get('values',None)[0][1]/1000
        except :
            print('***************read error ***************************')
            return "error"
    

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
            Loadprorityagent.Shedding_Amount=0
                 
        self.WeMo_respond_list.clear()

    def Increment_Wemo(self):
        pass
        
    def Schedule_WeMo(self):

        Scheduled_WeMo_Consumption=0 # final wemo 
        Temp_WeMo_Schedule={}#self.WeMo_Scheduled_Status # dummy vaiable for storing weMo status after going through the priority grouping
        
        for x,y in self.WeMo_Priorities.items():
            #print(x)
            #print(y)
            Wemo_Power_Consumption_List={} # variable that stores sorted WeMo power consumption
            
            for P in y:
                result=self.loads_consumption[P[0]]
                #Keep the previous memory if there is a read error
                Wemo_Power_Consumption_List[P[0]]=result #P[1]
            
            Pval=Wemo_Power_Consumption_List.values()
            Pkey=Wemo_Power_Consumption_List.keys()
            Scheduled_Total__WeMo_Consumption=int(self.Power_Consumption_Upper_limit)+int(Loadprorityagent.Shedding_Amount)
            print("WeMoooooo consumptionnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn"+str(self.Power_Consumption_Upper_limit)+"hhhhhhhhhhhh"+str(Loadprorityagent.Shedding_Amount))
            for y in Wemo_Power_Consumption_List.values():
               
                Scheduled_Total__WeMo_Consumption= int(Scheduled_Total__WeMo_Consumption)-min(Pval) # Allocate the load consumption to the current load consumption based on the priority and the amount of the power consumption of the WeMO variable

                Temp_WeMo_Schedule[Pkey[Pval.index(min(Pval))]]=0
                del Pkey[Pval.index(min(Pval))]
                del Pval[Pval.index(min(Pval))]
                if int(self.Power_Consumption_Upper_limit)>Scheduled_Total__WeMo_Consumption:
                   				 break
                   				
                 
            if int(self.Power_Consumption_Upper_limit)>Scheduled_Total__WeMo_Consumption:
                   			break

        for x in self.WeMo_Actual_Status.keys():
                if x in   Temp_WeMo_Schedule:
                    pass
                else :
                    pass
                   # Temp_WeMo_Schedule[x]=1

        return Temp_WeMo_Schedule
    def Check_Shedding_condition(self):
        total_consumption=self.total_consumption
        self.Power_Consumption_Upper_limit=total_consumption-int(Loadprorityagent.Shedding_Amount)
        if self.Power_Consumption_Upper_limit<0:
            self.Power_Consumption_Upper_limit=0
        print('uppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppper',str(self.Power_Consumption_Upper_limit),Loadprorityagent.Shedding_Amount)
                
        

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
    def Read_Total_Power_Consumption_sql(self):
        total=0
        
        for x in self.WeMo_Actual_Status.keys():
            if bool(self.WeMo_Power_Consumption_Sql)==False or (len(self.WeMo_Power_Consumption_Sql)!= len(self.loads_consumption)):
                result=self.Read_WeMo_from_sql(x)
                if result=="error":
                    pass
                else:
                    self.WeMo_Power_Consumption_Sql[x]=result
                total=total+int(self.WeMo_Power_Consumption_Sql[x])
                print('#####################################################Read_WeMO'+' '+str(x)+' '+str(self.WeMo_Power_Consumption_Sql[x]))
            else:
                total=total+int(self.loads_consumption[x])
                #mqqt_topic='devices/'+self.WeMo_Topics[x]+'/power'
                #self.client1.publish(mqqt_topic,self.WeMo_Power_Consumption_Sql[x])
                print('#####################################################direct_Read_WeMO'+' '+str(x)+' '+str(self.loads_consumption[x]))
            
                
        #self.vip.pubsub.publish('pubsub', "datalogger/WeMo/Total_consumption",Message)
        #self.publish_to_sql(total)
        print('Total_Consumption '+str(total))
        return total
    
    def publish_to_sql(self,total):
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
        Message= {"Total_WeMo_Power_Consumption": total}
        self.vip.pubsub.publish(peer='pubsub',topic= 'devices/BMS/WeMO/all',headers=Header, message=Message)
        #WeMo_power=self.vip.rpc.call( 'platform.historian','query','BMS/WeMO/Total_WeMo_Power_Consumption',None,None, None, None,0,None,'LAST_TO_FIRST').get(timeout=10)
        #print(str(WeMo_power))

    def Schedule_Direct_Control_WeMo(self):
        print('********************direct control initialized****************************')
        Temp_WeMo_Schedule={}#self.WeMo_Scheduled_Status # dummy vaiable for storing weMo status after going through the priority grouping
        
        for x,y in self.WeMo_Priorities.items():
            #print(x)
            #print(y)
            for P in y:
                if Loadprorityagent.Direct_Control_Mode==1:
                    Temp_WeMo_Schedule[P[0]]=1
                if Loadprorityagent.Direct_Control_Mode==0:
                    Temp_WeMo_Schedule[P[0]]=0
                else:
                    pass
        return Temp_WeMo_Schedule
                    
        
        


    def Load_Priority(self):
        ### This function runs the GROUP NIRE'S load's priority algorithem
        print('*************************************************************Startingggggg*************************************************************'+str(Loadprorityagent.Shedding_Command),str(self.total_consumption))
        self.Check_Shedding_condition()
        ## Sort the WeMos based on the priority ratings
        #self.Read_Total_Power_Consumption_sql()
        #self.Read_Total_Power_Consumption()
        self.Sort_WeMo_List()
        

        if Loadprorityagent.Shedding_Command == 1:
            
            self.WeMo_Scheduled_Status=self.Schedule_WeMo()
            
            Loadprorityagent.Shedding_Command=0
            print(self.WeMo_Scheduled_Status)
        if Loadprorityagent.Direct_Control == 1:
            
            self.WeMo_Scheduled_Status=self.Schedule_Direct_Control_WeMo()
            
            Loadprorityagent.Direct_Control=0
            print(self.WeMo_Scheduled_Status)
        else:
            pass
        
        self.Send_WeMo_Schedule()
                        
        print('*******************************end of the function*************************'+str(self.WeMo_Scheduled_Status))
      

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
