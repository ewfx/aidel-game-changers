import json
import spacy
from spacy.scorer import Scorer
from spacy.training.example import Example

model_path = "../fine_tuned_spacy_model"
nlp = spacy.load(model_path)
baseline_nlp = spacy.load("en_core_web_sm")


test_file = "../data/spacey_test.json"
with open(test_file, "r", encoding="utf-8") as f:
    test_data = json.load(f)

for item in test_data:
    text, annotations = item
    doc = nlp(text)

def evaluate_model(nlp, test_data):
    scorer = Scorer()
    examples = []

    for item in test_data:
        text, annotations = item
        gold_annotations = annotations["entities"]

        doc = nlp(text)

        gold_doc = nlp.make_doc(text)
        ents = []
        for start, end, label in gold_annotations:
            span = gold_doc.char_span(start, end, label=label)
            if span:
                ents.append(span)

        gold_doc.ents = ents

        example = Example(predicted=doc, reference=gold_doc)
        examples.append(example)

    scores = scorer.score(examples)
    return scores

print("\n--- EVALUATING BASELINE MODEL (en_core_web_sm) ---\n")
baseline_scores = evaluate_model(baseline_nlp, test_data)
print(json.dumps(baseline_scores, indent=4))

print("\n--- EVALUATING FINE-TUNED MODEL ---\n")
custom_scores = evaluate_model(nlp, test_data)
print(json.dumps(custom_scores, indent=4))

