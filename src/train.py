"""Step 1: train โมเดลด้วยคำถามชุดง่าย แล้ว save เป็น model/model.pkl

รัน:  python src/train.py
"""
from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from features import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET, CLASS_ORDER, bucketize

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data" / "sleep_doomscrolling_habits.csv")
X = bucketize(df)          # ← แปลงเป็นตัวเลือกแบบเดียวกับหน้าเว็บ
y = df[TARGET]

preprocess = ColumnTransformer([
    ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                      ("scale", StandardScaler())]), NUMERIC_FEATURES),
    ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                      ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL_FEATURES),
])

candidates = {
    "baseline (เดาคลาสที่เจอบ่อยสุด)": DummyClassifier(strategy="most_frequent"),
    "logistic_regression": LogisticRegression(max_iter=2000),
    "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=42),
    "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05,
                                                             max_depth=3, random_state=42),
}

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("5-fold CV บน training set (metric = macro F1)")
scores = {}
for name, clf in candidates.items():
    s = cross_val_score(Pipeline([("prep", preprocess), ("clf", clf)]), X_train, y_train,
                        cv=cv, scoring="f1_macro")
    scores[name] = s.mean()
    print(f"  {name:32s} {s.mean():.3f} ± {s.std():.3f}")

best_name = max((n for n in scores if not n.startswith("baseline")), key=scores.get)
print(f"\nเลือก: {best_name}")
best = Pipeline([("prep", preprocess), ("clf", candidates[best_name])]).fit(X_train, y_train)
pred = best.predict(X_test)
print("\nผลบน test set")
print(classification_report(y_test, pred, labels=CLASS_ORDER, digits=3))
print("Confusion matrix (แถว=จริง, คอลัมน์=ทำนาย)", CLASS_ORDER)
print(confusion_matrix(y_test, pred, labels=CLASS_ORDER))

final = Pipeline([("prep", preprocess), ("clf", candidates[best_name])]).fit(X, y)
(ROOT / "model").mkdir(exist_ok=True)
joblib.dump(final, ROOT / "model" / "model.pkl")

good = X[y == "Good"]
meta = {
    "model": best_name,
    "cv_f1_macro": round(scores[best_name], 3),
    "good_sleeper_median": good[NUMERIC_FEATURES].median().to_dict(),
}
(ROOT / "model" / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
print("\nบันทึกแล้ว: model/model.pkl และ model/meta.json")
