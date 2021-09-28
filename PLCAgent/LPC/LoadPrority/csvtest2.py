from csv import DictReader, DictWriter
csv_path='WeMo_Config.csv'
with open(csv_path, "r") as csv_device:
                 reader = DictReader(csv_device)
		 print(reader)
		 for point in reader:
			Name = point.get("Name")
                        Priority = point.get("Priority")
                        Building = point.get("Building")
                        Cluster_Controller = point.get("cc")
                        Consumption = point.get("Consumption")
			print(Name)
