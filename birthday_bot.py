import discord
import os
import os.path
import random
import asyncio
from dotenv import load_dotenv
from datetime import datetime, date
import threading
import requests
import json
import copy

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TENOR_TOKEN = os.getenv('TENOR_TOKEN')
CHANNEL_TOKEN = os.getenv('CHANNEL_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)

# setting initial birthday check to false so the bot doesn't accidentally post when it is not someone's birthday
birthday_check = False
# creating a list to store if it is someone's birthday today
birth_today_list = []

# reading JSON file of birthdays if one exists, otherwise a blank dictionary for storing birthdays is created
path = os.path.join(os.path.dirname(__file__), 'birthday_dict.json')
file_exists = os.path.isfile(path)
if file_exists == True:
    # opening JSON file
    with open(path, "r") as openfile:
        # reading from json file
        birthday_dict = json.load(openfile)

        # converting the birth date string from the JSON file into a date time object
        for k, v in birthday_dict.items():
            birth_date_str = datetime.strptime(v['birth_date'], '%Y, %m, %d')
            v['birth_date'] = birth_date_str.date()
else: 
    # dictionary of users with birthdays registered in the discord server
    birthday_dict = {}

@client.event
async def on_ready():
    print(f"Logged in as a bot {client.user}")

@client.event
async def on_message(message):
    username = str(message.author.nick)
    channel = str(message.channel.name)
    user_message = str(message.content)
    
    # manually creating commands for users to interact with the bot
    #if message.author != client.user:
        #print(f'Message {user_message} by {username} on {channel} and name is {message.author.name}')

    if user_message.lower().startswith('!add'):
        await birthday_add(message)

    if user_message.lower().startswith('!next'):
        await birthday_next(message)

    if user_message.lower().startswith('!delete'):
        await birthday_delete(message)

    if user_message.lower().startswith('!help'):
        await commands(message)

async def birthday_add(message):
    # function to add the user's birthday to the dictionary

    username = str(message.author.nick)
    userid = str(message.author.id)

    def check(msg):
        return msg.author == message.author and msg.channel == message.channel

    if message.author == client.user:
        return
    
    # Single request to channel for full birthday instead of separate items, reduces unrequired user interaction.
    await message.channel.send('What is your birthday in the format DD/MM/YYYY?')
    msg = await client.wait_for("message", check = check)
    birthday_string = msg.content
    # wrap in an error block incase user provides an incorrectly formatted string.
    try:
        # convert birthday string to datetime object using strptime, guide for formatting codes: https://docs.python.org/3.8/library/datetime.html?highlight=strptime#strftime-and-strptime-format-codes
        birthday = datetime.strptime(birthday_string, '%d/%m/%Y')
        # utilise datetime to separate out parts of the date for storing in user object. Also use .date() to remove time part of datetime object.
        birthday_user = {"username": username, "birth_date": birthday.date()}
        # add users birthday details to birthday dictionary, keyed by the userid incase there are multiple users with the same name on the server.
        birthday_dict[userid] = birthday_user
        await message.channel.send(f'Thanks <@{userid}>, you entered {birthday_string}, this has been added to the birthday bot!')

        # creating a deep copy of the original dictionary so it remains unchanged
        birthday_dict_copy = copy.deepcopy(birthday_dict)
        
        for k, v in birthday_dict_copy.items():
            v['birth_date'] = v['birth_date'].strftime('%Y, %m, %d')

        # writing the dictionary to a JSON file
        my_json_path = os.path.join(os.path.dirname(__file__), "birthday_dict.json")
        with open(my_json_path, "w") as outfile:
            json.dump(birthday_dict_copy, outfile)

    except:
        await message.channel.send(f'An error occured, are you sure you entered your birthday in the correct format (DD/MM/YYYY)? Please start the process again with !add.')

    

async def birthday_next(message):
    # function to allow a user to ask the bot when the next birthday is

    # use datetime to get todays date
    today = datetime.today().date()
    # parse year from the datetime date object.
    curr_year = today.year
    # create a list to store each users next birthday.
    next_birthday_list = []

    # split birthday dict into key and values for all users that have added their birthday for using in for loop, key being the userid and values being the users username and birthday.
    for k, v in birthday_dict.items():
        # replace the year part of the users birthday with the current year.
        this_year_bday = v['birth_date'].replace(year=curr_year)
        # for birthdays that fall in this year after the current date append to next birthday list as current year date.
        if this_year_bday > today:
            next_birthday_list.append({"user": k, "birthday": this_year_bday})
        # for birthdays that fall in this year and are before the current date append to next birthday list as next years date.
        else:
            next_birthday_list.append({"user": k, "birthday": this_year_bday.replace(year=curr_year+1)})

    # add check that birthdays are present in the system if not throw an error message.
    if len(next_birthday_list) > 0:
        # use pythons built in sort to sort the list of birthdays using the birthday as the sort key.
        sorted_birthdays = sorted(next_birthday_list, key=lambda b: b['birthday'])
        # first index is the closest to the present date.
        next_birthday = sorted_birthdays[0]['birthday']
        # use datetime strftime to convert datetime object into readable text format of date. Format is the same as used in the birthday add function above with the link in the comment for reference.
        formatted_birthday_day = next_birthday.strftime('%d')
        formatted_birthday_month = datetime.strftime(next_birthday, '%B')
        if '0' in formatted_birthday_day:
            formatted_birthday_day = formatted_birthday_day[-1]
        # create list incase multiple users have the same next birthday.
        next_user_birthday = []
        for b in sorted_birthdays:
            if b['birthday'] == next_birthday:
                next_user_birthday.append(b['user'])

        # if there are more than one users with the next birthday, generate output to be sent to discord channel.
        if len(next_user_birthday) > 1:
            users = []
            for u in next_user_birthday:
                # return the username for each user from the main birthday dict for outputtings.
                users.append(birthday_dict[u]['username'])
            # format the user list into a string based on whether it is 2 or more users.
            if len(users) > 2:
                user_string = ', '.join(users) + ' all'
            else:
                user_string = ' and '.join(users) + ' both'
            #output_message = f"The next birthday is a busy one! {user_string} have their birthdays on {formatted_birthday_string}!"
            if int(formatted_birthday_day[-1]) == 1 and int(formatted_birthday_day[0]) != 1:
                output_message = f"The next birthday is a busy one! {user_string} have their birthdays on {formatted_birthday_day}st of {formatted_birthday_month}!"
            elif int(formatted_birthday_day[-1]) == 2 and int(formatted_birthday_day[0]) != 1:
                output_message = f"The next birthday is a busy one! {user_string} have their birthdays on {formatted_birthday_day}nd of {formatted_birthday_month}!"
            elif int(formatted_birthday_day[-1]) == 3 and int(formatted_birthday_day[0]) != 1:
                output_message = f"The next birthday is a busy one! {user_string} have their birthdays on {formatted_birthday_day}rd of {formatted_birthday_month}!"
            else:
                output_message = f"The next birthday is a busy one! {user_string} have their birthdays on {formatted_birthday_day}th of {formatted_birthday_month}!"
        else:
            # return the username of the user from the main birthday dict for outputtings.
            user = birthday_dict[next_user_birthday[0]]['username']
            #output_message = f"The next birthday is {user} on {formatted_birthday_string}!"
            if int(formatted_birthday_day[-1]) == 1 and int(formatted_birthday_day[0]) != 1:
                output_message = f"The next birthday is {user} on {formatted_birthday_day}st of {formatted_birthday_month}!"
            elif int(formatted_birthday_day[-1]) == 2 and int(formatted_birthday_day[0]) != 1:
                output_message = f"The next birthday is {user} on {formatted_birthday_day}nd of {formatted_birthday_month}!"
            elif int(formatted_birthday_day[-1]) == 3 and int(formatted_birthday_day[0]) != 1:
                output_message = f"The next birthday is {user} on {formatted_birthday_day}rd of {formatted_birthday_month}!"
            else:
                output_message = f"The next birthday is {user} on {formatted_birthday_day}th of {formatted_birthday_month}!"
        # output single message to the server with birthday details.
        await message.channel.send(output_message)
    else:
        # output error message if empty user list.
        await message.channel.send(f"There doesn't appear to be any users in the system please check that at least one user has added their birthday.")

def checkTime():
    # This function runs periodically every 1 second
    threading.Timer(1, checkTime).start()

    global birthday_check
    global birth_today_list
    birth_today_list = []
    now = datetime.now()

    current_time = now.strftime("%H:%M:%S")
    #print("Current Time =", current_time)

    if (current_time == '07:00:00'):  # check if matches with the desired time
        # using datetime to get today's date
        today = datetime.today().date()
        # parse year from the datetime date object.
        curr_year = today.year

        for k, v in birthday_dict.items():
            # replace the year part of the users birthday with the current year.
            this_year_bday = v['birth_date'].replace(year=curr_year)
            if this_year_bday == today:
                birth_today_list.append(k)

        # checking if it is someone's birthday and allowing an async function to post a gif
        if len(birth_today_list) > 0:
            birthday_check = True
        else:
            birthday_check = False

    if birthday_check == True:
        # No need to create a new event loop to run the async birthday_gif function
        # These two lines add it to Discord's already running event loop
        msg = asyncio.run_coroutine_threadsafe(birthday_gif(), client.loop)
        msg.result()
            
async def birthday_gif():
    # function that gets the bot to post a message with a gif if it is someone's birthday
    global birthday_check
    global birth_today_list
    global birthday_dict

    # manually setting the channel that the bot will send the message in. The CHANNEL_TOKEN is the channel id which can be obtained by right clicking on the desired channel and selecting "Copy Channel ID"
    channel = client.get_channel(int(CHANNEL_TOKEN))
    birthday_gif = get_random_birthday_gif()

    # using datetime to get today's date
    today = datetime.today().date()
    # parse year from the datetime date object.
    curr_year = today.year

    if len(birth_today_list) == 1:
        birth_year = birthday_dict[birth_today_list[0]]['birth_date']
        age = curr_year - birth_year.year
        embed = discord.Embed()
        embed.set_image(url = f"{birthday_gif}")
        message = f":partying_face: It is <@{birth_today_list[0]}>'s birthday today and they are {age} years old! Happy birthday! :partying_face:"
        await channel.send(message, embed = embed)
    
    if len(birth_today_list) == 2:
        birth_year1 = birthday_dict[birth_today_list[0]]['birth_date']
        birth_year2 = birthday_dict[birth_today_list[1]]['birth_date']
        age1 = curr_year - birth_year1.year
        age2 = curr_year - birth_year2.year
        await channel.send(f"It is <@{birth_today_list[0]}>'s birthday and they are {age1} years old, and <@{birth_today_list[1]}>'s birthday and they are {age2} years old! {birthday_gif}")

    if len(birth_today_list) > 2:
        for i in birth_today_list:
            birth_year = birthday_dict[i]['birth_date']
            age = curr_year - birth_year.year
            await channel.send(f"It is <@{i}>'s birthday today and they are {age} years old!")
        await channel.send(f"{birthday_gif}")
    
    # Resetting everything after the gif has been sent
    birthday_check = False
    birth_today_list = []

def get_random_birthday_gif():
    # Moving the changing of birthday check to false into this function to avoid the bot posting messages twice
    global birthday_check
    # set the apikey and limit
    apikey = TENOR_TOKEN  
    # setting the search limit to eight gifs
    lmt = 8
    
    # our test search
    search_term = "birthday"

    # get random results using default locale of EN_US
    r = requests.get("https://tenor.googleapis.com/v2/search?q=%s&key=%s&limit=%s&random=True" %(search_term, apikey, lmt))

    if r.status_code == 200:
        gifs = json.loads(r.content)
        gif_url = []
        for i in range(len(gifs['results'])):
            gif_url.append(gifs['results'][i]['media_formats']['gif']['url'])
    else:
        gifs = None
    
    gif = random.choice(gif_url)
    birthday_check = False
    return gif

async def birthday_delete(message):
    # Function to allow the user to delete themself from the birthday dictionary
    global birthday_dict
    username = message.author.id

    del birthday_dict[f'{username}']
    await message.channel.send(f'Congratulations <@{username}>, you have been deleted!')

    # creating a deep copy of the original dictionary so it remains unchanged
    birthday_dict_copy = copy.deepcopy(birthday_dict)
        
    for k, v in birthday_dict_copy.items():
        v['birth_date'] = v['birth_date'].strftime('%Y, %m, %d')

    # writing the dictionary to a JSON file
    my_json_path = os.path.join(os.path.dirname(__file__), "birthday_dict.json")
    with open(my_json_path, "w") as outfile:
        json.dump(birthday_dict_copy, outfile)

async def commands(message):
    # function that allows the user to see what commands are available for the bot to perform.
    username = message.author.id
    await message.channel.send(f'Hello <@{username}>, you can add your own birthday by typing !add, and check who has the next birthday by typing !next. You can also use !delete to remove yourself from the list. Hope this helps! :slight_smile:')

checkTime()
client.run(DISCORD_TOKEN)