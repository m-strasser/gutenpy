#!/usr/bin/env python3
"""
Scrapes books from gutenberg.spiegel.de
"""
import click
import requests
from bs4 import BeautifulSoup


class Book:
    """
    Stores information about a book.
    """
    def __init__(self, url):
        self.url = url
        self.author = None
        self.title = None
        self.year = None
        self.chapters = []

    def _find_chapter(self, soup, url):
        chapter_ = soup.find('h1')

        if chapter_:
            chapter = Chapter(chapter_.text, url)
            self.chapters.append(chapter)

            subtitle = soup.find('h2')
            if subtitle:
                chapter.subtitle = subtitle.text

            return (chapter, True)
        else:
            return (self.chapters[-1], False)

    def _find_subchapter(self, soup, chapter, url, level=2):
        subchap_ = soup.find('h{}'.format(level))

        if subchap_:
            subchapter = Chapter(subchap_.text, url)
            chapter.subchapters.append(subchapter)

            subtitle = soup.find('h{}'.format(level+1))
            subchapter.subtitle = subtitle.text

            return (subchapter, True)
        elif len(chapter.subchapters) > 0:
            return (chapter.subchapters[-1], False)
        else:
            return (None, False)

    def parse_site(self, soup, url, is_first=False):
        if not is_first:
            chapter, created = self._find_chapter(soup, url)
            if created:
                return chapter.parse_paragraph(soup, url)

            subchapter, created = self._find_subchapter(soup, chapter, url)
            if created:
                return subchapter.parse_paragraph(soup, url)

            ssubchapter, created = self._find_subchapter(soup, chapter, url,
                level=3)
            if created:
                return ssubchapter.parse_paragraph(soup, url)
        else:
            author = soup.find(class_='author')
            title = soup.find(class_='title')
            year = soup.find('h4')

            self.author = author.text
            self.title = title.text
            self.year = year.text.lstrip('(').rstrip(')')

            chapter = Chapter('Backtext', url)
            chapter.parse_paragraph(soup, url)

class Chapter:
    """
    Stores information about a chapter.
    """
    def __init__(self, name, url, parent = None, prev_=None, next_=None, subchapters=[]):
        self.name = name
        self.url = url
        self.subchapters = subchapters
        self.parent = parent
        self.prev = prev_
        self.next = next_
        self.paragraphs = []

    def parse_paragraph(self, soup, url, is_first=False):
        """
        Parses a paragraph (i.e. a site from Gutenberg).
        :param soup: The BeautifulSoup instance containing
        the paragraph.
        :param url: The URL to the paragraph's site.
        :param is_first: True for the first site of the book
        (to correctly extract chapter names).
        """
        self.paragraphs.append(
            Paragraph(url, soup.find_all('p')))


class Paragraph:
    """
    Stores information about a paragraph (i.e. a page on the Project
    Gutenberg site).
    """
    def __init__(self, url, text):
        self.url = url
        self.text = text


def get_chapter_list(soup, parent=None):
    """
    Parse the chapter list contained in the given element.
    :param soup: A BeautifulSoup instance containing a Table of Contents element.
    :returns: A list of chapter names and their subchapters.
    """
    chapters = []
    prev_chapter = None

    for c in soup.children:
        if c.name == 'li':
            subchapters = c.find('ol')

            if subchapters:
                chapter = Chapter(name=c.contents[0].text,
                                  prev_=prev_chapter,
                                  parent=parent)
                chapter.subchapters = get_chapter_list(subchapters,
                    chapter)
            else:
                chapter = Chapter(name=c.text,
                                  prev_=prev_chapter,
                                  parent=parent)

            if prev_chapter:
                prev_chapter.next = chapter

            chapters.append(chapter)
            prev_chapter = chapter

    return chapters

def get_toc(soup):
    """
    Searches for the Table of Contents element in the given element.
    :param soup: A BeautifulSoup instance.
    :returns: A list of chapter names and their subchapters.
    """
    toc = soup.find(class_='toc')
    prev_chapter = None
    chapters = []
    found_first_list = False
    chapter_list = None
    
    for c in toc.children:
        if c.name == 'p':
            chapter = Chapter(c.text, prev_chapter)
            if prev_chapter:
                prev_chapter.next = chapter

            chapters.append(chapter)
            prev_chapter = chapter
        if c.name == 'ol':
            chapter_list = c

    chapters.extend(get_chapter_list(chapter_list))
    return chapters


def scrape(url, book, is_first=False):
    """
    Scrapes the given URL and stores the result in the given `Book`
    instance.
    :param url: The URL to the first page of a Project Gutenberg book.
    :param book: An instance of `Book` storing the scraping results.
    """
    print('Scraping {}...'.format(url))
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.find(id='gutenb')

    book.parse_site(content, url, is_first)

    # Find the link to the next page.
    next_link = content.next_sibling.next_sibling
    if next_link.name == 'a':
        if '<<' in next_link.text:
            next_link = next_link.next_sibling.next_sibling
            if next_link.name != 'a' or '>>' not in next_link.text:
                # Last page, return.
                return

        scrape('{}{}'.format('http://gutenberg.spiegel.de',
                             next_link['href']),
               book)

@click.command()
@click.argument('URL')
def main(url):
    book = Book(url)
    scrape(url, book, True)

if __name__ == '__main__':
    main()
