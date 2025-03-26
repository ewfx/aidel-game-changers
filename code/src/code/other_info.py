import requests
import pandas as pd
from bs4 import BeautifulSoup
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import wikipedia
from urllib.parse import unquote
import re
from rapidfuzz import fuzz, process


finbert_model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
classifier = pipeline("text-classification", model=finbert_model, tokenizer=finbert_tokenizer)


def check_sanctions(company_name, result):
    print("Verifyin sanctions...")
    df = pd.read_csv('/data/sdn.csv', encoding='latin-1')
    match_found = any(company_name.lower() in str(name).lower() for name in df["SDN Name"])
    result["Sanctioned (OFAC)"] = match_found
    result["Sanctions URL"] = "https://sanctionssearch.ofac.treasury.gov/"
    result["Sanctioned (OFAC) Match"] = ""

    if match_found:
        result["Sanctioned (OFAC) Match"] = next(
            (str(name) for name in df["SDN Name"] if company_name.lower() in str(name).lower()), ""
        )

    # Check the second sanctions file with fuzzy matching on "caption"
    try:
        df_sanctions = pd.read_csv("/data/sanctions.csv", encoding="utf-8")
        captions = df_sanctions["caption"].dropna().astype(str).tolist()
        match, score, _ = process.extractOne(company_name, captions, scorer=fuzz.token_sort_ratio)

        result["Sanctioned (Other)"] = score >= 90
        result["Sanctioned (Other) Match"] = match if score >= 90 else ""
        result["Sanctioned (Other) URL"] = "https://www.opensanctions.org/datasets/default/"  # optional
    except Exception as e:
        result["Sanctioned (Other)"] = False
        result["Sanctioned (Other) Match"] = ""



# ========== PANAMA PAPERS CHECK ==========
def check_panama_papers(company_name, result):
    print("Verifying Panama Papers...")
    search_url = f"https://offshoreleaks.icij.org/search?q={company_name.replace(' ', '+')}"
    r = requests.get(search_url, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    # Look for exact match in the result rows
    found = False
    for tag in soup.select("div.search-results div.result h4"):
        name_text = tag.get_text(strip=True)
        if name_text.lower() == company_name.lower():
            found = True
            break

    if found:
        result["In Panama Papers"] = True
        result["Panama Leak URL"] = search_url


# ========== YAHOO NEWS LINKS ==========
def extract_real_url(yahoo_redirect_url):
    # Extracts the value of RU=... before /RK= or /RS=
    match = re.search(r"RU=(.+?)/(RK|RS|RZ)=", yahoo_redirect_url)
    if match:
        encoded_url = match.group(1)
        return unquote(encoded_url)
    return None

def get_yahoo_news_headlines(company_name, pages=3):
    headers = {"User-Agent": "Mozilla/5.0"}
    all_html = ""
    print("Verifying Yahoo News...")
    # Fetch Yahoo News results for multiple pages
    for page in range(pages):
        start = 1 + page * 10  # page 1: b=1, page 2: b=11, etc.
        query = company_name.replace(" ", "+")
        url = f"https://news.search.yahoo.com/search?p={query}&b={start}"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            all_html += res.text
        else:
            print(f"Failed to fetch page {page + 1}")

    # Parse headlines from combined HTML
    soup = BeautifulSoup(all_html, "html.parser")
    headlines = []

    for h4 in soup.find_all("h4", class_="s-title"):
        a = h4.find("a")
        if a and a.text:
            headlines.append(a.get_text(strip=True))

    return headlines

# ========== SENTIMENT ANALYSIS ==========
def analyze_sentiment_with_finbert(company_name, result):
    headlines = get_yahoo_news_headlines(company_name)
    sentiment_map = {"positive": 1, "neutral": 0, "negative": -1}
    sentiment_scores = []
    print("Performing sentiment analysis...")
    for headline in headlines:
        try:
            output = classifier(headline)[0]
            label = output["label"].lower()
            score = round(output["score"], 3)
            sentiment_scores.append(sentiment_map[label])
            result["News Articles"].append({
                "headline": headline,
                "sentiment": label,
                "confidence": score
            })
        except Exception as e:
            continue

    if sentiment_scores:
        result["Average Sentiment Score"] = round(sum(sentiment_scores) / len(sentiment_scores), 3)
        result["Mentioned in Negative News"] = any(s < 0 for s in sentiment_scores)

# ========== NGO DETECTION ==========
def check_if_ngo(company_name, result):
    print("Verifying if NGO...")
    keywords = ['foundation', 'association', 'ngo', 'non-governmental', 'charity', 'relief', 'aid', 'humanitarian', 'mission', 'trust', 'society']
    name_lower = company_name.lower()
    result["Likely NGO"] = any(word in name_lower for word in keywords)

    try:
        summary = wikipedia.summary(company_name, sentences=2).lower()
        if any(word in summary for word in keywords):
            result["Likely NGO"] = True
            page_url = wikipedia.page(company_name).url
            result["NGO Wiki URL"] = page_url
    except Exception as e:
        pass  # If no page or summary found, just skip

def check_in_warrants_list(company_name, result, filepath="/data/warrants.txt"):
    print("Verifying warrants...")
    warrants = pd.read_fwf(filepath, header=None, names=["name"])
    names_list = warrants["name"].dropna().astype(str).tolist()
    match, score, _ = process.extractOne(company_name, names_list, scorer=fuzz.token_sort_ratio)

    result["In_Warrants_List"] = score >= 90
    result["Warrants_Matched_Name"] = match if score >= 90 else ""
    result["Warrants_Source"] = "OpenSanctions (warrants.txt)"

def check_in_regulatory_list(company_name, result, filepath="/data/regulatory.txt"):
    print("Verifying regulatory risks...")
    regulatory = pd.read_fwf(filepath, header=None, names=["name"])
    names_list = regulatory["name"].dropna().astype(str).tolist()
    match, score, _ = process.extractOne(company_name, names_list, scorer=fuzz.token_sort_ratio)

    result["In_Regulatory_List"] = score >= 90
    result["Regulatory_Matched_Name"] = match if score >= 90 else ""
    result["Regulatory_Source"] = "OpenSanctions (regulatory.txt)"

def check_in_debarred_list(company_name, result, filepath="/data/debarred.txt"):
    print("Verifying Debarred risks...")
    debarred = pd.read_fwf(filepath, header=None, names=["name"])
    names_list = debarred["name"].dropna().astype(str).tolist()
    match, score, _ = process.extractOne(company_name, names_list, scorer=fuzz.token_sort_ratio)

    result["In_Debarred_List"] = score >= 90
    result["Debarred_Matched_Name"] = match if score >= 90 else ""
    result["Debarred_Source"] = "OpenSanctions (debarred.txt)"

def check_in_pep_list(company_name, result, filepath="pep.txt"):
    print("Verifying PEP risks...")
    pep = pd.read_fwf(filepath, header=None, names=["name"])
    names_list = pep["name"].dropna().astype(str).tolist()
    match, score, _ = process.extractOne(company_name, names_list, scorer=fuzz.token_sort_ratio)

    result["Is_PEP"] = score >= 90
    result["PEP_Matched_Name"] = match if score >= 90 else ""
    result["PEP_Source"] = "OpenSanctions (pep.txt)"



def get_other_info_company(company_name):
    print(f"Company is {company_name}")
    result = {
        "Company Name": company_name,
        "Sanctioned (OFAC)": False,
        "Sanctions URL": "",
        "In Panama Papers": False,
        "Panama Leak URL": "",
        "Likely NGO": False,
        "NGO Wiki URL": "",
        "Mentioned in Negative News": False,
        "Average Sentiment Score": 0.0,
        "News Articles": []
    }
    check_sanctions(company_name, result)
    check_panama_papers(company_name, result)
    check_if_ngo(company_name, result)
    analyze_sentiment_with_finbert(company_name, result)
    check_in_warrants_list(company_name, result)
    check_in_debarred_list(company_name, result)

    final_result = pd.DataFrame([result])
    return final_result

def get_other_info_person(person):
    print(f"Person is {person}")
    result = {
        "Person Name": person,
        "Sanctioned (OFAC)": False,
        "Sanctions URL": "",
        "Is_PEP": False}

    check_sanctions(person, result)
    check_panama_papers(person, result)
    check_if_ngo(person, result)
    analyze_sentiment_with_finbert(person, result)
    check_in_warrants_list(person, result)
    check_in_debarred_list(person, result)
    check_in_pep_list(person, result)

    final_result = pd.DataFrame([result])
    return final_result


