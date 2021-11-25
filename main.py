import re
import threading
import time
import hashlib

from datetime import datetime
from tinydb import TinyDB, Query

from selenium.webdriver.common.by import By
from selenium.webdriver.firefox import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Document struct
class Document(object):
    # The class "constructor" - It's actually an initializer
    def __init__(self):
        self.id = None
        self.result = None
        self.datetime = None
        self.payoutto = None
        self.gameid = None
        self.payoutid = None
        self.roll = None
        self.xch_in = None
        self.xch_out = None


def hash_string(in_str: str) -> str:
    # Assumes the default UTF-8
    hash_object = hashlib.md5(in_str.encode())
    hashed_string = hash_object.hexdigest()
    return hashed_string


def insert_data(roll_data: dict):
    db.insert(roll_data)


def get_data_by_id(doc_id: str) -> dict:
    docs = db.search(document.id == doc_id)
    if len(docs) > 1:
        print("ERROR - ID has duplicated")
    for doc in docs:
        return doc


def construct_document(raw_data: str) -> Document:
    # r'(?<result>\w+)\n(?<datetime>.*\n.*)\n(?<payoutto>.*)\n(?<gameid>\w+)\s(?<payoutid>\w+)\n(?<roll>.*)\n(?<xchin>.*?)\sXCH\s(?<xchout>.*)\sXCH'
    regex_patt = r'(\w+)\n(.*\n.*)\n(.*)\n(\w+)\s(\w+)\n(.*)\n(.*?)\sXCH\s(.*)\sXCH'
    match = re.match(regex_patt, raw_data)

    doc = Document()
    if len(match.groups()) == 8:
        doc.id = hash_string(match.group(2) + match.group(3) + match.group(4) + match.group(5))
        doc.result = match.group(1)
        date = match.group(2)
        doc.datetime = datetime.strptime(date, '%b %d, %Y\n%H:%M').strftime('%m/%d/%Y, %H:%M')  # "Nov 24, 2021\n23:16"
        doc.payoutto = match.group(3)
        doc.gameid = match.group(4)
        doc.payoutid = match.group(5)
        doc.roll = match.group(6)
        doc.xch_in = match.group(7)
        doc.xch_out = match.group(8)
    return doc


def start_data_collector():
    ff_options = Options()
    ff_options.headless = True

    with webdriver.WebDriver(options=ff_options, executable_path="geckodriver.exe") as driver:
        driver.get(URL)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.rolls')))
        while True:
            new_rolls = driver.find_elements(By.CSS_SELECTOR, 'tr.even-row' and 'tr.odd-row')

            for single_roll in new_rolls:

                doc = construct_document(single_roll.text)

                if not get_data_by_id(doc.id):
                    insert_data(doc.__dict__)

            new_rolls.clear()
            time.sleep(5)


def start_profit_processor():

    while True:
        xch_total: float = 0.0
        documents = db.all()
        for doc in documents:
            xch_total = xch_total + float(doc.get('xch_in'))
            if xch_total >= 0:
                xch_total = xch_total - float(doc.get('xch_out'))
            else:
                xch_total = xch_total + float(doc.get('xch_out'))
        print("{datetime}: Total XCH balance: {balance}".format(
            datetime=datetime.now().strftime("%d-%b-%Y_%H:%M:%S"),
            balance=str(xch_total)))
        time.sleep(60)


URL = "https://www.mojodice.com/"
db = TinyDB('local_db.json')
document = Query()

t1 = threading.Thread(target=start_data_collector, args=())
t2 = threading.Thread(target=start_profit_processor, args=())

t1.start()
t2.start()

t1.join()
t2.join()
