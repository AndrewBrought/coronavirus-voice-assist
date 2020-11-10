import requests
import json
import pyaudio
import pyttsx3
import speech_recognition as sr
import re
import config

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
        self.get_data()

    def get_data(self):
        response = requests.get(f'https://www.parsehub.com/api/v2/projects/{self.project_token}/last_ready_run/data',
                                params=self.params)
        self.data = json.loads(response.text)

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
        re.compile("[\w\s]+ cases [\w\s]+"): lambda country: data.get_country_data(country)['total_cases'],
    }

    while True:
        print("Listening...")
        text = get_audio()
        print(text)
        result = None
        # This will loop through and get the pattern and associated function for each entry
        for pattern, func in TOTAL_PATTERNS.items():
            if pattern.match(text):
                result = func()
                break

        if result:
            speak(result)
            print(result)

        if text.find(END_PHRASE) != -1:  # stop loop
            break


main()
