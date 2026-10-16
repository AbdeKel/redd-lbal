"""
Script d'entraînement pour le Datathon :
1. Modèle d'analyse de texte (SMS + Emails) avec TfidfVectorizer et MultinomialNB
2. Modèle d'analyse d'URLs avec TfidfVectorizer (char n-grams 2-5) et LogisticRegression
"""

import os
import sys
import time
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_file(filename):
    """Recherche le fichier dans le répertoire courant ou avec extension .csv.csv si nécessaire."""
    candidates = [
        os.path.join(BASE_DIR, filename),
        os.path.join(BASE_DIR, f"{filename}.csv"),
        os.path.join(BASE_DIR, "..", filename),
        os.path.join(BASE_DIR, "..", f"{filename}.csv")
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Impossible de trouver {filename}")


def train_text_model():
    print("\n" + "=" * 60)
    print(" 1. CRÉATION DU MODÈLE D'ANALYSE DE TEXTE (SMS & EMAILS)")
    print("=" * 60)

    # 1. Chargement de sms.csv
    sms_path = find_file("sms.csv")
    print(f"[-] Chargement de sms.csv depuis : {sms_path}")
    try:
        df_sms = pd.read_csv(sms_path, encoding='utf-8')
    except UnicodeDecodeError:
        df_sms = pd.read_csv(sms_path, encoding='latin1')

    # Harmonisation des colonnes de sms.csv -> texte et label
    # sms.csv contient généralement v1 (label) et v2 (texte)
    if 'v1' in df_sms.columns and 'v2' in df_sms.columns:
        df_sms = df_sms[['v2', 'v1']].rename(columns={'v2': 'texte', 'v1': 'label'})
    elif 'text' in df_sms.columns:
        label_col = 'label' if 'label' in df_sms.columns else df_sms.columns[1]
        df_sms = df_sms[['text', label_col]].rename(columns={'text': 'texte', label_col: 'label'})
    else:
        df_sms = df_sms.iloc[:, :2]
        df_sms.columns = ['label', 'texte'] if 'ham' in str(df_sms.iloc[0, 0]).lower() or 'spam' in str(df_sms.iloc[0, 0]).lower() else ['texte', 'label']
        df_sms = df_sms[['texte', 'label']]

    # Encodage binaire pour SMS : 0 = normal (ham), 1 = arnaque/spam
    df_sms['label'] = df_sms['label'].astype(str).str.strip().str.lower().map({
        'ham': 0, 'normal': 0, '0': 0,
        'spam': 1, 'smishing': 1, 'phishing': 1, '1': 1
    }).fillna(0).astype(int)

    print(f"    -> SMS chargés : {len(df_sms)} lignes (Ham: {(df_sms['label'] == 0).sum()}, Spam: {(df_sms['label'] == 1).sum()})")

    # 2. Chargement de emails.csv
    emails_path = find_file("emails.csv")
    print(f"[-] Chargement de emails.csv depuis : {emails_path}")
    try:
        df_emails = pd.read_csv(emails_path, encoding='utf-8')
    except UnicodeDecodeError:
        df_emails = pd.read_csv(emails_path, encoding='latin1')

    # Harmonisation des colonnes de emails.csv -> texte et label
    if 'text_combined' in df_emails.columns:
        df_emails = df_emails.rename(columns={'text_combined': 'texte'})
    elif 'text' in df_emails.columns:
        df_emails = df_emails.rename(columns={'text': 'texte'})
    
    df_emails = df_emails[['texte', 'label']]
    df_emails['label'] = pd.to_numeric(df_emails['label'], errors='coerce').fillna(0).astype(int)

    print(f"    -> Emails chargés : {len(df_emails)} lignes (Normal: {(df_emails['label'] == 0).sum()}, Phishing/Spam: {(df_emails['label'] == 1).sum()})")

    # 3. Fusion des deux datasets
    print("[-] Fusion des datasets...")
    df_text = pd.concat([df_sms[['texte', 'label']], df_emails[['texte', 'label']]], ignore_index=True)
    initial_count = len(df_text)

    # Suppression des valeurs nulles et des doublons
    df_text = df_text.dropna(subset=['texte', 'label'])
    df_text = df_text.drop_duplicates(subset=['texte'])

    # Mélange des données
    df_text = df_text.sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"    -> Lignes initiales : {initial_count} | Après nettoyage et déduplication : {len(df_text)}")
    print(f"    -> Distribution finale : 0 (Normal) = {(df_text['label'] == 0).sum()} | 1 (Arnaque/Spam/Phishing) = {(df_text['label'] == 1).sum()}")

    # Découpage Entraînement / Test (80% / 20%)
    X_train, X_test, y_train, y_test = train_test_split(
        df_text['texte'].astype(str),
        df_text['label'],
        test_size=0.2,
        random_state=42,
        stratify=df_text['label']
    )

    # 4. TfidfVectorizer classique
    print("[-] Vectorisation TF-IDF du texte...")
    t0 = time.time()
    vectorizer = TfidfVectorizer(max_features=100000, sublinear_tf=True)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    print(f"    -> TF-IDF terminé en {time.time() - t0:.2f}s (Vocabulaire : {len(vectorizer.vocabulary_):,} termes)")

    # 5. Entraînement MultinomialNB
    print("[-] Entraînement du classifieur MultinomialNB...")
    t1 = time.time()
    model = MultinomialNB(alpha=0.1)
    model.fit(X_train_vec, y_train)
    print(f"    -> Modèle entraîné en {time.time() - t1:.2f}s")

    # 6. Évaluation
    y_pred = model.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    print("\n" + "-" * 40)
    print("   MÉTRIQUES DU MODÈLE DE TEXTE")
    print("-" * 40)
    print(f"Exactitude (Accuracy)  : {acc * 100:.2f} %")
    print(f"Précision (Precision) : {prec * 100:.2f} %")
    print(f"Rappel (Recall)       : {rec * 100:.2f} %")
    print(f"F1-Score              : {f1 * 100:.2f} %")
    print("\nMatrice de confusion :")
    print(f"  [VN={cm[0,0]:<5}  FP={cm[0,1]:<5}]")
    print(f"  [FN={cm[1,0]:<5}  VP={cm[1,1]:<5}]")
    print("\nRapport de classification détaillé :")
    print(classification_report(y_test, y_pred, target_names=['Normal (0)', 'Arnaque/Spam (1)'], digits=4))

    # 7. Sauvegarde des modèles
    model_path = os.path.join(BASE_DIR, "text_model.joblib")
    vec_path = os.path.join(BASE_DIR, "text_vectorizer.joblib")
    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vec_path)
    print(f"[OK] Modèle sauvegardé sous : {model_path}")
    print(f"[OK] Vectoriseur sauvegardé sous : {vec_path}")

    return {
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1': f1
    }


def train_url_model():
    print("\n" + "=" * 60)
    print(" 2. CRÉATION DU MODÈLE D'ANALYSE DE LIENS (URLS)")
    print("=" * 60)

    # 1. Chargement de urls.csv
    urls_path = find_file("urls.csv")
    print(f"[-] Chargement de urls.csv depuis : {urls_path}")
    try:
        df_urls = pd.read_csv(urls_path, encoding='utf-8')
    except UnicodeDecodeError:
        df_urls = pd.read_csv(urls_path, encoding='latin1')

    # Harmonisation des colonnes -> url et label
    if 'type' in df_urls.columns and 'url' in df_urls.columns:
        df_urls = df_urls[['url', 'type']].rename(columns={'type': 'raw_label'})
    elif len(df_urls.columns) >= 2:
        df_urls = df_urls.iloc[:, :2]
        df_urls.columns = ['url', 'raw_label']
    else:
        raise ValueError("Structure inattendue pour urls.csv")

    # Nettoyage
    df_urls = df_urls.dropna(subset=['url', 'raw_label'])
    df_urls = df_urls.drop_duplicates(subset=['url'])

    # Encodage binaire : 0 = normal (benign), 1 = phishing / malveillant
    df_urls['label'] = df_urls['raw_label'].astype(str).str.strip().str.lower().apply(
        lambda x: 0 if x in ['benign', 'normal', 'safe', '0'] else 1
    )
    df_urls = df_urls[['url', 'label']]

    # Mélange des données
    df_urls = df_urls.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"    -> URLs après nettoyage et déduplication : {len(df_urls):,} lignes")
    print(f"    -> Distribution : 0 (Normal) = {(df_urls['label'] == 0).sum():,} | 1 (Phishing/Malveillant) = {(df_urls['label'] == 1).sum():,}")

    # Pour un entraînement performant et rapide, nous prenons un échantillon représentatif de 200 000 URLs
    # si le dataset est très grand (650k+ URLs avec n-grams de 2 à 5)
    sample_size = min(200000, len(df_urls))
    if len(df_urls) > sample_size:
        print(f"[-] Utilisation d'un échantillon stratifié de {sample_size:,} URLs pour un entraînement optimal...")
        df_train_sample, _ = train_test_split(
            df_urls,
            train_size=sample_size,
            stratify=df_urls['label'],
            random_state=42
        )
        df_train_sample = df_train_sample.reset_index(drop=True)
    else:
        df_train_sample = df_urls

    # Découpage Entraînement / Test (80% / 20%)
    X_train, X_test, y_train, y_test = train_test_split(
        df_train_sample['url'].astype(str),
        df_train_sample['label'],
        test_size=0.2,
        random_state=42,
        stratify=df_train_sample['label']
    )

    # 2. TfidfVectorizer paramétré avec analyzer='char' et ngram_range=(2, 5)
    print("[-] Vectorisation TF-IDF (analyzer='char', ngram_range=(2, 5))...")
    t0 = time.time()
    vectorizer = TfidfVectorizer(
        analyzer='char',
        ngram_range=(2, 5),
        max_features=100000
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    print(f"    -> TF-IDF terminé en {time.time() - t0:.2f}s (Features retenues : {X_train_vec.shape[1]:,})")

    # 3. Entraînement du modèle LogisticRegression
    print("[-] Entraînement du modèle LogisticRegression...")
    t1 = time.time()
    model = LogisticRegression(max_iter=500, solver='lbfgs', random_state=42)
    model.fit(X_train_vec, y_train)
    print(f"    -> Modèle entraîné en {time.time() - t1:.2f}s")

    # 4. Évaluation
    y_pred = model.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    print("\n" + "-" * 40)
    print("   MÉTRIQUES DU MODÈLE D'URLS")
    print("-" * 40)
    print(f"Exactitude (Accuracy)  : {acc * 100:.2f} %")
    print(f"Précision (Precision) : {prec * 100:.2f} %")
    print(f"Rappel (Recall)       : {rec * 100:.2f} %")
    print(f"F1-Score              : {f1 * 100:.2f} %")
    print("\nMatrice de confusion :")
    print(f"  [VN={cm[0,0]:<5}  FP={cm[0,1]:<5}]")
    print(f"  [FN={cm[1,0]:<5}  VP={cm[1,1]:<5}]")
    print("\nRapport de classification détaillé :")
    print(classification_report(y_test, y_pred, target_names=['Normal (0)', 'Phishing (1)'], digits=4))

    # 5. Sauvegarde des modèles
    model_path = os.path.join(BASE_DIR, "url_model.joblib")
    vec_path = os.path.join(BASE_DIR, "url_vectorizer.joblib")
    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vec_path)
    print(f"[OK] Modèle sauvegardé sous : {model_path}")
    print(f"[OK] Vectoriseur sauvegardé sous : {vec_path}")

    return {
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1': f1
    }


def main():
    total_start = time.time()
    print("=" * 60)
    print("  DÉMARRAGE DE L'ENTRAÎNEMENT DES MODÈLES IA (DATATHON)")
    print("=" * 60)

    text_metrics = train_text_model()
    url_metrics = train_url_model()

    total_duration = time.time() - total_start
    print("\n" + "=" * 60)
    print("  RÉSUMÉ GLOBAL DES PERFORMANCES")
    print("=" * 60)
    print(f"Temps total d'exécution : {total_duration:.2f} secondes\n")
    print(f"{'Modèle':<20} | {'Précision':<12} | {'Rappel':<12} | {'F1-Score':<12} | {'Exactitude':<12}")
    print("-" * 74)
    print(f"{'Texte (MultinomialNB)':<20} | {text_metrics['precision']*100:>10.2f} % | {text_metrics['recall']*100:>10.2f} % | {text_metrics['f1']*100:>10.2f} % | {text_metrics['accuracy']*100:>10.2f} %")
    print(f"{'URLs (LogisticReg)':<20} | {url_metrics['precision']*100:>10.2f} % | {url_metrics['recall']*100:>10.2f} % | {url_metrics['f1']*100:>10.2f} % | {url_metrics['accuracy']*100:>10.2f} %")
    print("=" * 60)
    print("Tous les modèles et vectoriseurs ont été enregistrés avec succès !")


if __name__ == "__main__":
    main()
