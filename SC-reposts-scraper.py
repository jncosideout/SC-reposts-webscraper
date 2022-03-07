# SoundCloud reposts webscraper for Sour_Cream_Pringles@soundcloud.com
from random import random, uniform
from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException
import time
import pyautogui as pag
from collections import namedtuple
from typing import NamedTuple
from os import path as Path
from pathlib import PurePath
from bs4 import BeautifulSoup
import requests
import sys

Point = NamedTuple('Point', [('x',float),('y',float)])

def extract(url: str):
    elem = None
    # uncomment for headless
    # fireFoxOptions = webdriver.FirefoxOptions()
    # fireFoxOptions.set_headless()
    # driver = webdriver.Firefox(firefox_options=fireFoxOptions)
    driver = webdriver.Firefox()
    driver.implicitly_wait(10)
    driver.get(url)
    
    global windowLocation
    windowLocation = driver.get_window_position()
    windowLocation = Point(float(windowLocation["x"]),
                            float(windowLocation["y"]))
    print(f"window location is {windowLocation}")
    
    global windowSize
    windowSize = driver.get_window_size()
    print(f"window size is {windowSize}")

    global windowNames
    windowNames = driver.window_handles

    # Expand to fullscreen so absolute coordinates will not require
    #  compensation for window position, browser toolbar, tabs bar, etc.
    
    windowLocation = Point(windowLocation.x+1, windowLocation.y+1)
    pag.moveTo(windowLocation.x,windowLocation.y)
    
    pag.click()
    pag.press('F11')

    pag.moveTo(windowSize['width']/2,windowSize['height']/2)

    try:
        scrollReposts(driver)
        # Make a copy of relevant data, because Selenium will throw if
        # you try to access the properties after the driver quit
        path = download(url, '.')
    finally:
        driver.close()
        
    songs = run(path)

    for song in songs:
        elem = elem + song + '\n'

    return elem

def scrollReposts(driver: webdriver):
    # delimiter of reposts page, signals bottom of reposts list
    css_selector = ".paging-eof"
    # <div class="paging-eof sc-border-light-top" title=""></div>
    condition = True
    while condition:
        pag.press('pagedown')
        try:
            WebDriverWait(driver, 1).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, css_selector)            
                )
            )
        except TimeoutException:
            condition = True
        else:
            condition = False

def download(url, dir):
    file_name = PurePath(url).name
    file_path = Path.join(dir, file_name)
    text = ''
    
    try:
        response = requests.get(url)
        if response.ok:
            text = response.text
        else:
            print('Bad response for', url, response.status_code)
    except requests.exceptions.ConnectionError as exc:
        print(exc)
        
    with open(file_path, 'w') as fh:
        fh.write(text)
    
    # debug
    print("downloaded html:")
    print(text)
    return(file_path)
    
def parse_html(path):
    with open(path, 'r') as fh:
        content = fh.read()

    return BeautifulSoup(content, 'html.parser')

def transform(soup: BeautifulSoup):
    songs = []
    containers = soup.find_all(id='container')
    for item in containers:
        if item is not None:
            songs.append(item.get_text())
    return songs

def run(path):
    soup = parse_html(path)
    content = transform(soup)
    unserialized = []
    for song in content:
        unserialized.append(song.strip() if song is not None else '')

    return unserialized

if __name__ == "__main__":
    # debug: test with random profile
    url = "https://soundcloud.com/notsorhody/reposts"

    # debug: test with Zonz's profile
    # url = "https://soundcloud.com/user-636779687/reposts"

    elem = extract(url)
    if elem is not None:
        with open('reposts.txt', 'w') as fh:
            fh.write(elem)
        print("wrote songs to reposts.txt")
        print(elem)
    else:
        print("Sorry, could not extract data")