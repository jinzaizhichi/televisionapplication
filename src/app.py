from playwright.sync_api import sync_playwright
import requests
import re
import urllib
import json
import os
import yaml
import time
import datetime
from flask import Flask
from flask import redirect

app = Flask(__name__)


datadir = os.environ["DATADIR"]
with open(os.path.join(datadir, "config.yml"), 'r') as file:
    config = yaml.safe_load(file)

class TokenError(Exception):
    pass
class BlockedChannelError(Exception):
    pass

class Tokensniffer:
    def __init__(self, page):
        self.token = None
        self.page = page
    def refresh(self):
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.on("request", self.onRequest)
            page.goto(urllib.parse.urljoin(config["tv_url"] , "/tv/" + self.page + "/"))
            browser.close()
    def onRequest(self, request):
        streamregex = "/live/streams/([^\_]*).m3u8"
        print(request.url)
        if re.search(streamregex, request.url) != None:
            self.token = request.url
            print("new token: " + str(self.token))
        else:
            return False

def listChannels():
    res = {}
    channelListRegex = "<a class=\"list-group-item\" href=\"/tv/(.*)/\">(.*)</a>"
    indexHTML = requests.get(config["tv_url"]).text
    for line in indexHTML.splitlines():
        search = re.search(channelListRegex, line)
        if search == None:
            continue
        name = search.group(2)
        url = search.group(1)
        res[name.replace("&amp;", "&")] = url
    return res

def getStreamUrl(page):
    token = Tokensniffer(page)
    token.refresh()
    return token.token

def getStream(page):
    if page not in channels.values():
        raise KeyError()
    if page not in streams.keys():
        streams[page] = getStreamUrl(page)
    if streams[page] == None:
        raise BlockedChannelError
    r3 = requests.get(streams[page])
    if r3.status_code != 200:
        raise TokenError("Invalid or Expired token")
    for line in r3.text.splitlines():
        if line.startswith("#"):
            continue
        if "_high.m3u8" in line:
            return urllib.parse.urljoin(streams[page], line)
#token = Tokensniffer("fox-news-channel-live-stream")
#token.refresh()
channels = listChannels()
streams = {}




@app.route("/channels.m3u")
def fullm3u():
    m3u = "#EXTM3U"
    for i, value in channels.items():
        m3u += "\n#EXTINF:-1 tvg-chno=\"%s\",%s\n%s/channel/%s" % (str(list(channels.keys()).index(i) + 1), i, config["visible_url"], value)
    return(m3u)
@app.route("/channel/<channel>")
def appchannel(channel):
    try:
        res = getStream(channel)
        return redirect(res)
    except TokenError:
        streams[channel] = getStreamUrl(channel)
        res = getStream(channel)
        return redirect(res)
    except BlockedChannelError:
        return ("Channel is blocked", 403) 
    except KeyError:
        return ("Channel does not exist", 404)
