import requests
import pandas as pd
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
import re

def search_sec_edgar_company(name):
    name = name.replace("'", "")
    """ Fetch SEC EDGAR data for a given company name """
    base_url = "https://www.sec.gov/cgi-bin/browse-edgar"
    params = {"company": name, "count": 100, "action": "getcompany"}
    headers = {"User-Agent": "CompanyLookup/1.0 (contact@email.com)"}

    response = requests.get(base_url, params=params, headers=headers)
    if response.status_code == 200:
        return response.text  
    return None

CORROBORATION_SCORES = {
    "FULLY_CORROBORATED": 0,
    "PARTIALLY_CORROBORATED": 1,
    "ENTITY_SUPPLIED_ONLY": 2
}

CONFORMITY_SCORES = {
    "CONFORMING": 0,
    "NON_CONFORMING": 2,
    "NOT_APPLICABLE": 1
}

sic_sector_map = {
    1: "Agricultural Production - Crops",
    2: "Agricultural Production - Livestock",
    7: "Agricultural Services",
    8: "Forestry",
    9: "Fishing, Hunting, and Trapping",
    10: "Metal Mining",
    12: "Coal Mining",
    13: "Oil and Gas Extraction",
    14: "Mining and Quarrying of Nonmetallic Minerals",
    15: "General Building Contractors",
    16: "Heavy Construction Contractors",
    17: "Special Trade Contractors",
    20: "Food and Kindred Products",
    21: "Tobacco Products",
    22: "Textile Mill Products",
    23: "Apparel and Other Textile Products",
    24: "Lumber and Wood Products",
    25: "Furniture and Fixtures",
    26: "Paper and Allied Products",
    27: "Printing and Publishing",
    28: "Chemicals and Allied Products",
    29: "Petroleum Refining",
    30: "Rubber and Miscellaneous Plastics",
    31: "Leather and Leather Products",
    32: "Stone, Clay, and Glass Products",
    33: "Primary Metal Industries",
    34: "Fabricated Metal Products",
    35: "Industrial Machinery and Equipment",
    36: "Electronic and Electrical Equipment",
    37: "Transportation Equipment",
    38: "Measuring Instruments & Optical Goods",
    39: "Miscellaneous Manufacturing Industries",
    40: "Railroad Transportation",
    41: "Local and Interurban Passenger Transit",
    42: "Trucking and Warehousing",
    43: "U.S. Postal Service",
    44: "Water Transportation",
    45: "Air Transportation",
    46: "Pipelines, Except Natural Gas",
    47: "Transportation Services",
    48: "Communications",
    49: "Electric, Gas, and Sanitary Services",
    50: "Wholesale Trade - Durable Goods",
    51: "Wholesale Trade - Nondurable Goods",
    52: "Building Materials & Garden Supplies",
    53: "General Merchandise Stores",
    54: "Food Stores",
    55: "Automotive Dealers and Service Stations",
    56: "Apparel and Accessory Stores",
    57: "Furniture and Home Furnishings Stores",
    58: "Eating and Drinking Places",
    59: "Miscellaneous Retail",
    60: "Depository Institutions (Banks, Credit Unions)",
    61: "Non-Depository Credit Institutions",
    62: "Security & Commodity Brokers, Dealers",
    63: "Insurance Carriers",
    64: "Insurance Agents, Brokers, and Service",
    65: "Real Estate",
    67: "Holding and Other Investment Offices",
    70: "Hotels and Other Lodging Places",
    72: "Personal Services",
    73: "Business Services",
    75: "Automotive Repair, Services, and Parking",
    76: "Miscellaneous Repair Services",
    78: "Motion Pictures",
    79: "Amusement and Recreation Services",
    80: "Health Services",
    81: "Legal Services",
    82: "Educational Services",
    83: "Social Services",
    84: "Museums, Botanical Gardens, and Zoos",
    86: "Membership Organizations",
    87: "Engineering & Management Services",
    88: "Private Households",
    89: "Services, Not Elsewhere Classified",
    91: "Executive, Legislative, and General Government",
    92: "Justice, Public Order, and Safety",
    93: "Finance, Taxation, and Monetary Policy",
    94: "Administration of Human Resources",
    95: "Environmental Quality and Housing Programs",
    96: "Administration of Economic Programs",
    97: "National Security and International Affairs"
}


def get_lei_info(company):
    url1 = f"https://api.gleif.org/api/v1/lei-records?filter[owns]={company}&page[number]=1&page[size]=50"
    headers = {'Accept': 'application/vnd.api+json'}

    response1 = requests.get(url1, headers=headers)
    ob = response1.json()  

    if not ob.get('data'):  
        return pd.DataFrame(columns=[
            "company_name", "headquarters_country", "conformity_flag", "conformity_score",
            "corroboration_level", "corroboration_score", "ocid", "cik",
            "parent_company_name", "parent_headquarters", "parent_conformity_flag", "parent_conformity_score",
            "parent_corroboration_level", "parent_corroboration_score", "parent_ocid", "parent_cik"
        ])

    results = []

    for item in ob['data']:
        try:
            company_name = item['attributes']['entity']['legalName']['name']
            headquarters_country = item['attributes']['entity']['headquartersAddress']['country']
            conformity_flag = item['attributes']['conformityFlag']
            ocid = item['attributes'].get('ocid', None)
            corroboration_level = item['attributes']['registration']['corroborationLevel']

            conformity_score = CONFORMITY_SCORES.get(conformity_flag, -1)
            corroboration_score = CORROBORATION_SCORES.get(corroboration_level, -1)

            parent_company_name, parent_headquarters = company_name, headquarters_country
            parent_conformity_flag, parent_corroboration_level, parent_ocid = conformity_flag, corroboration_level, ocid
            parent_conformity_score, parent_corroboration_score = conformity_score, corroboration_score

            parent_data = item.get('relationships', {}).get('ultimate-parent', {}).get('links', {})

            if "reporting-exception" in parent_data:
                pass  
            elif "lei-record" in parent_data:
                parent_url = parent_data["lei-record"]
                parent_response = requests.get(parent_url, headers=headers)
                parent_ob = parent_response.json()

                if parent_ob.get('data'):
                    parent_company_name = parent_ob['data']['attributes']['entity']['legalName']['name']
                    parent_headquarters = parent_ob['data']['attributes']['entity']['headquartersAddress']['country']
                    parent_conformity_flag = parent_ob['data']['attributes']['conformityFlag']
                    parent_ocid = parent_ob['data']['attributes'].get('ocid', None)
                    parent_corroboration_level = parent_ob['data']['attributes']['registration']['corroborationLevel']

                    parent_conformity_score = CONFORMITY_SCORES.get(parent_conformity_flag, -1)
                    parent_corroboration_score = CORROBORATION_SCORES.get(parent_corroboration_level, -1)


            results.append({
                "company_name": company_name,
                "headquarters_country": headquarters_country,
                "conformity_flag": conformity_flag,
                "conformity_score": conformity_score,
                "corroboration_level": corroboration_level,
                "corroboration_score": corroboration_score,
                "ocid": ocid,
                "parent_company_name": parent_company_name,
                "parent_headquarters": parent_headquarters,
                "parent_conformity_flag": parent_conformity_flag,
                "parent_conformity_score": parent_conformity_score,
                "parent_corroboration_level": parent_corroboration_level,
                "parent_corroboration_score": parent_corroboration_score,
                "parent_ocid": parent_ocid,
            })

        except (KeyError, TypeError):
            continue  
    final_result = pd.DataFrame(results)
    return final_result

def extract_companies_to_dataframe(html_content):
    """ Parses SEC HTML response and converts company data into a Pandas DataFrame """
    soup = BeautifulSoup(html_content, "html.parser")
    company_table = soup.find("table", class_="tableFile2") 

    data = []
    if company_table:
        rows = company_table.find_all("tr")[1:]  
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                cik = cols[0].text.strip()
                name = cols[1].text.strip()
                match = re.search(r"^(.*?)\s*SIC:\s*(\d+)\s*-\s*(.+)", name)

                if match:
                    name = match.group(1).strip() 
                    sic_code = match.group(2)  
                    industry = match.group(3).strip()  
                else:
                    sic_code = None
                    industry = None

                if re.search(r"\b(19|20)\d{2}\b", name):
                    continue  

                data.append({"company_name": name, "cik": cik, "sic_code": sic_code, "industry": industry, "fetch_from": "SEC-EDGAR"})
    return pd.DataFrame(data)

def search_sec_company(partial_name):
    partial_name = partial_name.replace("'", "")
    url = f"https://efts.sec.gov/LATEST/search-index?entityName={partial_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    companies_list = []
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if "hits" in data:
            results = data["hits"]
            results = results['hits']
            all_names = list({
                name.strip().replace("  ", " ")
                for item in results
                for name in item["_source"].get("display_names", [])
            })
            pattern = re.compile(r"(.+?) \(CIK (\d+)\)")

            result = [
                {"company_name": match.group(1), "cik": match.group(2), "sic_code": None, "industry": None, "fetch_from": "SEC_EFT"}
                for entry in all_names if (match := pattern.match(entry))
            ]
            frame = pd.DataFrame(result)
            return frame
        else:
            print("No results found.")
    else:
        print(f"Error: {response.status_code}")

def fuzzy_match_all_companies_sec(user_input, df):
    """ Returns a DataFrame of all companies with SIC codes, sector labels, and match scores """

    user_input_lower = user_input.lower()
    df["company_name_lower"] = df["company_name"].str.lower()

    df["match_score"] = df["company_name_lower"].apply(
        lambda x: 0.4 * fuzz.QRatio(user_input_lower, x) +
                  0.3 * fuzz.token_sort_ratio(user_input_lower, x) +
                  0.3 * fuzz.partial_ratio(user_input_lower, x)
    )

    df["sic_code"] = pd.to_numeric(df["sic_code"], errors="coerce")

    df["sic_code_2digit"] = df["sic_code"].dropna().astype(int).astype(str).str[:2]
    df["sic_code_2digit"] = pd.to_numeric(df["sic_code_2digit"], errors="coerce")

    df["Sector"] = df["sic_code_2digit"].map(sic_sector_map)

    df = df.sort_values(by=["sic_code_2digit" , "match_score"], ascending=False)

    df_with_sic = df[df["sic_code"].notna()]
    df_without_sic = df[df["sic_code"].isna()]
    df_sec_eft = df[df["fetch_from"] == 'SEC_EFT']
    top_with_sic = df_with_sic.nlargest(2, "match_score")
    top_without_sic = df_without_sic.nlargest(2, "match_score")
    top_in_sec_eft = df_sec_eft.nlargest(2, "match_score")
    final_results = pd.concat([top_with_sic, top_without_sic, top_in_sec_eft])
    final_results['info_count'] = final_results.notna().sum(axis=1)

    final_results = final_results.sort_values(by=['cik', 'info_count'], ascending=[True, False]).drop_duplicates(
        subset='cik', keep='first')

    final_results = final_results.drop(columns=['info_count'])
    return final_results

def get_top_values_between_sec_and_lei(p, k):
    """Fuzzy match the top row of p with k, and vice versa, adding match scores and final averages."""
    p['final_average'] = (p['average'])
    k['final_average'] = (k['match_score'])

    return p, k  #

def add_match_and_parent_count(df, user_input):
    user_input_lower = user_input.lower()

    df["match_score"] = df["company_name"].apply(
        lambda x: 0.4 * fuzz.QRatio(user_input_lower, x.lower()) +
                  0.3 * fuzz.token_sort_ratio(user_input_lower, x.lower()) +
                  0.3 * fuzz.partial_ratio(user_input_lower, x.lower())
    )

    parent_counts = df["parent_company_name"].value_counts()
    df["parent_count"] = df["parent_company_name"].map(parent_counts)


    df["parent_percentage"] = (df["parent_count"] / len(df)) * 100
    df['equality_score'] = 0.00  # Default
    df.loc[df['company_name'] == df['parent_company_name'], 'equality_score'] = 100.00
    df['average'] = (0.25 * df['parent_percentage'] + 0.5 * df['match_score'] + 0.25 * df['equality_score'])
    df.loc[df['match_score'] > 70, 'average'] = (0.7 * df['match_score'] + 0.3 * df['parent_percentage'])

    df = df.sort_values(by=['average'], ascending = False )
    return df

def normalize_name(name):
    """Convert to lowercase and remove spaces for robust matching."""
    name = name.lower()
    name = re.sub(r'\b(corp|corporation|inc|ltd|llc|co)\b', '', name)
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)  
    name = name.replace('.', " ")
    name = name.replace (",", " ")
    name = re.sub(r'\s+', ' ', name).strip() 
    return name

def merge_ranked_dataframes(p, k):
    p["normalized_name"] = p["company_name"].apply(normalize_name)
    k["normalized_name"] = k["company_name"].apply(normalize_name)

    p = p.sort_values(by="match_score", ascending=False, ignore_index=True) if "match_score" in p else p
    k = k.sort_values(by="match_score", ascending=False, ignore_index=True) if "match_score" in k else k

    final_df = pd.DataFrame()  

    if not p.empty and not k.empty and p.loc[0, "normalized_name"] == k.loc[0, "normalized_name"]:
        final_df = pd.merge(p.loc[[0]], k.loc[[0]], on="company_name", how="outer", suffixes=("_p", "_k"))
        final_df["confidence_score"] = 1.0
    else:
        common_names = set(p["normalized_name"]).intersection(set(k["normalized_name"]))
        for name in common_names:
            p_match = p[p["normalized_name"] == name]
            k_match = k[k["normalized_name"] == name]
            if not p_match.empty and not k_match.empty:
                if (60 <= p_match.iloc[0]["match_score"] <= 100) and (60 <= k_match.iloc[0]["match_score"] <= 100):
                    final_df = pd.merge(p_match, k_match, on="company_name", how="outer", suffixes=("_p", "_k"))
                    final_df["confidence_score"] = 0.8
                    break


    if final_df.empty:
        top_p = p.iloc[0] if not p.empty else None
        top_k = k.iloc[0] if not k.empty else None

        if top_p is not None and top_k is not None:
            final_row = top_p if top_p["match_score"] >= top_k["match_score"] else top_k
        elif top_p is not None:
            final_row = top_p
        else:
            final_row = top_k

        final_df = pd.DataFrame([final_row])
        final_df["confidence_score"] = final_df["match_score"].apply(lambda x: 1.0 if x > 80 else (0.8 if 60 <= x <= 80 else 0.6))

    all_columns = ["company_name"] + [col for col in (list(p.columns) + list(k.columns)) if col != "company_name"]
    if {"normalized_name_p", "normalized_name_k"}.issubset(final_df.columns):
        final_df["normalized_name"] = final_df[["normalized_name_p", "normalized_name_k"]].bfill(axis=1).iloc[:, 0]
        final_df.drop(columns=["normalized_name_p", "normalized_name_k"], errors="ignore", inplace=True)
    final_df = final_df.reindex(columns=all_columns + ["confidence_score"], fill_value=None)
    cols_to_drop = [col for col in final_df.columns if
                    col.startswith(('match_score', 'parent_count', 'parent_percentage',
                                    'equality_score', 'average', 'final_average',
                                    'company_name_lower'))]
    final_df.drop(columns=cols_to_drop, errors="ignore", inplace=True)
    final_df['normalized_name'] = final_df["normalized_name"] = final_df["normalized_name"].astype(str)
    final_df = final_df.groupby(axis=1, level=0).first()

    if len(final_df) == 1:
        merged_row = final_df.iloc[0]

    elif len(final_df) == 2:
        merged_row = final_df.iloc[0].copy()

        for col in final_df.columns:
            val1, val2 = final_df.iloc[0][col], final_df.iloc[1][col]

            if str(val1) == str(val2):  
                merged_row[col] = val1
            elif pd.isna(val1):  
                merged_row[col] = val2
            elif pd.isna(val2): 
                merged_row[col] = val1
            elif isinstance(val1, str) and isinstance(val2, str):
                merged_row[col] = val1 if len(val1) >= len(val2) else val2

        final_df = pd.DataFrame([merged_row])

    return final_df

def get_company_info(company):
    print(f"Fetching SEC-EDGAR and LEI info for {company}")
    final_company = pd.DataFrame()
    sec_df = pd.DataFrame()
    html_content = search_sec_edgar_company(company)
    df = extract_companies_to_dataframe(html_content)
    df = pd.concat([df, search_sec_company(company)])
    info = fuzzy_match_all_companies_sec(company, df)

    if isinstance(info, pd.DataFrame):
        k = pd.concat([sec_df, info], ignore_index=True)

        p = get_lei_info(company)
        p = add_match_and_parent_count(p, company)

        if len(k) == 0:
            p_top = p.loc[p['average'].idxmax()].copy() 

            if p_top['match_score'] > 80:
                p_top.loc['confidence_on_entity'] = 0.8
            elif 60 < p_top['match_score'] <= 80:
                p_top.loc['confidence_on_entity'] = 0.6
            else:
                print("There's no match here")
                return final_company

            all_columns = ["company_name"] + [col for col in (list(p.columns) + list(k.columns)) if
                                              col != "company_name"]
            final_company = pd.DataFrame([p_top]).reindex(columns=all_columns + ["confidence_on_entity"],
                                                          fill_value=None)
            cols_to_drop = [col for col in final_company.columns if
                            col.startswith(('match_score', 'parent_count', 'parent_percentage',
                                            'equality_score', 'average', 'final_average',
                                            'company_name_lower'))]
            final_company.drop(columns=cols_to_drop, errors="ignore", inplace=True)

            return final_company

        elif len(p) == 0:
            k_top = k.loc[k['match_score'].idxmax()].copy()

            if k_top['match_score'] > 80:
                k_top.loc['confidence_on_entity'] = 0.8
            elif 60 < k_top['match_score'] <= 80:
                k_top.loc['confidence_on_entity'] = 0.6
            else:
                print("There's no match here")

            all_columns = ["company_name"] + [col for col in (list(p.columns) + list(k.columns)) if
                                              col != "company_name"]
            final_company = pd.DataFrame([k_top]).reindex(columns=all_columns + ["confidence_on_entity"],
                                                          fill_value=None)
            cols_to_drop = [col for col in final_company.columns if
                            col.startswith(('match_score', 'parent_count', 'parent_percentage',
                                            'equality_score', 'average', 'final_average',
                                            'company_name_lower'))]
            final_company.drop(columns=cols_to_drop, errors="ignore", inplace=True)
            return final_company

        else:
            p, k = get_top_values_between_sec_and_lei(p, k)

        final_company = merge_ranked_dataframes(p,k)
        return final_company
