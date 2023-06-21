# SoundCloud Reposts Webscraper
Python script that uses Selenium and BeautifulSoup to scrape users' public reposts pages to get all the urls of songs they reposted.
I use this in tandem with my https://github.com/jncosideout/SoundCloud-Mastadon-repost-bot
Unfortunately, SoundCloud stopped accepting new requests for API keys 3 years ago. So I couldn't tap into my SC account and get my reposts feed.
So I learned how to build a webscraper and automate the processing of my huge list of songs.

The script has to scroll to the bottom of a "reposts" page so the lazy-loading list completely serves all songs. Then it saves the webpage to parse it later with BeautifulSoup. Earlier versions of the script saved it to a file, but loading that file back into memory took a very long time. The script can be easily modified to do it that way again.