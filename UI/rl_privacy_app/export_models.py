"""Train and export the six category models from the project notebooks.

The notebook code is executed as-is (up to the reward-coefficient selection cell), so the exported
classifier, text models, interaction rules and Q-table are the same objects the notebook builds.

usage:  python export_models.py [category ...]        (default: all six)
"""
import contextlib
import io
import json
import os
import re
import sys
import time

import joblib
import matplotlib

matplotlib.use("Agg")

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK_DIR = os.path.dirname(HERE)          # the notebooks and CSVs live one level up
MODEL_DIR = os.path.join(HERE, "models")

CATEGORIES = {
    "education": "Android_Privacy_RL_Education_Reference.ipynb",
    "games": "Android_Privacy_RL_Games.ipynb",
    "lifestyle_health": "Android_Privacy_RL_Lifestyle_Health.ipynb",
    "media_entertainment": "Android_Privacy_RL_Entertainment_Media.ipynb",
    "productivity_tools": "Android_Privacy_RL_Productivity_Tools.ipynb",
    "social_communication": "Android_Privacy_RL_Social_Communication.ipynb",
}
N_EXAMPLES_PER_CLASS = 4


def notebook_code(path):
    """Code cells up to and including the reward-coefficient selection cell."""
    cells = [("".join(c["source"])) for c in json.load(open(path))["cells"] if c["cell_type"] == "code"]
    stop = next(i for i, s in enumerate(cells) if "BEST_ALPHA, BEST_BETA" in s and "selection_df.iloc[0]" in s)
    code = "\n\n".join(cells[: stop + 1])
    # Keep the final text model of every view (the notebook only keeps them in loop variables).
    code = code.replace("text_cv = StratifiedKFold", "TEXT_MODELS = {}\ntext_cv = StratifiedKFold", 1)
    keep = "    vec, lr = fit_text_model(games_text[tr_pos], y_tr_text, other_text, vec_kwargs)\n"
    assert keep in code, "text-model fit line not found"
    code = code.replace(keep, keep + "    TEXT_MODELS[name] = (vec, lr)\n", 1)
    return code


def export(key):
    t0 = time.time()
    os.chdir(NOTEBOOK_DIR)
    ns = {"display": lambda *a, **k: None, "__name__": "__notebook__"}
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        exec(compile(notebook_code(CATEGORIES[key]), CATEGORIES[key], "exec"), ns)

    import numpy as np
    import pandas as pd

    rl = ns["RL_FEATURES"]
    best = (float(ns["BEST_ALPHA"]), float(ns["BEST_BETA"]), float(ns["BEST_GAMMA"]))

    # Test-set metrics of the exported configuration (same computation as the notebook).
    test_res = ns["apply_policy"](ns["BEST_Q"], ns["test_df"], *best)
    w = ns["PRIVACY_SCORE_WEIGHTS"]
    test_score = np.clip(w["individual"] * test_res["IndividualRisk"] + w["classifier"] * test_res["MaliciousProbability"]
                         + w["interaction"] * test_res["InteractionRisk"], 0, 1)
    test_pred = (test_score > float(ns["BEST_THRESHOLD"])).astype(int)
    metrics = {k: float(v) for k, v in ns["classification_metrics"](test_res["TrueLabel"], test_pred).items()}
    metrics["ROC_AUC"] = float(ns["roc_auc_score"](test_res["TrueLabel"], test_score))
    metrics["TestApps"] = int(len(test_res))

    # The most frequent raw column of each permission group (used when only the group is known).
    cat_df, raw_cols = ns["cat_df"], ns["RAW_PERMISSION_COLUMNS_ALL"]
    representative = {}
    for perm, cols in ns["PERMISSION_COLUMN_MAP"].items():
        present = [c for c in cols if c in cat_df.columns]
        if present:
            freq = cat_df[present].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
            representative[perm] = str(freq.idxmax())

    # Example apps from the TEST split, with the notebook's own output for parity tests.
    rng = np.random.RandomState(7)
    examples = []
    test_df = ns["test_df"].reset_index(drop=True)
    for label in (1, 0):
        idx = np.flatnonzero(test_res["TrueLabel"].values == label)
        for i in rng.choice(idx, size=min(N_EXAMPLES_PER_CLASS, len(idx)), replace=False):
            row = cat_df.iloc[int(test_df.loc[i, "uid"])]
            perms = [c for c in raw_cols if pd.to_numeric(row[c], errors="coerce") == 1]
            num = lambda c: float(pd.to_numeric(row[c], errors="coerce")) if pd.notna(pd.to_numeric(row[c], errors="coerce")) else 0.0
            examples.append({
                "app_name": str(row["App"]), "package": str(row["Package"]) if pd.notna(row["Package"]) else "",
                "genre": str(row["Category"]), "description": str(row["Description"]) if pd.notna(row["Description"]) else "",
                "related_apps": str(row["Related apps"]) if pd.notna(row["Related apps"]) else "",
                "rating": num("Rating"), "num_ratings": num("Number of ratings"), "price": num("Price"),
                "permissions": perms, "true_label": int(label),
                "notebook": {"privacy_score": float(test_score.iloc[i]), "malicious": bool(test_pred.iloc[i]),
                             "allowed": test_res.loc[i, "AllowedPermissions"],
                             "classifier_risk": float(test_res.loc[i, "MaliciousProbability"])},
            })

    rules = [{k: (list(v) if isinstance(v, tuple) else v) for k, v in r.items()
              if k not in ("Conditions", "_TrainMask")} for r in ns["INTERACTION_RULES"]]
    for r in rules:
        r.update({k: (float(v) if isinstance(v, (np.floating, float)) else int(v) if isinstance(v, np.integer) else v)
                  for k, v in r.items()})

    bundle = {
        "key": key,
        "category": ns["CATEGORY"],
        "genres": list(ns["CATEGORY_RAW_VALUES"]),
        "rl_features": list(rl),
        "permission_names": list(ns["PERMISSION_NAMES"]),
        "permission_column_map": ns["PERMISSION_COLUMN_MAP"],
        "representative_raw": representative,
        "raw_permission_columns": list(raw_cols),
        "clf_permission_features": list(ns["CLF_PERMISSION_FEATURES"]),
        "metadata_features": list(ns["METADATA_FEATURES"]),
        "genre_features": list(ns["GENRE_FEATURES"]),
        "text_feature_order": list(ns["TEXT_RISK_FEATURES"]),
        "weight_map": {k: float(v) for k, v in ns["weight_map"].items()},
        "utility_map": {k: float(v) for k, v in ns["utility_map"].items()},
        "risk_bin_edges": [float(x) for x in ns["RISK_BIN_EDGES"]],
        "rules": rules,
        "alpha": best[0], "beta": best[1], "gamma": best[2],
        "denial_cost": 0.5,
        "threshold": float(ns["BEST_THRESHOLD"]),
        "score_weights": {k: float(v) for k, v in w.items()},
        "base_malicious_rate": float(ns["BASE_MALICIOUS_RATE"]),
        "risk_model_name": str(ns["BEST_RISK_MODEL_NAME"]),
        "test_metrics": metrics,
        "examples": examples,
    }
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, f"{key}.json"), "w") as f:
        json.dump(bundle, f, indent=1)
    joblib.dump({"risk_model": ns["risk_model"], "text_models": ns["TEXT_MODELS"], "q_table": ns["BEST_Q"]},
                os.path.join(MODEL_DIR, f"{key}.joblib"), compress=3)
    print(f"{key}: exported in {time.time() - t0:.0f}s | model={bundle['risk_model_name']} | "
          f"rules={len(rules)} | test precision={metrics['Precision']:.3f} accuracy={metrics['Accuracy']:.3f}")


if __name__ == "__main__":
    for k in (sys.argv[1:] or list(CATEGORIES)):
        export(k)
