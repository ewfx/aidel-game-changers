# 🚀 Project Name
   AI-Driven Entity Intelligence & Risk Analysis
## 📌 Table of Contents
- [Introduction](#introduction)
- [Demo](#demo)
- [How to Run](#how-to-run)
- [Tech Stack](#tech-stack)
- [Team](#team)

---

## 🎯 Introduction
We have created an entity recognition and risk analysis project. The entity recognition is performed by a fine-tuned version of a SpaCy model that we trained on cleaned up and modified version of FiNER-ORD dataset from Georgia Tech.
Comparing F1, recall and precision proved this model to be better than base model by huge margin.


To validate the matches and enrich the data, we use two sources of **SEC-EDGAR** - an API and web scraping the result of search box, from which we gathered CIK number, SIC number - which proved regular filings reducing risk.

We also used **GLEIF** as a secondary source to validate the match, from where we used industry standard information **corrobaration flags**, **policy conforming flags** and **headquarters** of company. We also pulled in **information of the parent company** to validate if it was being owned by companies in tax-havens or shell companies.

Other data sources for organisations and people include :
- **OFAC sanctions**
- **Debarred Lists**
- **Regulatory Watch Lists**
- **SDN lists**
- **Warranted Lists**
- **PEP Lists**

All of these were consolidated lists from multiple datasets available across OFAC sources.

We also generated a **sentiment analysis score** for the entity using Hugging Face model called **FinBERT** by ProsusAI. As data for that, we web scraped 3 pages of headlines from **YahooNews!** directly to better understand market trends.

Along the way, we also calculated **confidence score** based on **fuzzy matching** using **RapidFuzz** the entity name to each source ans generating averages based on **match_score** and **primary_company**.

Finally, the two generated enriched data sources were passed with targeted prompts to Google's **Gemini AI 1.5 Pro**, to generate a risk score, final confidence score, classification and summary.

Since, summary was generated per entity, it was too elaborate, so to make it succinct, we used a Hugging Face transfer model for summarizer which defaulted to **Distilled-BERT**. 

While we were unable to test the final functionality due to a dependency issue of Python 3 with SpaCy locally, we created an API endpoint using **FastAPI** that would in theory, take JSON/Text input and output the processed info.


## 🎥 Demo
📹 [Video Demo](#) - https://drive.google.com/file/d/1BVMuKPtJyTnayt32MUeB33IY83O_6mr2/view?usp=share_link 

We have also added an explanation document in artifacts/arch that better explain the project and our solution to it. Attached along side is a Colab version of our output for references.
## 🏃 How to Run
1. Clone the repository  
   ```sh
   git clone https://github.com/your-repo.git
   ```
2. Install dependencies  
   ```sh
   pip install -r requirements.txt 
   ```
3. Run the project  
   ```sh
   uvicorn main:app --reload
   ```

## 🏗️ Tech Stack
- 🔹 Python

## 👥 Team
- Surya S - https://github.com/suryasridhar | https://www.linkedin.com/in/surya-sridhar-06938135
- **Teammate 2** - [GitHub](#) | [LinkedIn](#)
