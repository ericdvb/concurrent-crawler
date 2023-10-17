import requests
import html2text
import re
from pprint import pprint
from bs4 import BeautifulSoup, NavigableString

def main(url = "", avoid_list = []):
    # sampleUrl = "https://www.brex.com/journal/how-to-manage-runaway-saas-spend"
    # sampleUrl = "https://sprig.com/customers/chipper-cash"
    # sampleUrl = "https://docs.sprig.com/docs/team-discovery"
    sampleUrl = "https://www.timescale.com"
    r = requests.get(sampleUrl)
    r.encoding = "utf-8"

    # only works for first sample brex link
    # parsed = BeautifulSoup(r.text, "html.parser").find("main")
    parsed = BeautifulSoup(r.text, "html.parser")

    # ignore image content
    for img in parsed.find_all("img"):
        img.decompose()

    # ignore links that contain anything other than plain text
    for link in parsed("a"):
        for child in link.contents:
            # if child.name not in ['style', 'span', 'p', 'i', 'strong'] and type(child) != 'string':
            if type(child) != NavigableString and child.name not in ['style', 'p']:
                link.decompose()
    
    # handle avoid_list
    for selector in avoid_list:
        for selected in parsed.find_all(True, { "class": selector }):
            selected.decompose()
        selected = parsed.find(True, id=selector)
        if selected != None:
            selected.decompose()

    standard_elements_to_ignore = ["nav", "header", "footer", "button"]
    for tag in standard_elements_to_ignore:
        for element in parsed.find_all(tag):
            element.decompose()

    for element in parsed(True):
        if element.hidden == True:
            element.decompose()

    # find all dispay:none styles
    #display_none_styles = parsed(text=re.compile(r'display:\s*none'))

    # find elements with the given classes
    # for style in display_none_styles:
    #   class_name = style["data-emotion"].replace(" ", "-")
    #   for selected in parsed(True, { 'class': class_name }):
    #       selected.decompose()

    md = html2text.html2text(parsed.prettify())
    print(md)

main(url="", avoid_list=[])