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
import sys

Point = NamedTuple('Point', [('x',float),('y',float)])

def extract(url: str):
    elem = ''
    # uncomment for headless
    # fireFoxOptions = webdriver.FirefoxOptions()
    # fireFoxOptions.set_headless()
    # driver = webdriver.Firefox(firefox_options=fireFoxOptions)
    driver = webdriver.Firefox()
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
    
    first_art = WebDriverWait(driver, 10).until(
                EC.visibility_of(
                    driver.find_element(By.CLASS_NAME, "sound__coverArt")            
                )
            )
    art_size = first_art.rect
    
    try:
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(first_art,art_size["width"] + 1, art_size["height"] + 1)
        # actions.send_keys(Keys.F11)
        actions.send_keys(Keys.PAGE_DOWN)
        actions.perform()
        
        scrollReposts(driver)
        # # Make a copy of relevant data, because Selenium will throw if
        # # you try to access the properties after the driver quit
        # page_source = driver.page_source
        # path = save(page_source, '.')
        time.sleep(3)
    finally:
        driver.close()

    # songs_array = run(path)

    # for song in songs_array:
    #     elem = elem + song + '\n'

    # return elem

def scrollReposts(driver: webdriver):
    print("Scrolling")
    # delimiter of reposts page, signals bottom of reposts list
    # <div class="paging-eof sc-border-light-top" title=""></div>
    css_selector = ".paging-eof"
    condition = True
    while condition:
        # cover_art = None
        # art_size_x = 0
        # art_size_y = 0
        # while art_size_y <= 0:
        #     cover_art = driver.find_element(By.CLASS_NAME, "sound__coverArt")
        #     art_size = cover_art.rect
        #     art_size_x = art_size["width"]
        #     art_size_y = art_size["height"]

        actions = ActionChains(driver)
        # actions.move_to_element_with_offset(cover_art, art_size_x + 1, art_size_y + 1)
        # actions.send_keys(Keys.F11)
        actions.send_keys(Keys.PAGE_DOWN)
        actions.perform()
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

def save(text, dir):
    file_name = PurePath(url).name + '.html'
    file_path = Path.join(dir, file_name)
        
    with open(file_path, 'w') as fh:
        fh.write(text)
    
    # debug
    print("~~~~~~~~~~~~~downloaded html~~~~~~~~~~~~~")
    print(text)
    return(file_path)
    
def parse_html(path):
    with open(path, 'r') as fh:
        content = fh.read()

    return BeautifulSoup(content, 'html.parser')

def transform(soup: BeautifulSoup):
    songs = []
    div_repost_lazyList = soup.find("div", class_="userReposts lazyLoadingList")
    ul_repost_list = div_repost_lazyList.contents[0]
    
    for repost_item in ul_repost_list.children:
        if repost_item is not None:
            coverArt_link = repost_item.find("a", class_="sound__coverArt")
            song = coverArt_link.get('href')
            songs.append(song)
    return songs

def run(path):
    soup = parse_html(path)
    content = transform(soup)
    songs_list = []
    for song in content:
        stripped_song = song.strip() if song is not None else ''
        full_url = "https://soundcloud.com" + stripped_song
        songs_list.append(full_url)

    return songs_list

if __name__ == "__main__":
    # debug: test with random profile
    url = "https://soundcloud.com/notsorhody/reposts"

    # debug: test with Zonz's profile
    # url = "https://soundcloud.com/user-636779687/reposts"

    elem = extract(url)
    if elem is not None:
        with open('reposts-1.txt', 'w') as fh:
            fh.write(elem)
        print("wrote songs to reposts-1.txt")
        print(elem)
    else:
        print("Sorry, could not extract data")