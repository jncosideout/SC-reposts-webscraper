# SoundCloud reposts webscraper for Sour_Cream_Pringles@soundcloud.com
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
from datetime import datetime
from collections import namedtuple
from typing import NamedTuple
from os import path as Path
from pathlib import PurePath
from bs4 import BeautifulSoup

Point = NamedTuple('Point', [('x',float),('y',float)])

def extractSongList(url: str):
    songList = ''
    # uncomment for headless
    # fireFoxOptions = webdriver.FirefoxOptions()
    # fireFoxOptions.add_argument("-headless")
    # driver = webdriver.Firefox(options=fireFoxOptions)

    # uncomment for not headless
    driver = webdriver.Firefox()

    driver.get(url)    
    print("loaded page")

    # grab first song album art for starting reference point to scroll on page
    first_art = WebDriverWait(driver, timeout=5).until(
                    EC.visibility_of_element_located(
                        (By.CLASS_NAME, "sound__artwork")            
                    )
                )
    art_size = first_art.rect
    
    try:
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(first_art,
                                            art_size["width"] + 1,
                                             art_size["height"] + 1)
        actions.send_keys(Keys.PAGE_DOWN)
        actions.perform()
        print("got first art cover and did first pagedown")
        scrollReposts(driver)
        # # Make a copy of relevant data, because Selenium will throw if
        # # you try to access the properties after the driver quit
        global page_source
        page_source = driver.page_source
        global path 
        # path = save(page_source, '.')
        # print(f"saved to {path}")
    finally:
        driver.close()

    songs_array = run()

    for song in songs_array:
        songList = songList + song + '\n'

    return songList

def scrollReposts(driver: webdriver):
    print("Scrolling")
    startTime = datetime.now()
    scrollCount = 0
    # delimiter of reposts page, signals bottom of reposts list
    # <div class="paging-eof sc-border-light-top" title=""></div>
    css_selector_name = "paging-eof"
    css_selector = "." + css_selector_name
    condition = True
    while condition:
        scrollCount += 1
        actions = ActionChains(driver)
        actions.send_keys(Keys.PAGE_DOWN)
        actions.perform()
        try:
            element = WebDriverWait(driver, 1).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, css_selector)            
                )
            )
            
        except TimeoutException:
            condition = True
        else:
            isFound = css_selector_name in element.get_attribute("class")
            condition = not isFound
            print(f"done scrolling, scrolled {scrollCount} times")
    endTime = datetime.now()
    execution = endTime - startTime
    print(f"scrolling exectution time was {execution}")

def save(text, dir):
    file_name = PurePath(url).name + '.html'
    file_path = Path.join(dir, file_name)
        
    with open(file_path, 'w') as fh:
        fh.write(text)
    
    # debug
    print("~~~~~~~~~~~~~downloaded html~~~~~~~~~~~~~")
    return(file_path)
    
def parse_html():
    # with open(path, 'r') as fh:
    #     content = fh.read()

    return BeautifulSoup(page_source, 'html.parser')

def transform(soup: BeautifulSoup):
    print("processing soup")
    startTime = datetime.now()
    songs = []
    div_repost_lazyList = soup.find("div", class_="userReposts lazyLoadingList")
    ul_repost_list = div_repost_lazyList.contents[0]
    
    for repost_item in ul_repost_list.children:
        if repost_item is not None:
            coverArt_link = repost_item.find("a", class_="sound__coverArt")
            song = coverArt_link.get('href')
            songs.append(song)
    print("done")            

    endTime = datetime.now()
    execution = endTime - startTime
    print(f"parsing exectution time was {execution}")

    return songs


def run():
    soup = parse_html()
    content = transform(soup)
    songs_list = []
    for song in content:
        stripped_song = song.strip() if song is not None else ''
        full_url = "https://soundcloud.com" + stripped_song
        songs_list.append(full_url)

    return songs_list

if __name__ == "__main__":
    url = "https://soundcloud.com/sour_cream_pringles/reposts"
    startTime = datetime.now()
    songList = extractSongList(url)
    if songList is not None:
        with open('reposts-1.txt', 'w') as fh:
            fh.write(songList)
        print("wrote songs to reposts-1.txt")
    else:
        print("Sorry, could not extract data")
    endTime = datetime.now()
    execution = endTime - startTime
    print(f"total exectution time was {execution}")