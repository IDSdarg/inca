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

class irishexaminer(rss):
    """Scrapes irishexaminer.com"""

    def __init__(self,database=True):
        self.database=database
        self.doctype = "irishexaminer (www)"
        self.rss_url= "http://feeds.examiner.ie/ietopstories"
        self.version = ".1"
        self.date    = datetime.datetime(year=2017, month=8, day=30)

    def parsehtml(self,htmlsource):
        '''
        Parses the html source to retrieve info that is not in the RSS-keys
        In particular, it extracts the following keys (which should be available in most online news:
        section    sth. like economy, sports, ...
        text        the plain text of the article
        byline      the author, e.g. "Bob Smith"
        byline_source   sth like ANP
        '''
    
        try:
            tree = fromstring(htmlsource)
        except:
            logger.warning("cannot parse?",type(doc),len(doc))
            logger.warning(doc)
            return("","","", "")
        try:
            title = tree.xpath("//*[@class='col-left-story']//h1/text()")
        except:
            title = ""
            logger.info("No 'title' field encountered - don't worry, maybe it just doesn't exist.")
        try:        
            text = " ".join(tree.xpath("//*[@class='ctx_content']//story/p/text()"))   
        except:
            text = ""
            logger.info("No 'text' field encountered - don't worry, maybe it just doesn't exist.")
        try:
            teaser = " ".join(tree.xpath("//*[@class='ctx_content']/p//text()"))
        except:
            teaser = ""
            logger.info("No 'teaser' field encountered - don't worry, maybe it just doesn't exist")
        try:
            byline = tree.xpath("//*[@class='byline']//text()")[-1]
        except:
            byline = ""
            logger.info("No 'byline' field encountered - don't worry, maybe it just doesn't exist.")
            
        extractedinfo={"title":title,
                       "text":text.strip().replace("\n",""),
                       "teaser":teaser.replace("\xa0",""),
                       "byline":byline.strip()
                       }

        return extractedinfo    