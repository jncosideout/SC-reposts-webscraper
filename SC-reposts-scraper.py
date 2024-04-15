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
from datetime import datetime
from collections import namedtuple
from typing import NamedTuple
from os import path as Path
from pathlib import PurePath
from bs4 import BeautifulSoup
import argparse
from random import uniform
from signal import signal, SIGINT, SIGTERM, SIGQUIT

# Globals
Point = NamedTuple('Point', [('x',float),('y',float)])
driver: Firefox
page_source: str
continue_scrolling = True
scrolling_started = False

def handleInterrupt(signal, frame):
    '''Intended to stop scrolling the page early so page_source can be captured
    and processed when the user sends a keyboard interrupt Ctrl+C for SIGINT or Ctrl+\ for SIGQUIT

    WARNING: Sending SIGINT to the parent process (e.g. shell when invoking SC-reposts-scraper.py
    or when running in a vscode debug session) will also kill the webdriver marionette process
    causing the webdriver to throw several errors, such as urllib3.exceptions.MaxRetryError
    or selenium-specific errors when accessing webdriver properties

    Therefore, only send SIGINT to the python process running the script itself

    '''
    signal_name = ''
    match signal:
        case 2:
            signal_name = 'SIGINT'
        case 3:
            signal_name = 'SIGQUIT'
        case 15:
            signal_name = 'SIGTERM'
        case _:
            signal_name = 'Unknown: {}'.format(str(signal))
            
    global continue_scrolling
    print(f'{signal_name} System signal captured')
    if scrolling_started == True:
        print('scrolling will not continue')
        continue_scrolling = False

signal(SIGINT, handleInterrupt)
signal(SIGTERM, handleInterrupt)
signal(SIGQUIT, handleInterrupt)

def scrapeReposts(url: str):
    global page_source, driver
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
    # https://stackoverflow.com/questions/44777053/selenium-movetargetoutofboundsexception-with-firefox
    # Browsers other than Firefox treat Webdrivers move_to_element action as scroll to part
    # of page with element, then hover over it. Firefox seems to have taken a hardline stance
    # that move_to_element is just "hover over" and we are waiting for a scroll action to fix this.
    # For now you have to workaround this bug using javascript
    driver.execute_script("arguments[0].scrollIntoView();", first_art)

    try:
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(first_art,
                                            art_size["width"] + 1,
                                             art_size["height"] + 1)
        actions.send_keys(Keys.PAGE_DOWN)
        actions.perform()
        print("got first art cover and did first pagedown")
        scrollReposts(driver)
    finally:
        # # Make a copy of relevant data, because Selenium will throw if
        # # you try to access the properties after the driver quit
        page_source = driver.page_source
        driver.close()
        driver.quit()

def scrollReposts(driver: webdriver):
    global continue_scrolling, scrolling_started
    scrolling_started = True
    print("Scrolling")
    startTime = datetime.now()
    scrollCount = 0
    # delimiter of reposts page, signals bottom of reposts list
    # <div class="paging-eof sc-border-light-top" title=""></div>
    css_selector_name = "paging-eof"
    css_selector = "." + css_selector_name

    while continue_scrolling:
        if scrollLimit > 0 and scrollCount > scrollLimit:
            print(f"scroll limit hit, scrolled {scrollCount} times")
            break
        scrollCount += 1

        actions = ActionChains(driver)
        actions.send_keys(Keys.PAGE_DOWN)
        actions.perform()
        # randomize the wait time to avoid bot detection
        pause = uniform(1.0, 3.0)
        try:
            element = WebDriverWait(driver, pause).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, css_selector)            
                )
            )
            
        except TimeoutException:
            continue
        except Exception as ex:
            print('Encountered exception type ({}) while scrolling'.format(type(ex)))
            break
        else:
            isFound = css_selector_name in element.get_attribute("class")
            continue_scrolling = not isFound
            if isFound:
                print(f"Finished scrolling to {css_selector_name}, scrolled {scrollCount} times")
    endTime = datetime.now()
    execution = endTime - startTime
    print(f"scrolling execution time was {execution}")

def save(text, dir):
    file_name = PurePath(url).name + '.html'
    file_path = Path.join(dir, file_name)
        
    with open(file_path, 'w') as fh:
        fh.write(text)
    
    # debug
    print("~~~~~~~~~~~~~downloaded html~~~~~~~~~~~~~")
    print(f"saved to {file_path}")
    return(file_path)
    
def parse_html():
    return BeautifulSoup(page_source, 'html.parser')

def transform(soup: BeautifulSoup):
    print("processing soup")
    songs = []
    if   soup is None:
        return
    div_repost_lazyList = soup.find("div", class_="userReposts lazyLoadingList")
    try:
        ul_repost_list = div_repost_lazyList.contents[0]
    except Exception as ex:
        print('Encountered exception type ({}) while transforming soup'.format(type(ex)))
        print(ex.with_traceback)
        return

    for repost_item in ul_repost_list.children:
        if repost_item is not None:
            coverArt_link = repost_item.find("a", class_="sound__coverArt")
            song = coverArt_link.get('href')
            songs.append(song)
    print("done")            
    return songs


def run():
    startTime = datetime.now()
    soup = parse_html()
    content = transform(soup)
    songs_list = []
    if content is None:
        return
    for song in content:
        stripped_song = song.strip() if song is not None else ''
        full_url = "https://soundcloud.com" + stripped_song
        songs_list.append(full_url)

    endTime = datetime.now()
    execution = endTime - startTime
    print(f"parsing exectution time was {execution}")
    return songs_list

if __name__ == "__main__":
    url = "https://soundcloud.com/sour_cream_pringles/reposts"
    startTime = datetime.now()

    parser = argparse.ArgumentParser("SC-reposts-scraper", argument_default=argparse.SUPPRESS)
    parser.add_argument("saved_page_path",
                        metavar="path/to/reposts.html",
                        nargs='?',                        
                        help="path to html file of saved reposts webpage to parse")
    parser.add_argument("--scroll-limit",
                        nargs='?',
                        help="limit for number of times webdriver scrolls with pageDown",
                        type=int)
    args = parser.parse_args()

    pathToHtml = ''
    if hasattr(args, "saved_page_path"):
        pathToHtml = args.saved_page_path
    scrollLimit = 0
    if hasattr(args, "scroll_limit"):
        scrollLimit = args.scroll_limit
    
    if pathToHtml != '':
        try:
            print(f'parsing local html {pathToHtml}')
            with open(pathToHtml, 'r') as fh:
                page_source = fh.read()
        except (FileNotFoundError, OSError) as e:
            print(f'{pathToHtml} could not be opened')
            print(e)
            quit()
    else:
        scrapeReposts(url)
    
    songs_array = run()
    songList = ''

    if songs_array is not None:
        try:
            for song in songs_array:
                songList = songList + song + '\n'
            with open('reposts-1.txt', 'w') as fh:
                fh.write(songList)
            print("wrote songs to reposts-1.txt")
        except Exception as ex:
            print('Error writing songs to file {}'.format(type(ex)))
            if pathToHtml == '':
                save(page_source, '.')
    else:
        print("Sorry, could not extract data")
        if pathToHtml == '':
            save(page_source, '.')

    endTime = datetime.now()
    execution = endTime - startTime
    print(f"total exectution time was {execution}")