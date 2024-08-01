import os
import random
import re

import google.generativeai as genai
import requests
import wikipedia
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
GEMINI_KEY = os.getenv("GOOGLE_API_KEY")
WIKI_REQUEST = "http://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles="


genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


def get_wiki_facts(prompt: str, number: int = 5) -> list:
    """Fetch factual one liners from Wikipedia.

    Parameters
    ----------
    prompt : str
        Name of the article to fetch facts from.
    number : int, optional
        Number of facts (default is 5).

    Returns
    -------
    list
        *number* amount of facts based on *prompt*.

    """
    return random.sample(split_into_sentences(wikipedia.summary(prompt, auto_suggest=False)), k=number)


def create_false_statement(fact: str) -> str:
    """Get a false fact based on a true fact.

    Parameters
    ----------
    fact : str
        The true fact.

    Returns
    -------
    str
        Falsified version of the fact.

    """
    prompt = f"Create a false fact for a True False quiz based on this fact: {fact} in one line. Answer directly and only the false statement."  # noqa: E501
    response = model.generate_content(prompt)
    return response.text


def get_wiki_image(search_term: str) -> str | bool:
    """Return featured image URL of search.

    This function may fail because of many reasons, e.g.
    if the connection failed, or if the parsing did not
    go as expected. False is returned to indicate failure.

    Parameters
    ----------
    search_term : str
        The search term to use for the Wiki image search.

    Returns
    -------
    str
        URL of the image.
    bool
        Returns False if any error occured.

    """
    try:
        wikipedia.set_lang("en")
        result = wikipedia.search(search_term, results=1)
        if not result:
            return False

        wkpage = wikipedia.WikipediaPage(title=result[0])
        response = requests.get(wkpage.url, timeout=3)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        infobox = soup.find("table", {"class": "infobox"})
        if not infobox:
            return False

        image_tag = infobox.find("img", class_="mw-file-element")
        if not image_tag:
            return False

        image_url = image_tag["src"]
        if image_url.startswith("//"):
            image_url = "https:" + image_url

        return image_url  # noqa: TRY300
    except Exception:
        return False


# Credits to https://stackoverflow.com/questions/4576077/how-can-i-split-a-text-into-sentences
alphabets = "([A-Za-z])"
prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = (
    r"(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
)
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov|edu|me)"
digits = "([0-9])"
multiple_dots = r"\.{2,}"


def split_into_sentences(text: str) -> list[str]:
    r"""Split the text into sentences.

    If the text contains substrings "\<prd\>" or "\<stop\>", they would lead
    to incorrect splitting because they are used as markers for splitting.

    Parameters
    ----------
    text : str
        Text to be split into sentences.

    Returns
    -------
    list[str]
        list of sentences

    """
    text = " " + text + "  "
    text = text.replace("\n", " ")
    text = re.sub(prefixes, "\\1<prd>", text)
    text = re.sub(websites, "<prd>\\1", text)
    text = re.sub(digits + "[.]" + digits, "\\1<prd>\\2", text)
    text = re.sub(multiple_dots, lambda match: "<prd>" * len(match.group(0)) + "<stop>", text)
    if "Ph.D" in text:
        text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub(r"\s" + alphabets + "[.] ", " \\1<prd> ", text)
    text = re.sub(acronyms + " " + starters, "\\1<stop> \\2", text)
    text = re.sub(
        alphabets + "[.]" + alphabets + "[.]" + alphabets + "[.]",
        "\\1<prd>\\2<prd>\\3<prd>",
        text,
    )
    text = re.sub(alphabets + "[.]" + alphabets + "[.]", "\\1<prd>\\2<prd>", text)
    text = re.sub(" " + suffixes + "[.] " + starters, " \\1<stop> \\2", text)
    text = re.sub(" " + suffixes + "[.]", " \\1<prd>", text)
    text = re.sub(" " + alphabets + "[.]", " \\1<prd>", text)
    if "”" in text:
        text = text.replace(".”", "”.")
    if '"' in text:
        text = text.replace('."', '".')
    if "!" in text:
        text = text.replace('!"', '"!')
    if "?" in text:
        text = text.replace('?"', '"?')
    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    sentences = text.split("<stop>")
    sentences = [s.strip() for s in sentences]
    if sentences and not sentences[-1]:
        sentences = sentences[:-1]
    return sentences
