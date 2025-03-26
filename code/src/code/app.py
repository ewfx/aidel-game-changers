import spacy
import pandas as pd
import google.generativeai as genai
import json
from sec_info import *
from other_info import *
from summarizer import *

prompt_org = f"Assume you are finance risk officer. You will be given 2 jsons. one json will have information on company name, corrobaration score, conformity score, the same for its parent, headquarters for both and possible CIK number. You have to calculate a risk score for that. A lower conformation and corrobartion score means it's compliant so lower risk. If SIC and CIK are available, that's lower risk because frequent filings. If parent is headquartered in a tax-haven, that needs to be penalised as risky. There will also be a confidence score for how confident we are of that, you need to generate a confidence score your risk score as well. Your output should be risk score, confidence score average and a summary of how you got there under key 'summary'. Json 2 will have true/false values on sanctions ofac and sanction others, presence in panama papers, in warrants, and in debarred lists. Any of these being true must be penalised much harshly than other. There will also be a sentiment analysis score, which if negative should be used to penalise but not extremely. This should have same output as previous json. At the end, final output should be final risk score average, final confidence average, full explaination from both json and a entity type classification of the company into ngo, corporation, shell company etc. Provide only final json output of risk score,confidence score, entity type and a list of supporting evidence from the json's where you got the scores from. Do not give me analysis of the seperate jsons, do not show the calculation. Supporting evidence should be a list of strings like Panama Papers, OFAC Sanctions. If you used corrobating, conformity and headquarters, th evidence is LEI sources. If any othe sanction or simialr values had returned false, don't add that in the evidence.Make the json as simple as possible like how an API response would be. All scores are between 0 and 1. All 5 keys including summary cannot be skipped and should be present. Summary cannot be empty. Supporting evidence must always be a list. The keys have to be risk_score, confidence_score, entity_type, summary and supporting_evidence. Don't change that. Json1 json 2 are as follows."
prompt_people = f"Assume you are finance risk officer. You will be given a json object about a person which will have information on if they were sanction, debarred, person of interest etc. Each will have score, everything except sentiment analysis will have high penalistion. Your output should be risk score, confidence score average and a small summary of how you got there. Json 2 will have true/false values on sanctions ofac and sanction others, presence in panama papers, in warrants, and in debarred lists. Any of these being true must be penalised much harshly than other. There will also be a sentiment analysis score, which if negative should be used to penalise but not extremely. This should have same output as previous json. At the end, final output should be final risk score average, final confidence average, a summary of how you got there under key 'summary' and a entity type classification of the company into pep, sanctioned, watchlisted. If none of these, just say person entity. Provide only final json output of risk score,confidence score, entity type and a list of supporting evidence from the json's where you got the scores from. Do not give me analysis of the seperate jsons, do not show the calculation. Supporting evidence should be a list of strings like Panama Papers, OFAC Sanctions for PEP, Sanctions etc. If any othe sanction or simialr values had returned false, don't add that in the evidence.Make the json as simple as possible like how an API response would be.All scores are between 0 and 1, and need to be able to be parsed as numbers.  The keys have to be risk_score, confidence_score, entity_type, summary and supporting_evidence. Don't change that. Json1 is as follows"
genai.configure(api_key="")

model = genai.GenerativeModel("gemini-2.0-pro-exp")

nlp = spacy.load("./fine_tuned_spacy_model")


text = "On March 15th, 2024, a large international wire transfer was initiated from HSBC Holdings in London to BlackRock Inc. in New York. The transaction, valued at $450 million, was flagged due to references to Elon Musk and Christine Lagarde in accompanying documents."

def get_info(text):
    r = process_entities(get_entities(text))
    df = r[r['label'] != 'LOC']
    result = {
    "entity": df["text"].tolist(),
    "label": df["label"].tolist(),
    "risk_score": df["risk_score"].tolist(),
    "confidence_score": df["confidence_score"].tolist(),
    "entity_type": df["entity_type"].tolist(),
    "supporting_evidence": df["supporting_evidence"].tolist(),
    "summary": " ".join(df["summary"].tolist())
    }
    result_df = pd.DataFrame(result)
    result_df = summarize_dict(result_df)
    return result_df

def get_entities(text):
    doc = nlp(text)
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
    return pd.DataFrame(entities)

def process_entities(df):
    transaction_entity_info = df
    for idx, row in df.iterrows():
        name = row["text"]
        label = row["label"]

        if label == "ORG":
            print(f"\n Processing ORG: {name}")
            json1 = get_other_info_company(name).to_json(orient="records", indent=2)
            json2 = get_company_info(name).to_json(orient="records", indent=2)
            response_pd = get_gemini_score_org(json1, json2)
            response_pd['supporting_evidence'] = response_pd['supporting_evidence'].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) else str(x))
            for col in response_pd.columns:
                transaction_entity_info.at[idx, col] = response_pd.iloc[0][col]

        elif label == "PER":
            print(f"\n Processing PER: {name}")
            json1 = get_other_info_person(name).to_json(orient="records", indent=2)
            response_pd = get_gemini_score_person(json1)
            response_pd['supporting_evidence'] = response_pd['supporting_evidence'].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) else str(x))
            for col in response_pd.columns:
                transaction_entity_info.at[idx, col] = response_pd.iloc[0][col]
        else:
            print(f"\n Skipping: {name} (label: {label})")
    return transaction_entity_info

def get_gemini_score_org(json1, json2):
    print("Getting Gemini score for org...")
    response = model.generate_content(prompt_org + json1 + json2)
    print(response.text)
    cleaned = str(response.text).replace("```json", "").replace("```", "").strip()
    data = json.loads(cleaned)
    return pd.DataFrame([data])

def get_gemini_score_person(json1):
    print("Getting Gemini score for person...")
    response = model.generate_content(prompt_people + json1)
    print(response.text)
    cleaned = str(response.text).replace("```json", "").replace("```", "").strip()
    data = json.loads(cleaned)
    return pd.DataFrame([data])

