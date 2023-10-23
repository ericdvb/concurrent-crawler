import re
from time import sleep
import html2text
from bs4 import BeautifulSoup, NavigableString

def parse_to_markdown(base_url, path, response, urls_to_visit, urls_lock, avoid_list=[]):
    result_string = f'subprocess with path: {path}'
    print(result_string)
    parsed = BeautifulSoup(response.text, "html.parser")
    print('finished parsing for path:', path, flush=True)

    links = list(map(lambda link: link['href'], parsed('a', href=re.compile(rf'^(/|{base_url})'))))
    print('processing links for path:', path, flush=True)
    for link in links:
        print('checking if link is in path and waiting to write:', link, flush=True)
        urls_lock.acquire()
        if link not in urls_to_visit:
            print('writing link to link list', link, flush=True)
            urls_to_visit.append(link)
        urls_lock.release()

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

    with open(f'{path.replace("/", "_")}', "a+") as f:
        print('writing file', flush=True)
        f.write(markdown_result)
        print('file written', flush=True)
    return (links, result_string)