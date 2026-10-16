# Re-train the ORIGINAL prototype's models exactly as train_models.py does
# (emails.csv was not provided, so the text model uses sms.csv only).
import pandas as pd, joblib, time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

df = pd.read_csv('../data/raw/uci_sms.csv', encoding='latin1')[['v2','v1']].rename(columns={'v2':'texte','v1':'label'})
df['label'] = df['label'].map({'ham':0,'spam':1})
df = df.drop_duplicates('texte').sample(frac=1, random_state=42)
Xtr, Xte, ytr, yte = train_test_split(df.texte, df.label, test_size=0.2, random_state=42, stratify=df.label)
vec = TfidfVectorizer(max_features=100000, sublinear_tf=True); m = MultinomialNB(alpha=0.1)
m.fit(vec.fit_transform(Xtr), ytr)
print("TEXT (their split):"); print(classification_report(yte, m.predict(vec.transform(Xte)), digits=4))
joblib.dump(m,'models/text_model.joblib'); joblib.dump(vec,'models/text_vectorizer.joblib')

u = pd.read_csv('../data/raw/urls.csv').dropna().drop_duplicates('url')
u['label'] = u['type'].str.strip().str.lower().apply(lambda x: 0 if x in ['benign','normal','safe','0'] else 1)
u = u.sample(frac=1, random_state=42)
s, _ = train_test_split(u, train_size=200000, stratify=u.label, random_state=42)
Xtr, Xte, ytr, yte = train_test_split(s.url, s.label, test_size=0.2, random_state=42, stratify=s.label)
t=time.time(); vec = TfidfVectorizer(analyzer='char', ngram_range=(2,5), max_features=100000)
Xv = vec.fit_transform(Xtr)
m = LogisticRegression(max_iter=500, random_state=42).fit(Xv, ytr)
print("URL (their split):", round(time.time()-t,1),"s"); print(classification_report(yte, m.predict(vec.transform(Xte)), digits=4))
joblib.dump(m,'models/url_model.joblib'); joblib.dump(vec,'models/url_vectorizer.joblib')
