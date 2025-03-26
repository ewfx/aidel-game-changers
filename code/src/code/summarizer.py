from transformers import pipeline

summarizer = pipeline("summarization")

def summarize_dict(input_dict):
  summary = input_dict.get('summary')
  summaries = summarizer(summary, max_length=50, min_length=30, do_sample=False)
  input_dict['summary'] = summaries[0]['summary_text']

