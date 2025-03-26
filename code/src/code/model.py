import json
import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans
from spacy.training import Example

nlp = spacy.load("en_core_web_sm")

with open("spacey_train.json", "r", encoding="utf-8") as f:
    data = json.load(f)

if "ner" not in nlp.pipe_names:
    ner = nlp.add_pipe("ner", last=True)
else:
    ner = nlp.get_pipe("ner")

existing_labels = set(ner.labels)

for _, annotations in data:
    for _, _, label in annotations["entities"]:
        if label not in existing_labels:
            ner.add_label(label)

db = DocBin()
examples = []

for text, annotations in data:
    doc = nlp.make_doc(text)
    ents = []

    for start, end, label in annotations["entities"]:
        span = doc.char_span(start, end, label=label, alignment_mode="contract")
        if span is not None:
            ents.append(span)

    doc.ents = filter_spans(ents)
    db.add(doc)

    examples.append(Example.from_dict(doc, {"entities": annotations["entities"]}))

db.to_disk("./train.spacy")
print("✅ Saved spaCy training data to train.spacy")

optimizer = nlp.resume_training()

for epoch in range(50):
    losses = {}
    nlp.update(examples, drop=0.3, losses=losses)
    print(f"Epoch {epoch + 1} | Loss: {losses['ner']}")

nlp.to_disk("./fine_tuned_spacy_model")
print("✅ Fine-tuned model saved successfully")
