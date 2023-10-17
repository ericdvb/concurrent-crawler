import requests
import html2text
import re
from pprint import pprint
from bs4 import BeautifulSoup, NavigableString

def main(response, void_list = []):

    # only works for first sample brex link
    # parsed = BeautifulSoup(r.text, "html.parser").find("main")
    print('entered parse_to_md')
    breakpoint()
    if isinstance(response, BeautifulSoup):
        parsed = response
    else:
        parsed = BeautifulSoup(response.text, "html.parser")

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

    markdown_result = html2text.html2text(parsed.prettify())
    return markdown_result