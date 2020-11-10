import requests
import json
import pyaudio
import pyttsx3
import speech_recognition as sr
import re
import config
import threading
import time

# ---------------------------------- ParseHub Custom API Setup and Call Handlers -------------------------------------
# from parso.python.tree import Lambda


API_KEY = config.API_KEY
PROJECT_TOKEN = config.PROJECT_TOKEN


class Data:
    def __init__(self, api_key, project_token):
        self.api_key = api_key
        self.project_token = project_token
        self.params = {
            "api_key": self.api_key
        }
        self.data = self.get_data()

    def get_data(self):
        response = requests.get(f'https://www.parsehub.com/api/v2/projects/{self.project_token}/last_ready_run/data',
                                params=self.params)
        data = json.loads(response.text)
        return data

    def get_total_cases(self):
        data = self.data['total']

        for content in data:
            if content['name'] == "Coronavirus Cases:":
                return content['value']

    def get_total_deaths(self):
        data = self.data['total']

        for content in data:
            if content['name'] == "Deaths:":
                return content['value']
        return "0"

    def get_country_data(self, country):
        data = self.data["country"]

        for content in data:
            if content['name'].lower() == country.lower():
                return content
        return "0"

    #  This will give us a list of countries for the program to listen for so it will recognize requests
    #  about a particular country
    def get_list_of_countries(self):
        countries = []
        for country in self.data['country']:
            countries.append(country['name'].lower())

        return countries

    # --------------------------  Setting up a Thread to check-in the url for updated info without giving
    # pause to our program ------------
    def update_data(self):
        # This initializes a new run on the parsehub servers
        response = requests.post(f'https://www.parsehub.com/api/v2/projects/'
                                 f'{self.project_token}/run', params=self.params)

        def poll():
            # this acts like a transition buffer between threads so as not to just take over an active thread
            time.sleep(0.1)
            old_data = self.data
            while True:
                new_data = self.get_data()
                if new_data != old_data:
                    self.data = new_data
                    print("Data updated")
                    break
                time.sleep(5)

        t = threading.Thread(target=poll)
        t.start()


# THREADING:
# Here we're constantly checking the server for updated info - we are basically asynchronously making calls to the
# url to determine differences from previous info received - ALL separately from the program running

# data = Data(API_KEY, PROJECT_TOKEN)
# print(data.get_list_of_countries())


# print(data.get_country_data("usa"))


def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


# speak("hello")


# -------------------------------- Speech Software Design -------------------------------------

#  Go back to 32mins in ( https://www.youtube.com/watch?v=gJY8D468Jv0 )
def get_audio():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source)
        said = ""

        try:
            said = r.recognize_google(audio)
        except Exception as e:
            print("Exception:", str(e))

    return said.lower()


print(get_audio())


def main():
    print("Started Program")
    data = Data(API_KEY, PROJECT_TOKEN)
    # print(data.get_list_of_countries())
    END_PHRASE = "stop"
    country_list = data.get_list_of_countries()

    # Here we're defining RegEx search patterns 're'
    TOTAL_PATTERNS = {
        # Here, we're making a dictionary that has patterns that map to a function
        # the regex [\w\s] means we're looking for any number of words before the target word "total" and "cases"
        # The function is what value we want to speak out - it makes it easy to assign a response to a pattern
        re.compile("[\w\s]+ total [\w\s]+ cases"): data.get_total_cases,
        re.compile("pablo [\w\s]+ total [\w\s]+ cases"): data.get_total_cases,
        re.compile("[\w\s]+ total cases"): data.get_total_cases,
        re.compile("[\w\s]+ total [\w\s]+ deaths"): data.get_total_deaths,
        re.compile("[\w\s]+ total deaths"): data.get_total_deaths,
    }

    COUNTRY_PATTERNS = {
        # Here we use lambda to define an annonymous function to take in a single parameter to pass to our
        # get_country_data function
        re.compile("[\w\s]+ cases [\w\s]+"): lambda country: data.get_country_data(country)['total_cases'],
        re.compile("[\w\s]+ deaths [\w\s]+"): lambda country: data.get_country_data(country)['total_deaths'],
        re.compile("[\w\s]+ active cases [\w\s]+"): lambda country: data.get_country_data(country)['active_cases'],
    }

    UPDATE_COMMAND = "update"

    while True:
        print("Listening...")
        text = get_audio()
        print(text)
        result = None

        # For pattern and function in the items of COUNTRY_PATTERNS:
        #  First, we check our speech/text patterns with the patterns ascribed above
        # Second, we convert the string into a set so that we can now use each word as comparison check against a list
        #  of our countries
        # Third, we iterate through the list of our countries and try to match an individual word to a country - if so,
        # then we pass that country as a parameter in our lambda function
        for pattern, func in COUNTRY_PATTERNS.items():
            if pattern.match(text):
                words = set(text.split(" "))
                for country in country_list:
                    if country in words:
                        result = func(country)
                        break

        # This will loop through and get the pattern and associated function for each entry
        for pattern, func in TOTAL_PATTERNS.items():
            if pattern.match(text):
                result = func()
                break

        if text == UPDATE_COMMAND:
            result = "Data is being updated. This may take a moment!"
            data.update_data()

        if result:
            speak(result)
            print(result)

        if text.find(END_PHRASE) != -1:  # stop loop
            break


main()
