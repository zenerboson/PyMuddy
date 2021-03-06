#!python
import json
import libinventory
import libitems
from datetime import datetime
import sys
from extensionlocals import *
import gamepages
class CommandParser:
	def __init__(self,world):
		self.commands={}
		self.environmentVariables={'commandnotfoundmessages':['I\'m not sure I understand you.']}
		self.referenceArguments={'world':world,'commandprocessor':self,'factory':None,'player':None,'protocol':None}
		self.blockingInput=''
		self.state='normal'
		self.deniedplayers=[]
	def _tick(self,player,world):
		self.transmitToCurrentPlayer(self.pertickmessageme.encode('utf8'))

		try:
			player.sanity-=self.ticksanitycost
			self.transmitToCurrentPlayer(('The spell drains %s sanity, leaving you with %s' % (str(self.ticksanitycost),str(player.sanity))).encode('utf8'))
		except:
			pass
		try:
			player.health-=self.tickhealthcost
			self.transmitToCurrentPlayer(('The spell drains %s health, leaving you with %s' % (str(self.tickhealthcost),str(player.health))).encode('utf8'))
		except:
			pass
		if self.tickdamage!=None:
			self.transmitToEveryoneInRoom(('%s\'s spell drains %s of your health' % (player.name,str(self.tickdamage))).encode('utf8'),player.room,False)
			for foo,playerx in player.room.players.iteritems():
				if playerx!=player:
					playerx.health-=self.tickdamage
		if self.ticksanity!=None:
			self.transmitToEveryoneInRoom(('%s\'s spell drains %s of your sanity' % (player.name,str(self.ticksanity))).encode('utf8'),player.room,False)
			for foo,playerx in player.room.players.iteritems():
				if playerx!=player:
					playerx.sanity-=self.ticksanity
		self.transmitToEveryoneInRoom(self.pertickmessageeveryone.encode('utf8'),player.room,False)

	def addCommand(self,name,function,properties_dict):
		self.commands[name]=(function,properties_dict)
	def setEnv(self,envname,value):
		self.environmentVariables[envname]=value
	def registerReferenceArgument(self,name,argument):
		self.referenceArguments[name]=argument
	def registerCommandAlias(self,origin,alias):
		self.commands[alias]=self.commands[origin]
	def nonBlockingInput(self,callback):
		self.referenceArguments['protocol'].state='WAITING_FOR_INPUT'
		self.referenceArguments['protocol'].inputCallback=callback
	def getCurrentRoom(self):
		return self.referenceArguments['player'].room
	def isPlayerInRoom(self,room,player):
		inRoom=False
		if player in room.players.keys():
			inRoom=True
		if player in room.players.values():
			inRoom=True
		return inRoom
	def transmitToCurrentPlayer(self,line):
		self.referenceArguments['protocol'].sendLine(line)
	def transmitToPlayer(self,line,player):
		try:
			for client in self.referenceArguments['factory'].clients:
				if client.player.name==player.name:
					client.sendLine(line.encode('utf8'))
		except KeyError:
			return False
	def transmitToEveryone(self,line,transmittoself):
		try:
			for client in self.referenceArguments['factory'].clients:
				if factory==client and not transmittoself:
					pass
				else:
					client.sendLine(line.encode('utf8'))
			return True
		except KeyError:
			return False
	def transmitToEveryoneInRoom(self,line,room,transmittoself):
		try:
			for foo,player in room.players.iteritems():
				if player==self.referenceArguments['player']:
					if transmittoself:
						player.thing.sendLine(line.encode('utf8'))
				else:
					player.thing.sendLine(line.encode('utf8'))
			return True
		except KeyError:
			return False
	def getPlayerByName(self,name):
		try:
			return self.referenceArguments['world'].players[name]
		except KeyError:
			return None
	def getNetworkClients(self):
		try:
			self.referenceArguments['factory'].clients
		except NameError:
			return []
		return list(self.referenceArguments['factory'].clients)
	def getPlayers(self):
		try:
			self.referenceArguments['factory'].clients
		except NameError:
			return []
		client_list=[]
		for client in list(self.referenceArguments['factory'].clients):
			client_list.append(client.player)
		return client_list
	def parseCommand(self,input,player,factory,world):
		if player.isinsane:
			return(True, "INSANE IN THE MEMBRANE INSANE GOT NO BRAIN!")
		if player.isdead:
			return(True, "Dude, you're a corpse. Good luck with that.")
		if player.isdenied:
			return(True,self.denymessage)
		if self.state!='normal':
			if input.strip('\n\r')=='stop':
				self.state='normal'
				world.removeTickCall(self._tick)
				for player in self.deniedplayers:
					player.isdenied=False
					self.deniedplayers.remove(player)
				if self.stopmessageeveryone!=None:
					self.transmitToEveryoneInRoom(self.stopmessageeveryone.replace('</>',player.name),player.room,False)
				return(True, self.stopmessageme)
			else:
				return(True, self.state)
		try:
			if self.referenceArguments['factory']==None and factory!=None:
				self.referenceArguments['factory']=factory
				for client in self.referenceArguments['factory'].clients:
					if client.player.name==player.name:
						self.referenceArguments['protocol']=client
				self.referenceArguments['protocol'].commandParser=self
				self.referenceArguments['protocol'].factory.protocol.factory=self.referenceArguments['factory']=factory
			if self.referenceArguments['player']==None and player!=None:
				self.referenceArguments['player']=player
		except BaseException as e:
			log('WARNING!!!: ENCOUNTERED ERROR AS FOLLOWS WHILE SETTING PARSER REFARGS: %s' % str(e))
		splits=input.strip('\n\r').split(' ')
		try:
			command=self.commands[splits[0].lower()][0]
			properties=self.commands[splits[0].lower()][1]
			if 'args' in properties:
				arguments_required=properties['args']
				argument_list={}
				for argument_name in arguments_required:
					if argument_name=='current_player':
						argument_list['current_player']=player
					else:
						argument_list[argument_name]=self.referenceArguments[argument_name]
			return(True,command(splits[1:],**argument_list))
		except KeyError:
			if input.strip('\n\r') in player.spells.keys():
				return (True,self.castSpell(input.strip('\n\r'),player,world))
			elif ' '.join(input.strip('\n\r').split(' ')[:-1]) in player.spells.keys():
				 return (True,self.castSpell(input.strip('\n\r'),player,world))
			else:
				return (False,self.environmentVariables['commandnotfoundmessages'][0])
	def castSpell(self,spellname,player,world):
		spell=player.spells[spellname]
		self.transmitToCurrentPlayer(spell['startcastmessage'].encode('utf8'))
		if spell['startcastaroundtarget']!='':
			self.transmitToEveryoneInRoom(spell['startcastaroundtarget'].replace('</>',player.name).encode('utf8'),player.room,False)
		csplit=spell['cost'].split(' ')
		if 'start' in csplit:
			startcosttype=csplit[csplit.index('start')+1]
			if startcosttype=='sanity':
				player.sanity-=int(csplit[csplit.index('start')+2])
				self.transmitToCurrentPlayer(('The spell drains %s sanity, leaving you with %s' % (str(csplit[csplit.index('start')+2]),str(player.sanity))).encode('utf8'))
			if startcosttype=='health':
				player.health-=int(csplit[csplit.index('start')+2])
				self.transmitToCurrentPlayer(('The spell drains %s health, leaving you with %s' % (str(csplit[csplit.index('start')+2]),str(player.health))).encode('utf8'))
		if 'tick' in csplit:
			tickcosttype=csplit[csplit.index('tick')+1]
			if tickcosttype=='sanity':
				self.ticksanitycost=int(csplit[csplit.index('tick')+2])
			if tickcosttype=='health':
				self.tickhealthcost=int(csplit[csplit.index('tick')+2])
			self.tickcosttype=tickcosttype
		asplit=spell['action'].split(' ')
		if 'deny' in asplit:
			self.deny=True
			for name,playerx in player.room.players.iteritems():
				if playerx!=player:
					playerx.isdenied=True;
					self.deniedplayers.append(playerx)
		self.tickdamage=None
		self.ticksanity=None
		if 'damage' in asplit:
			self.tickdamage=int(asplit[asplit.index('damage')+1])
		if 'sanity' in asplit:
			self.ticksanity=int(asplit[asplit.index('sanity')+1])
		AOE=False
		if 'tick' in asplit:
			tick=True
			self.state=spell['runningmessage']
			world.addTickCall(self._tick,player,world)
			self.stopmessageme=spell['endcastmessage']
			if spell['endcastmessagearoundtarget']!='':
				self.stopmessageeveryone=spell['endcastmessagearoundtarget']
			else:
				self.stopmessageeveryone=None
		self.denymessage=spell['lockdownmessage']
		if asplit[0]=='AOE':
			AOE=True
		if 'tickeveryonemessage' in asplit:
			self.pertickmessageeveryone=asplit[asplit.index('tickeveryonemessage')+1].replace("(","").replace(")","").replace("'","").replace('&',' ')
		if 'tickmemessage' in asplit:
			self.pertickmessageme=asplit[asplit.index('tickmemessage')+1].replace("("," ").replace(")"," ").replace("'"," ").replace('&',' ')
		return ""


#Cthulhu was here
def log(text):
	text2="[%s - gamefiles] %s" % ((str(datetime.now())),text)
	sys.stdout.write(text2)
class World:
	def __init__(self,initialroom):
		self.commandParser=CommandParser(self)
		self.manpage=gamepages.GamePage()
		self.commandParser.registerReferenceArgument('gamepagers',self.manpage)
		self.rooms={}
		self.players={}
		self.rooms[initialroom.name]=initialroom
		self.spawn=self.rooms[initialroom.name]
		self.state=''
		self.tickfuncs=[]
		self.registerCommands()
	def doTick(self):
		for tick in self.tickfuncs:
			tick[0](*tick[1])
	def addTickCall(self,call,*args):
		self.tickfuncs.append((call,args))
	def removeTickCall(self,call):
		for tickfunc in self.tickfuncs:
			if tickfunc[0]==call:
				self.tickfuncs.remove(tickfunc)
	def registerCommands(self):
		#IMPORTANT!!!
		#DEFINE NEW COMMANDS HERE USING UPDATED API, NOT IN THE WORLD COMMAND PARSER CALL
		#TODO Port entirety of old parser functions to new system
		#Testing callback
		def inputCallbackOne(line,protocol):
			mush=searchForItemInHashTable(line,protocol.player.getCurrentRoomContents())
			protocol.sendLine(str(mush).encode('utf8'))
		#Testing commmand for version two command implementations and callbacks
		def phishCommand(line,world=None,commandprocessor=None):
			commandprocessor.nonBlockingInput(inputCallbackOne)
			return('')
		def attackCommand(line,world=None,commandprocessor=None,player=None):
			line=" ".join(line)
			if player.equipped==None:
				return "You currently are not permitted to attack with your bare hands. Combat is a WIP, sorry!"
			if commandprocessor.isPlayerInRoom(player.room,commandprocessor.getPlayerByName(line)):
				if player.equipped.getProperty('type')=='weapon':
					commandprocessor.getPlayerByName(line).combatAttacked(player.equipped.getProperty('damage'),player)
					return "Attacked"
				else:
					return "You do not have a valid weapon equipped!"
			else:
				return "You can see no such thing to attack!"

		def equipCommand(line,player=None):
			line=" ".join(line)
			try:
				item=searchForItemInHashTable(line,player.inventory.getItemTable())
				returnstring=''
				if item==None:
					return "You do not have that to equip!"
				if item[0]=='multi':
					player.equipped=item[1]
					returnstring+='%s %s equipped' % (str(len(item[1])),item[1][0].shortdescription)
					for each in player.equipped:
						each.additions.append(' (equipped) ')
				if item[0]=='single':
					player.equipped=item[1]
					returnstring+='%s equipped' % item[1].shortdescription
					player.equipped.additions.append(' (equipped) ')
				return returnstring
			except KeyError:
				return "You do not have that to equip!"
		def unequipCommand(line,player=None):
			line=" ".join(line)
			if type(player.equipped)==type([]):
				for each in player.equipped:
					each.additions.remove(' (equipped) ')
			else:
				player.equipped.additions.remove(' (equipped) ')
			player.equipped=None
			return "Equipped your bare hands."
		def inventoryCommand(line,player=None):
			data=''
			for key,value in player.inventory.items.iteritems():
				data+='%sx %s%s\n' % (str(len(value)),value[0].shortdescription,''.join(value[0].additions))
			if data=="":
				data='Your inventory is empty\n'
			data+='Your health is currently %s out of a maximum of %s\n' % (str(player.health),str(player.maxhealth))
			data+='Your sanity is currently %s out of a maximum of %s\n' % (str(player.sanity),str(player.maxsanity))
			return data
		def manCommand(line,gamepagers=None):
			if line==[]:
				data='\n\r'+gamepagers.getHelpPage()
				data+=gamepagers.getFullManual()
				return data
			if len(line)>0:
				for each in line:
					data='\n\r'
					data+=gamepagers.getManualForCommand(each)
				return data
		def readCommand(line, player=None,commandprocessor=None):
			name=(' ').join(line)
			item=player.getInventoryItemByDescription(name)
			if item!=None:
				item=item[0]
				if item.properties['type']=='book':
					if item.read:
						return "You've already gained knowledge from this text. Use 'spells' to use this in the future."
					else:
						commandprocessor.transmitToEveryoneInRoom('%s reads %s' % (player.name,item.name),commandprocessor.referenceArguments['player'].room,False)
						commandprocessor.referenceArguments['player'].learned=True
						item.read=True
						bookprops=item.properties
						commandprocessor.referenceArguments['player'].spells[bookprops['trigger']]=bookprops
						return item.properties['readmessage']
				else:
					return "That's not a book!"
			else:
				return "You aren't carrying that!"
		def spellsCommand(line,player=None,commandprocessor=None):
			if player.learned:
				text='You have the capability to use the following spells. This is a gift, use your power wisely.\n\n'
				for trigger,spelldict in player.spells.iteritems():
					text+=spelldict['spell']+'\n'
				commandprocessor.transmitToEveryoneInRoom('%s flips through a glowing book. You feel that it possesses some great power.' % player.name,player.room,False)
				return text
			else:
				return "I'm not sure I understand you."
		self.commandParser.addCommand('spells',spellsCommand,{'args':['player','commandprocessor']})
		self.commandParser.addCommand('read',readCommand,{'args':['player','commandprocessor']})
		self.commandParser.addCommand('phish',phishCommand,{'args':['world','commandprocessor']})
		self.commandParser.addCommand('attack',attackCommand,{'args':['world','commandprocessor','player']})
		self.commandParser.registerCommandAlias('attack','kill')
		self.commandParser.addCommand('equip',equipCommand,{'args':['player']})
		self.commandParser.addCommand('unequip',unequipCommand,{'args':['player']})
		self.commandParser.addCommand('inventory',inventoryCommand,{'args':['player']})
		self.commandParser.registerCommandAlias('inventory','i')
		self.commandParser.addCommand('man',manCommand,{'args':['gamepagers']})
	def add_room(self,room):
		self.rooms[room.name]=room
	def add_player(self,player):
		self.players[player.name]=player
		self.spawn.players[player.name]=player
		self.players[player.name].room=self.spawn
		self.spawn.players[player.name].room=self.spawn
	def move_player(self,room1,room2,playername):
		self.players[playername].room=room2
		room2.players[playername]=room1.players[playername]
		room2.players[playername].room=room2
		del room1.players[playername]
		room1.players[playername]=None
	def remove_player(self,playername):
		self.players[playername].room.players[playername]=None
		self.players[playername]=None
		del self.players[playername]
	def saytoplayer(self,playername,text,factory,player2):
		try:
			for c in factory.clients:
				if c.player.name==playername and c.player.name!=player2:
					c.sendLine(text.encode('utf8'))
		except:
			pass
	def process_command(self,command,playername,factory=None,player2=None):
		factory=factory
		try:
			command=command.decode('utf8')
		except:
			return "An error ocurred! Please contact the sysadmin and inform him of the situation in which this ocurred."
		command=str(command)
		if command=='':
			return ''
		command_array=command.split()
		player=self.players[playername]
		parsing_response=self.commandParser.parseCommand(command,player,factory,self)
		if parsing_response[0]:
			return parsing_response[1]
		else:
			pass
		extra=""
		if self.state=='getting_num_items_grab':
			try:
				int(command)
			except:
				return "That's not a valid number!\n Please give a valid number!\n"
			name=self.arbitrary_data_storage
			for key,value in player.room.contents.iteritems():
				for x in name:
					if x in key:
						if int(command)>len(value):
							return "You can't see that many! Please give a smaller number!"
						if int(command)!=0:
							contents_item=True
							try:
								player.inventory.items[key]
							except:
								contents_item=False
							if not contents_item:
								player.inventory.items[key]=[]
							player.inventory.items[key]+=value[0:int(command)]
							if int(len(value))==int(command):
								del player.room.contents[key]
								self.state=''
								return "Taken"
							del player.room.contents[key][0:int(command)]
						self.state=''
						return "Taken"
		if self.state=='getting_num_items_drop':
			try:
				int(command)
			except:
				return "That's not a valid number!\n Please give a valid number!\n"
			name=self.arbitrary_data_storage
			for key,value in player.inventory.items.iteritems():
				for x in name:
					if x in key:
						if int(command)>len(value):
							return "You can't see that many! Please give a smaller number!"
						if int(command)!=0:
							contents_item=True
							try:
								player.room.contents[key]
							except:
								contents_item=False
							if not contents_item:
								player.room.contents[key]=[]
							player.room.contents[key]+=value[0:int(command)]
							if int(len(value))==int(command):
								del player.inventory.items[key]
								self.state=''
								return "Taken"
							del player.inventory.items[key][0:int(command)]
						self.state=''
						return "Dropped"
		command=command.lower()
		if command[0:2]=="x " or command[0:8]=="examine ":
			if command[0:2]=="x ":
				name=command[2:].strip("\n").split()
			if command[0:8]=="examine ":
				name=command[8:].strip("\n").split()
			for key,value in player.room.contents.iteritems():
				for x in name:
					if x in key:
						return("Examining %s - %s" % (key,value.longdescription))
			for key,value in player.inventory.items.iteritems():
				for x in name:
					if x in key:
						return("Examining %s - %s" % (key,value.longdescription))

			return "You can see no such thing."
		if command[0:4]=="get " or command[0:5]=="take " or command[0:5]=="grab ":
			if command[0:4]=="get ":
				name=command[4:].strip("\n").split()
			if command[0:5]=="take " or command[0:5]=="grab ":
				name=command[5:].strip("\n").split()
			for key,value in player.room.contents.iteritems():
				for x in name:
					if x in key:
						if len(value)>1 and self.state!='getting_num_items_grab':
							self.state='getting_num_items_grab'
							self.arbitrary_data_storage=name
							return "How many do you want to %s?" % command.split()[0]
						contents_item=True
						try:
							player.inventory.items[key]
						except:
							contents_item=False
						if not contents_item:
							player.inventory.items[key]=[]
						player.inventory.items[key].append(value[0])
						del player.room.contents[key]
						return "Taken"
			return "You can see no such thing!"
		if command[0:5]=="drop ":
			name=command[5:].strip("\n").split()
			for key,value in player.inventory.items.iteritems():
					for x in name:
						if x in key:
							if len(value)>1:
								self.state='getting_num_items_drop'
								self.arbitrary_data_storage=name
								return "How many do you want to %s?" % command.split()[0]
							contents_item=True
							try:
								player.room.contents[key]
							except:
								contents_item=False
							if not contents_item:
								player.room.contents[key]=[]
							player.room.contents[key].append(value[0])
							del player.inventory.items[key]
							return "Dropped"
			return "You aren't carrying any such thing!"
		if command=="hapl" or command=="hapl mei":
			return "You are a simple noob, standing in a room. \n This is PyMuddy, a MUD built with Python, \nor a Multiplayer Adventure without any graphics built with a coding language. \nIt was made by two 1337 ninja coderz/haxxors, zenerboson and guidepupguy, and one silly noobish, MysteryPig.\nYou can type a command and then press enter to do a thing. \nN makes you go north. W makes you go west. \nYou can figure out the other two, plus up and down. \nYou can type take blah to get an item called blah, if it is in the room.\nI checks your inventory and health. \nDrop lets you put a thing down.\nIf you go west twice, there is free candy and an ornate burning chipmunk."
		if command=="help" or command=="noob" or command=="iamanoob" or command=="h" or command=="info":
			return "This is not the command you are looking for. Try hapl mei."
		if command=="i" or command=="inventory":
			data=''
			for key,value in player.inventory.items.iteritems():
				data+='%sx %s\n' % (str(len(value)),value[0].shortdescription)
			if data=="":
				data='Your inventory is empty'
			data+='Your health is currently %s out of a maximum of %s\n' % (str(player.health),str(player.maxhealth))
			return data
		if command=="1337" or command=="haxxor" or command=="1337haxxor":
			return "You are a 1337 |-|4><><0|2.\n   run(notavirus.trojanhorse)\n   init(godmode)\n   init(sopro) \nTentacles wrapped and locked. The system is now under your control. Type 'hack CIA' to continue."
		if command=="hack CIA" or command=="hack cia":
			return "\n >hack CIA.gov/allthesecrets \n...\nSECRETS: Area 51  Illuminati  9/11\n >9/11\n BUSH DID 9/11. 9/11 = 911. 911 has 3 numbers. A triangle has 3 points. Illuminati confirmed. 911. 911 makes you think of the fire department. Fire trucks are red. Red has 3 letters. Illuminati confirmed. BUSH AND THE ILLUMINATI DID 9/11. \n  /\ \n / O\ \n/____\ "
		if command=="look" or command=="l":
			for key,value in player.room.contents.iteritems():
				if len(value)==1:
					extra+="\nYou can also see a "+value[0].shortdescription+" here"
				else:
					extra+="\nYou can also see %s %ss here" % (str(len(value)),value[0].shortdescription)
			for key,value in player.room.players.iteritems():
				if key!=player.name:
					extra+="\n%s is here too!" % key
			return player.room.name+" : "+player.room.appearance+extra
		elif command=="west" or command=="w" or command=="go w" or command=="go west":
			if player.room.west!=None:
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s leaves to the west" % player.name,factory,player2)
				self.move_player(player.room,self.rooms[player.room.west],player.name)
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s enters from the east" % player.name,factory,player2)
				return self.process_command('look',playername)
			else:
				return "You can't go that way!"
		elif command=="east" or command=="e" or command=="go e" or command=="go east":
			if player.room.east!=None:
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s leaves to the east" % player.name,factory,player2)
				self.move_player(player.room,self.rooms[player.room.east],player.name)
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s enters from the west" % player.name,factory,player2)
				return self.process_command('look',playername)
			else:
				return "You can't go that way!"
		elif command=="north" or command=="n" or command=="go n" or command=="go north":
			if player.room.north!=None:
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s leaves to the north" % player.name,factory,player2)
				self.move_player(player.room,self.rooms[player.room.north],player.name)
				return self.process_command('look',playername)
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s enters from the south" % player.name,factory,player2)
			else:
				return "You can't go that way!"
		elif command=="south" or command=="s" or command=="go s" or command=="go south":
			if player.room.south!=None:
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s leaves to the south" % player.name,factory,player2)
				self.move_player(player.room,self.rooms[player.room.south],player.name)
				return self.process_command('look',playername)
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s enters from the north" % player.name,factory,player2)
			else:
				return "You can't go that way!"
		elif command=="up" or command=="u" or command=="go u" or command=="go up":
			if player.room.up!=None:
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s leaves upwards" % player.name,factory,player2)
				self.move_player(player.room,self.rooms[player.room.up],player.name)
				return self.process_command('look',playername)
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s enters from below" % player.name,factory,player2)
			else:
				return "You jump fruitlessly."
		elif command=="down" or command=="d" or command=="go d" or command=="go down":
			if player.room.down!=None:
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s leaves downwards" % player.name,factory,player2)
				self.move_player(player.room,self.rooms[player.room.down],player.name)
				for key,value in self.players.iteritems():
					if value.room==player.room:
						self.saytoplayer(value.name,"%s enters from above" % player.name,factory,player2)
				return self.process_command('look',playername)
			else:
				return "You can't go that way!"
		elif command=="xyzzy":
			return("Honestly? Really? Are you actually saying that? Yes you are.\a")
		elif command=='quit' or command=='exit':
			return('#exit#')
		elif command_array[0]=='stab' or command_array[0]=='a' or command_array[0]=='kill' or command_array[0]=='attack':
			print(command_array)
			if len(command_array)<4:
				return "You need to specify what to attack and what to attack with!"
			if command_array[1] in player.room.players.keys():
				pass
			else:
				return "You can't see any such person to attack!"
			bleh=None
			for key,value in player.inventory.items.iteritems():
				if command_array[3] in key:
					bleh=key
			if bleh==None:
				return "You don't have that thing!"
			if player.inventory.items[bleh][0].properties['type']=='weapon':
				attacktype=''
			else:
				return "That's a silly thing to attack with."
			if player.inventory.items[bleh][0].properties['type']=='wizzered':
				attacktype='smokeofweed'
			if not player.can_attack:
				return "You are in no condition to attack!"
			playername2=player.name
			self.players[command_array[1]].take_damage(player.inventory.items[bleh][0].properties['damage'])
			if attacktype=='':
				self.saytoplayer(command_array[1],"%s attacks you with a %s! You lose %s life! You are now at %s life!\a" % (player.name,player.inventory.items[bleh][0].properties['stance'],player.inventory.items[bleh][0].properties['damage'],self.players[command_array[1]].health),factory,playername2)
				return "You attack %s, dealing %s damage!" % (command_array[1],player.inventory.items[bleh][0].properties['damage'])
			else:
				self.saytoplayer(command_array[1],"%s attacks you with a %s! You lose %s life! You are now at %s life!\a Also, smoke of weed fills the room! You are now high!" % (player.name,player.inventory.items[bleh][0].properties['stance'],player.inventory.items[bleh][0].properties['damage'],self.players[command_array[1]].health),factory,playername2)
				return "You attack %s, dealing %s damage! Smoke of weed fills the room! Make your escape now!" % (command_array[1],player.inventory.items[bleh][0].properties['damage'])
		else:
			return "I'm not sure I understand you"
class Room:
	def __init__(self,name,appearance,contents={},fromfile=None,west=None,east=None,north=None,south=None,up=None,down=None):
		self.appearance=appearance
		self.name=name
		self.contents={}
		self.players={}
		self.west=west
		self.east=east
		self.north=north
		self.south=south
		self.up=up
		self.down=down
		datatypes=[("appearance",self.set_1),("name",self.set_2),("contents",self.set_3),("east",self.set_4),("north",self.set_5),("south",self.set_6),("west",self.set_7),("up",self.set_8),("down",self.set_9)]
		if fromfile!=None:
			try:
				log("Loading room %s\n" % fromfile)
				self.fp=open(fromfile,"r+")
			except BaseException as e:
				log("Warning - Bad room file path %s!\n" % fromfile)
				del self
				return
			self.fp.seek(0)
			for line in self.fp.readlines():
				for datatype in datatypes:
					if line[0:len(datatype[0])]==datatype[0]:
						if datatype[0]!="contents":
							datatype[1](line[len(datatype[0])+1:].strip("\n"))
						else:
							for x in line[len(datatype[0]):].split():
								item=libitems.Item(x)
								log("Loading item %s" % x)
								contents_item=True
								try:
									self.contents[item.name]
								except:
									contents_item=False
								if not contents_item:
									self.contents[item.name]=[]
								self.contents[item.name].append(item)
			try:
				self.fp.close()
				del self.fp
				log("Done! - loaded room name %s\n" % self.name)
			except:
				pass
	def set_1(self,x):
		self.appearance=x
	def set_2(self,x):
		self.name=x
	def set_3(self,x):
		self.contents=x
	def set_4(self,x):
		if x[0]==" ":
			x=x[1:]
		self.east=x
	def set_5(self,x):
		if x[0]==" ":
			x=x[1:]
		self.north=x
	def set_6(self,x):
		if x[0]==" ":
			x=x[1:]
		self.south=x
	def set_7(self,x):
		if x[0]==" ":
			x=x[1:]
		self.west=x
	def set_8(self,x):
		if x[0]==" ":
			x=x[1:]
		self.up=x
	def set_9(self,x):
		if x[0]==" ":
			x=x[1:]
		self.down=x

class Player(object):
	def __init__(self,name):
		self._health=100
		self.isdenied=False
		self.maxhealth=100
		self.maxsanity=100
		self.learned=False
		self.can_attack=True
		self.equipped=None
		self.inventory=libinventory.Inventory()
		self.name=name
		self.spells={}
		self.isdead=False
		self.isinsane=False
		self._sanity=100
	def get_health(self):
		return self._health
	def set_health(self, value):
		if value<0:
			value=0
			self.thing.sendLine('You are dead now! |0| |_| 907 |*|/\||\|3|)'.encode('utf8'))
			self.isdead=True
		self._health=value
	def get_sanity(self):
		return self._sanity
	def set_sanity(self, value):
		if value<0:
			value=0
			self.thing.sendLine('You are insane now! Insane in the brain, insane, got no brain! Insane in the membrane!'.encode('utf8'))
			self.isinsane=True
		self._sanity=value
	health=property(get_health,set_health)
	sanity=property(get_sanity,set_sanity)
	def take_damage(self,damage):
		self.health-=int(damage)
		if self.health<=0:
			self.isdead=True
	def getCurrentRoomContents(self):
		return self.room.contents
	def combatAttacked(self,damage,attacker):
		self.health-=int(damage)
	def checkItemInInventory(self,itemname):
		try:
			return len(self.inventory.getItemByName(itemname))
		except KeyError:
			return 0

	def getInventoryItemByDescription(self,itemname):
		name=itemname.split(' ')
		for key,value in self.inventory.items.iteritems():
				for x in name:
					if x in key:
						return value
		return None
class Creature:
	def __init__(self,properties):
		self.properties=properties
		self.name=properties['name']
		self.health=properties['health']
		self.maxhealth=properties['maxhealth']
		self.drops=libinventory.Inventory()
		for key,value in self.properties['drops'].iteritems():
			self.drops.additem(key,value)
		self.behaviours=properties['behaviours']
class TriggerManager:
	def __init__(self,world):
		self.eventmap={}
		self.worldreference=world
	def addEventWithTrigger(self,triggername,event):
		try:
			self.eventmap[triggername]
		except KeyError:
			self.eventmap[triggername]=[]
		self.eventmap[triggername].append(event)
	def trigger(self,eventname):
		for event in self.eventmap[eventname]:
			event()
