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
        self.chapters = None

    def print_chapters(self, indent=0, chapters=None):
        """
        Prints the chapter list.
        :param indent: Starting indent (increasing by 2 for each level of
        subchapters).
        :param chapters: The list of chapters to print (If None, the
        `Book` instances chapter list will be used).
        """
        if chapters is None:
            chapters = self.chapters

        for c in chapters:
            print('{}{}'.format(indent*' ', c['name']))
            if c['subchapters']:
                self.print_chapters(indent+2, c['subchapters'])


def get_chapter_list(soup):
    """
    Parse the chapter list contained in the given element.
    :param soup: A BeautifulSoup instance containing a Table of Contents element.
    :returns: A list of chapter names and their subchapters.
    """
    chapters = []

    for c in soup.children:
        if c.name == 'li':
            subchapters = c.find('ol')

            if subchapters:
                chapters.append({'name': c.contents[0].text,
                                 'subchapters': get_chapter_list(subchapters)})
            else:
                chapters.append({'name': c.text, 'subchapters': []})

    return chapters

def get_toc(soup):
    """
    Searches for the Table of Contents element in the given element.
    :param soup: A BeautifulSoup instance.
    :returns: A list of chapter names and their subchapters.
    """
    toc = soup.find(class_='toc')
    chapters = []
    found_first_list = False
    chapter_list = None
    
    for c in toc.children:
        if c.name == 'p':
            chapters.append({'name': c.text, 'subchapters': []})
        if c.name == 'ol':
            chapter_list = c

    chapters.extend(get_chapter_list(chapter_list))
    return chapters

def scrape(url, book):
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

    if book.author is None:
        author = content.find(class_='author')
        book.author = author.text

    if book.chapters is None:
        book.chapters = get_toc(content)

    next_link = content.next_sibling.next_sibling
    if next_link.name == 'a':
        if '<<' in next_link.text:
            next_link = next_link.next_sibling.next_sibling
            if next_link.name != 'a' or '>>' not in next_link.text:
                return

        scrape('{}{}'.format('http://gutenberg.spiegel.de',
                             next_link['href']),
               book)

@click.command()
@click.argument('URL')
def main(url):
    book = Book(url)
    scrape(url, book)

if __name__ == '__main__':
    main()
