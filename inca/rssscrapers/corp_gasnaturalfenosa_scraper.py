import requests
import datetime
from lxml.html import fromstring
from core.scraper_class import Scraper
from scrapers.rss_scraper import rss
from core.database import check_exists
import feedparser
import re
import logging

logger = logging.getLogger(__name__)

def polish(textstring):
    #This function polishes the full text of the articles - it separated the lead from the rest by ||| and separates paragraphs and subtitles by ||.
    lines = textstring.strip().split('\n')
    lead = lines[0].strip()
    rest = '||'.join( [l.strip() for l in lines[1:] if l.strip()] )
    if rest: result = lead + ' ||| ' + rest
    else: result = lead
    return result.strip()

class gnf(rss):
    """Scrapes Gas Natural Fenosa"""

    def __init__(self):
        self.doctype = "gnf (corp)"
        self.rss_url ='http://prensagnf.azurewebsites.net/feed/'
        self.version = ".1"
        self.date = datetime.datetime(year=2017, month=7, day=5)

    def parsehtml(self,htmlsource):
        '''                                                                                                                                                                                                                                                                 
        Parses the html source to retrieve info that is not in the RSS-keys                                                                                                                                                                                                 


        Parameters                                                                                                                                                                                                                                                         
        ----                                                                                                                                                                                                                                                               
        htmlsource: string                                                                                                                                                                                                                                                
            html retrived from RSS feed                                                                                                                                                                                                                                    


        yields                                                                                                                                                                                                                                                             
        ----                                                                                                                                                                                                                                                               
        title    the title of the article                                                                                                                                                                                                                                   
        teaser    the intro to the artcile                                                                                                                                                                                                                                  
        text    the plain text of the article                                                                                                                                                                                                                               
        '''

        tree = fromstring(htmlsource)
        try:
            title="".join(tree.xpath('//*/h2[@class="entry-title"]/a//text()')).strip()
        except:
            title = ""
            logger.warning("Could not parse article title")
        try:
            teaser="".join(tree.xpath('//*[@class="post-content"]/ul//text()')).strip()
        except:
            logger.debug("Could not parse article teaser")
            teaser= ""
            teaser_clean = " ".join(teaser.split())
        try:
            text="".join(tree.xpath('//*[@class="post-content"]/p//text()')).strip()
        except:
            logger.debug("Could not parse article text")
            text = ""
        text = "".join(text)
        releases={"title":title.strip(),
                  "teaser":teaser.strip(),
                  "text":polish(text).strip()
                  }

        return releases
